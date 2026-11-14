# srv-cloudwatch : groupes de journaux des deux Lambdas, rétention courte.
# Noms fixes (pas de référence à aws_lambda_function) pour éviter un cycle
# avec les depends_on des fonctions.

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.name_prefix}-api"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "agents" {
  name              = "/aws/lambda/${var.name_prefix}-agents"
  retention_in_days = 14
}
