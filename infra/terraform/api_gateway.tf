# srv-api-gateway : porte d'entrée unique, authorizer JWT natif relié à Cognito.
# Routes exactement comme dans le contrat (services.routes_to et apis.provider).

locals {
  # 18 APIs du contrat v0.4.8, avec l'intégration Lambda qui les dessert.
  routes = {
    me_get               = { method = "GET", path = "/v1/me", target = "api" }
    me_profile_put       = { method = "PUT", path = "/v1/me/profile", target = "api" }
    conversations_list   = { method = "GET", path = "/v1/conversations", target = "api" }
    conversations_create = { method = "POST", path = "/v1/conversations", target = "api" }
    conversation_update  = { method = "PATCH", path = "/v1/conversations/{sessionId}", target = "api" }
    conversation_delete  = { method = "DELETE", path = "/v1/conversations/{sessionId}", target = "api" }
    messages_list        = { method = "GET", path = "/v1/conversations/{sessionId}/messages", target = "api" }
    messages_create      = { method = "POST", path = "/v1/conversations/{sessionId}/messages", target = "agents" }
    portfolios_list      = { method = "GET", path = "/v1/portfolios", target = "api" }
    holdings_put         = { method = "PUT", path = "/v1/portfolios/{portfolioId}/holdings", target = "api" }
    portfolio_summary    = { method = "GET", path = "/v1/portfolios/{portfolioId}/summary", target = "agents" }
    market_search        = { method = "GET", path = "/v1/market/search", target = "agents" }
    agents_registry      = { method = "GET", path = "/v1/agents", target = "api" }
    mandates_create      = { method = "POST", path = "/v1/conversations/{sessionId}/mandates", target = "api" }
    mandates_list        = { method = "GET", path = "/v1/conversations/{sessionId}/mandates", target = "api" }
    runs_create          = { method = "POST", path = "/v1/conversations/{sessionId}/runs", target = "agents" }
    runs_get             = { method = "GET", path = "/v1/conversations/{sessionId}/runs/{runId}", target = "agents" }
    speech_session       = { method = "POST", path = "/v1/speech/session", target = "api" }
  }
}

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = distinct(concat(var.cors_origins, ["https://${aws_cloudfront_distribution.front.domain_name}"]))
    allow_methods = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Authorization", "Content-Type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "cognito"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.client.id]
    issuer   = local.cognito_issuer
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000 # limite connue du contrat (chat synchrone)
}

resource "aws_apigatewayv2_integration" "agents" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.agents.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_route" "this" {
  for_each = local.routes

  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "${each.value.method} ${each.value.path}"
  target             = "integrations/${each.value.target == "api" ? aws_apigatewayv2_integration.api.id : aws_apigatewayv2_integration.agents.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
}

# Une seule permission par fonction, couvrant toutes les routes de l'API.
resource "aws_lambda_permission" "api" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${local.account_id}:${aws_apigatewayv2_api.this.id}/*/*"
}

resource "aws_lambda_permission" "agents" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agents.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${local.account_id}:${aws_apigatewayv2_api.this.id}/*/*"
}
