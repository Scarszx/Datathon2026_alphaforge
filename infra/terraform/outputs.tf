output "api_url" {
  description = "URL de base de l'API (préfixe /v1 du contrat)."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "cognito_user_pool_id" {
  description = "ID du user pool Cognito (issuer pour le front)."
  value       = aws_cognito_user_pool.pool.id
}

output "cognito_user_pool_client_id" {
  description = "ID du client d'application sans secret (Amplify Auth / SDK Cognito)."
  value       = aws_cognito_user_pool_client.client.id
}

output "table_names" {
  description = "Noms des tables DynamoDB, dont Analyses (identiques à local.table_names)."
  value       = local.table_names
}

output "dataset_bucket" {
  description = "Nom du bucket privé du jeu de données (préfixe dataset/<version>/)."
  value       = local.dataset_bucket
}

output "front_bucket" {
  description = "Nom du bucket S3 du front (origine CloudFront)."
  value       = local.front_bucket
}

output "front_url" {
  description = "URL publique du front (origine à ajouter au CORS si nécessaire)."
  value       = "https://${aws_cloudfront_distribution.front.domain_name}"
}

output "analyses_table" {
  description = "Nom de la table Analyses (mandats et runs, variable ANALYSES_TABLE)."
  value       = aws_dynamodb_table.analyses.name
}

output "kb_id" {
  description = "Identifiant de la Knowledge Base réglementaire (variable KB_ID de la Lambda agents)."
  value       = aws_bedrockagent_knowledge_base.regulation.id
}

output "kb_data_source_id" {
  description = "Identifiant de la source de données S3 de la KB (pour start-ingestion-job, voir infra/scripts/kb_sync.sh)."
  value       = aws_bedrockagent_data_source.corpus.data_source_id
}

output "kb_corpus_prefix" {
  description = "Préfixe S3 du corpus indexé (kb/<version>/) dans le bucket dataset_bucket."
  value       = local.kb_prefix
}

output "guardrail_id" {
  description = "Identifiant du Guardrail Bedrock (variable GUARDRAIL_ID)."
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_version" {
  description = "Version publiée du Guardrail (variable GUARDRAIL_VERSION)."
  value       = aws_bedrock_guardrail_version.this.version
}
