variable "aws_region" {
  description = "Région AWS du déploiement (contrat v0.4.0 : us-east-1, toutes les ressources y restent)."
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

variable "model_auditor" {
  description = "Profil d'inférence Bedrock de l'auditeur (agent-auditor, section agents du contrat v0.4.0)."
  type        = string
  default     = "global.anthropic.claude-sonnet-5-5"
}

variable "model_writer" {
  description = "Profil d'inférence Bedrock du rédacteur (agent-writer, section agents du contrat v0.4.0)."
  type        = string
  default     = "global.anthropic.claude-sonnet-5-5"
}

variable "kb_corpus_version" {
  description = "Version du corpus réglementaire téléversé sous s3://<bucket>/kb/<version>/ (storage-kb-corpus). La source de données de la Knowledge Base n'indexe que ce préfixe."
  type        = string
  default     = "2026-11-14"
}

variable "embedding_model_id" {
  description = "Modèle d'embeddings Bedrock de la Knowledge Base (disponible en us-east-1). Doit produire des vecteurs de var.embedding_dimensions dimensions."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dimensions" {
  description = "Dimension des vecteurs (Titan Text Embeddings V2 : 256, 512 ou 1024). Identique pour le modèle et l'index S3 Vectors."
  type        = number
  default     = 1024
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
