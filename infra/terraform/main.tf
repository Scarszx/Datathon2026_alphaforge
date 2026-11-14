terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # État partagé à prévoir pour l'intégration (une seule personne fera apply).
  # Décommenter et adapter, puis migrer l'état avec `terraform init -migrate-state` :
  #
  # backend "s3" {
  #   bucket       = "<bucket-etat-terraform>"
  #   key          = "alphaforge/terraform.tfstate"
  #   region       = "us-east-1"
  #   use_lockfile = true
  #   encrypt      = true
  # }
}

# Aucune data source évaluée par terraform validate : fmt et validate passent
# sans identifiants AWS. data.aws_caller_identity n'est résolue qu'au plan.
data "aws_caller_identity" "current" {}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "AlphaForge"
      ManagedBy = "terraform"
    }
  }
}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # Noms de tables exacts du contrat (section databases) : lus par
  # backend/common/config.py via les variables d'environnement.
  table_names = {
    users         = "Users"
    conversations = "Conversations"
    messages      = "Messages"
    portfolios    = "Portfolios"
  }

  # Suffixe par compte : les noms de bucket sont globalement uniques.
  dataset_bucket = "${var.name_prefix}-dataset-${local.account_id}"
  front_bucket   = "${var.name_prefix}-front-${local.account_id}"

  # Modèles Bedrock (section agents du contrat, model : A_CHOISIR).
  # L'invocation bedrock-runtime exige un profil d'inférence : l'ID nu
  # (anthropic.claude-sonnet-5-5) est refusé en on-demand throughput.
  # Défaut : profil global (prix liste). Alternative : us.anthropic.claude-sonnet-5-5
  # (+10 %, routage limité aux régions US/Canada).
  model_ids = distinct([var.model_orchestrator, var.model_analyst, var.model_governance])

  # Modèle de fondation derrière chaque profil (préfixe de routage retiré).
  # Région "*" : le routage global peut viser n'importe quelle région du catalogue.
  foundation_model_arns = [
    for m in local.model_ids : "arn:aws:bedrock:*::foundation-model/${replace(m, "/^(global|us|eu|au|jp|in)[.]/", "")}"
  ]
  # L'ARN d'un profil d'inférence porte le compte de l'appelant.
  inference_profile_arns = [
    for m in local.model_ids : "arn:aws:bedrock:${var.aws_region}:${local.account_id}:inference-profile/${m}"
  ]
  bedrock_invoke_arns = distinct(concat(local.inference_profile_arns, local.foundation_model_arns))

  cognito_issuer = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.pool.id}"

  dataset_prefix_arn = "arn:aws:s3:::${local.dataset_bucket}/dataset/*"
}
