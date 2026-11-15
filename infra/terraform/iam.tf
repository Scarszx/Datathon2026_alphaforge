# Rôles et politiques au moindre privilège, d'après les modes d'accès du contrat
# (sections services.access_to_dbs, access_to_storage, uses_services).

locals {
  table_arn = {
    users               = "arn:aws:dynamodb:${var.aws_region}:${local.account_id}:table/${local.table_names.users}"
    conversations       = "arn:aws:dynamodb:${var.aws_region}:${local.account_id}:table/${local.table_names.conversations}"
    conversations_index = "arn:aws:dynamodb:${var.aws_region}:${local.account_id}:table/${local.table_names.conversations}/index/updatedAt-index"
    messages            = "arn:aws:dynamodb:${var.aws_region}:${local.account_id}:table/${local.table_names.messages}"
    portfolios          = "arn:aws:dynamodb:${var.aws_region}:${local.account_id}:table/${local.table_names.portfolios}"
    analyses            = "arn:aws:dynamodb:${var.aws_region}:${local.account_id}:table/${local.table_names.analyses}"
  }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  name               = "${var.name_prefix}-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role" "agents" {
  name               = "${var.name_prefix}-agents-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Lambda API : tables selon srv-api-light, + lecture de universe.parquet
# (contrat : PUT holdings valide chaque ticker ; écart explicite au doc WS1
# « tables seulement », justifié par la règle 3 de srv-api-light — voir README).
data "aws_iam_policy_document" "api" {
  # db-users : read_write
  statement {
    sid       = "UsersReadWrite"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [local.table_arn.users]
  }

  # db-conversations : read_write_delete (+ index updatedAt pour le tri)
  statement {
    sid       = "ConversationsReadWriteDelete"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [local.table_arn.conversations, local.table_arn.conversations_index]
  }

  # db-messages : read_delete
  statement {
    sid       = "MessagesReadDelete"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]
    resources = [local.table_arn.messages]
  }

  # db-portfolios : read_write
  statement {
    sid       = "PortfoliosReadWrite"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [local.table_arn.portfolios]
  }

  # db-analyses : read_write_delete (écrit les mandats, version = dernière + 1 ;
  # supprime mandats et runs avec la conversation).
  statement {
    sid       = "AnalysesReadWriteDelete"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]
    resources = [local.table_arn.analyses]
  }

  # Journaux (groupes créés par Terraform, rétention 14 jours).
  statement {
    sid       = "Logs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/aws/lambda/${var.name_prefix}-*:log-stream:*"]
  }
}

# Lambda agent-runtime : tables selon srv-agent-runtime, lecture du préfixe du
# jeu de données, invocation Bedrock (profil + modèle de fondation), journaux.
data "aws_iam_policy_document" "agents" {
  # db-conversations : read_update
  statement {
    sid       = "ConversationsReadUpdate"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem"]
    resources = [local.table_arn.conversations]
  }

  # db-messages : read_write
  statement {
    sid       = "MessagesReadWrite"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem"]
    resources = [local.table_arn.messages]
  }

  # db-portfolios : read
  statement {
    sid       = "PortfoliosRead"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = [local.table_arn.portfolios]
  }

  # db-users : read
  statement {
    sid       = "UsersRead"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [local.table_arn.users]
  }

  # db-analyses : read_write (lit les mandats, écrit les runs partial puis done).
  statement {
    sid       = "AnalysesReadWrite"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [local.table_arn.analyses]
  }

  # Jeu de données : le préfixe complet (la version change sans toucher à l'IAM).
  statement {
    sid       = "DatasetRead"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${local.dataset_prefix_arn}/*"]
  }

  # Bedrock : le profil d'inférence ET le modèle de fondation derrière
  # (piège des profils globaux : le routage peut viser plusieurs régions).
  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = local.bedrock_invoke_arns
  }

  # srv-bedrock-kb : recherche dans la KB réglementaire (tool-search-regulation).
  statement {
    sid       = "KnowledgeBaseRetrieve"
    effect    = "Allow"
    actions   = ["bedrock:Retrieve"]
    resources = [aws_bedrockagent_knowledge_base.regulation.arn]
  }

  # srv-bedrock-guardrails : filtre d'entrée et de sortie (ApplyGuardrail, ou
  # guardrail passé à l'invocation du modèle). Le tier STANDARD des sujets
  # évalue via l'inférence multi-région : le rôle doit autoriser le profil de
  # guardrail de la région source et de chaque région de destination du profil
  # us.guardrail.v1:0 (us-east-1, us-east-2, us-west-2).
  statement {
    sid       = "GuardrailApply"
    effect    = "Allow"
    actions   = ["bedrock:ApplyGuardrail"]
    resources = concat(
      [aws_bedrock_guardrail.this.guardrail_arn],
      [for r in ["us-east-1", "us-east-2", "us-west-2"] :
        "arn:aws:bedrock:${r}:${local.account_id}:guardrail-profile/us.guardrail.v1:0"]
    )
  }

  # Complétion d'un run (partial -> done) : la Lambda s'invoque elle-même en
  # asynchrone (InvocationType=Event, décision WS5). ARN construit à partir du
  # nom pour éviter un cycle rôle <-> fonction.
  statement {
    sid       = "SelfInvokeCompleteRun"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.aws_region}:${local.account_id}:function:${var.name_prefix}-agents"]
  }

  # Clé secrète Langfuse en SSM Parameter Store (SecureString, créée hors
  # Terraform pour ne jamais figurer dans terraform.tfstate).
  statement {
    sid       = "LangfuseSecretParamRead"
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${var.aws_region}:${local.account_id}:parameter/${trimprefix(var.langfuse_secret_param, "/")}"]
  }

  # Journaux.
  statement {
    sid       = "Logs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/aws/lambda/${var.name_prefix}-*:log-stream:*"]
  }
}

resource "aws_iam_role_policy" "api" {
  name   = "${var.name_prefix}-api-policy"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api.json
}

resource "aws_iam_role_policy" "agents" {
  name   = "${var.name_prefix}-agents-policy"
  role   = aws_iam_role.agents.id
  policy = data.aws_iam_policy_document.agents.json
}
