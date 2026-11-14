variable "aws_region" {
  description = "Région AWS du déploiement (contrat : A_CONFIRMER ; le compte d'atelier est ici)."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Préfixe des noms de ressources (fonctions, buckets, log groups)."
  type        = string
  default     = "alphaforge"
}

variable "dataset_version" {
  description = "Version du jeu de données téléversée sous s3://<bucket>/dataset/<version>/ (variable DATASET_VERSION des Lambdas, section storage du contrat)."
  type        = string
  # Pas de défaut : le plan demandera la version téléversée par l'ingestion (WS3).
}

variable "model_orchestrator" {
  description = "Profil d'inférence Bedrock de l'orchestrateur (agent-orchestrator, section agents du contrat)."
  type        = string
  default     = "global.anthropic.claude-sonnet-5-5"
}

variable "model_analyst" {
  description = "Profil d'inférence Bedrock de l'analyste (agent-analyst)."
  type        = string
  default     = "global.anthropic.claude-sonnet-5-5"
}

variable "model_governance" {
  description = "Profil d'inférence Bedrock de la gouvernance (agent-governance)."
  type        = string
  default     = "global.anthropic.claude-sonnet-5-5"
}

variable "cors_origins" {
  description = "Origines autorisées par l'API Gateway (le front local en développement). L'URL CloudFront du front est ajoutée automatiquement."
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "pandas_layer_arn" {
  description = "ARN de la couche Lambda AWS SDK for pandas (runtime Python 3.12, architecture arm64). La Lambda agent-runtime en a besoin pour pandas/pyarrow. Voir infra/README.md pour trouver la dernière version ; null tant qu'elle n'est pas choisie."
  type        = string
  default     = null
}

variable "log_level" {
  description = "Niveau de journalisation des Lambdas (LOG_LEVEL)."
  type        = string
  default     = "INFO"
}
