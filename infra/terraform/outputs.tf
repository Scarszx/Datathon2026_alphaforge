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
  description = "Noms des tables DynamoDB (identiques à local.table_names)."
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
