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
  default     = "global.anthropic.claude-opus-5-5"
}

variable "model_auditor" {
  description = "Profil d'inférence Bedrock de l'auditeur (agent-auditor, section agents du contrat v0.4.0)."
  type        = string
  default     = "global.anthropic.claude-opus-5-5"
}

variable "model_writer" {
  description = "Profil d'inférence Bedrock du rédacteur (agent-writer, section agents du contrat v0.4.0)."
  type        = string
  default     = "global.anthropic.claude-opus-5-5"
}

variable "kb_corpus_version" {
  description = "Version du corpus réglementaire téléversé sous s3://<bucket>/kb/<version>/ (storage-kb-corpus). La source de données de la Knowledge Base n'indexe que ce préfixe."
  type        = string
  default     = "2026-11-14"
}

variable "kb_citable_corpus_version" {
  description = "Version du corpus par section (métadonnée citable) réellement ingérée dans la Knowledge Base, ex. 2026-11-15. Vide tant que l'ancien corpus est en place : le code n'applique alors ni le filtre citable strict ni les citations fixées de R5 et R9. À renseigner dans le même apply que kb_corpus_version, après l'ingestion."
  type        = string
  default     = ""
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
  description = "Origines autorisées par l'API Gateway (développement local sur Vite). L'URL CloudFront du front est ajoutée automatiquement."
  type        = list(string)
  default     = ["http://localhost:5173", "http://localhost:4173"]
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

variable "langfuse_public_key" {
  description = "Clé publique du projet Langfuse (identifiant non secret)."
  type        = string
  default     = "pk-lf-a2d4308e-ebc7-41b4-b0e5-69afc46d74cd"
}

variable "langfuse_base_url" {
  description = "URL de base Langfuse (région US par défaut)."
  type        = string
  default     = "https://us.cloud.langfuse.com"
}

variable "langfuse_secret_param" {
  description = "Chemin du paramètre SSM SecureString contenant la clé secrète Langfuse (créé hors Terraform via aws ssm put-parameter pour ne jamais figurer dans le tfstate)."
  type        = string
  default     = "/alphaforge/langfuse/secret-key"
}
