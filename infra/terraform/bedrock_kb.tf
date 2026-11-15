# srv-bedrock-kb : Knowledge Base réglementaire (contrat v0.4.0).
#
# Corpus (storage-kb-corpus) : s3://<bucket du jeu de données>/kb/<version>/,
# alimenté par infra/scripts/kb_sync.sh (job-kb-sync), qui lance aussi
# l'ingestion. Chaque document a son <fichier>.metadata.json à côté : Bedrock
# lit ces attributs (juridiction, regulateur, sujets, date_version, langue,
# type_document, source_url, date_recuperation) à l'ingestion, sans déclaration
# dans Terraform. agent-auditor filtre ensuite sur juridiction et sujets.
#
# Magasin de vecteurs : Amazon S3 Vectors (choix justifié dans infra/README.md :
# création en quelques secondes, aucun coût fixe, entièrement en Terraform).

locals {
  kb_vector_bucket = "${var.name_prefix}-kb-vectors-${local.account_id}"
  kb_index_name    = "${var.name_prefix}-kb-regulation"
}

# --- Magasin de vecteurs (S3 Vectors) ---

resource "aws_s3vectors_vector_bucket" "kb" {
  vector_bucket_name = local.kb_vector_bucket
  # Compte d'atelier supprimé après l'événement : destroy sans vidage préalable.
  force_destroy = true
}

resource "aws_s3vectors_index" "kb" {
  vector_bucket_name = aws_s3vectors_vector_bucket.kb.vector_bucket_name
  index_name         = local.kb_index_name
  data_type          = "float32"
  dimension          = var.embedding_dimensions
  distance_metric    = "cosine"

  # S3 Vectors limite les métadonnées filtrables à 2 Ko par vecteur. Le texte
  # du passage et le bloc interne de Bedrock sont donc non filtrables ; les
  # attributs du .metadata.json (juridiction, sujets…) restent filtrables.
  metadata_configuration {
    non_filterable_metadata_keys = ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]
  }
}

# --- Rôle de service de la KB (lecture du corpus, embeddings, index) ---

data "aws_iam_policy_document" "kb_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    # Protection contre le « confused deputy » : seules les KB de ce compte.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock:${var.aws_region}:${local.account_id}:knowledge-base/*"]
    }
  }
}

resource "aws_iam_role" "kb" {
  name               = "${var.name_prefix}-kb-role"
  assume_role_policy = data.aws_iam_policy_document.kb_assume.json
}

data "aws_iam_policy_document" "kb" {
  # Corpus : liste limitée au préfixe kb/, lecture des objets sous kb/.
  statement {
    sid       = "CorpusList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.dataset.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["kb/*"]
    }
  }

  statement {
    sid       = "CorpusRead"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.dataset.arn}/kb/*"]
  }

  # Embeddings (modèle de fondation, région de la KB).
  statement {
    sid       = "EmbeddingModel"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_model_arn]
  }

  # Index S3 Vectors : écriture à l'ingestion, requête au Retrieve.
  statement {
    sid    = "VectorIndex"
    effect = "Allow"
    actions = [
      "s3vectors:GetIndex",
      "s3vectors:PutVectors",
      "s3vectors:GetVectors",
      "s3vectors:DeleteVectors",
      "s3vectors:QueryVectors",
    ]
    resources = [aws_s3vectors_index.kb.index_arn]
  }
}

resource "aws_iam_role_policy" "kb" {
  name   = "${var.name_prefix}-kb-policy"
  role   = aws_iam_role.kb.id
  policy = data.aws_iam_policy_document.kb.json
}

# --- Knowledge Base et source de données ---

resource "aws_bedrockagent_knowledge_base" "regulation" {
  name        = "${var.name_prefix}-regulation"
  description = "Canadian regulatory corpus (CSA, CIRO, AMF, FSRA, FCAA) used by agent-auditor to cite rule verdicts. English only."
  role_arn    = aws_iam_role.kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model_arn
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = var.embedding_dimensions
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.kb.index_arn
    }
  }

  # Bedrock vérifie les droits du rôle à la création : la politique doit exister
  # avant (en cas d'erreur de propagation IAM, relancer apply).
  depends_on = [aws_iam_role_policy.kb]
}

resource "aws_bedrockagent_data_source" "corpus" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.regulation.id
  name              = "${var.name_prefix}-regulation-corpus"
  description       = "Regulatory documents and their .metadata.json under kb/${var.kb_corpus_version}/."
  # RETAIN : la suppression de la source ne dépend pas de l'index (destroy fiable).
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.dataset.arn
      inclusion_prefixes = [local.kb_prefix]
    }
  }

  # Passages courts et précis pour les citations KB-nn (extrait court).
  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
}
