# srv-cognito : comptes et mots de passe, émet et renouvelle les JWT.
# Connexion par username, client sans secret, flux SRP + USER_PASSWORD_AUTH + refresh
# (section conventions.authentication du contrat).

resource "aws_cognito_user_pool" "pool" {
  name = "${var.name_prefix}-users"

  # Login par username (le contrat ne demande ni email ni téléphone vérifiés).
  auto_verified_attributes = []
  username_configuration {
    case_sensitive = false
  }

  password_policy {
    minimum_length = 8
    # Politique volontairement simple pour le datathon : les comptes des
    # personas sont créés à la main (admin-set-user-password --permanent).
    require_lowercase                = false
    require_uppercase                = false
    require_numbers                  = false
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  mfa_configuration = "OFF"

  # Inscription sans code de confirmation par courriel : le déclencheur
  # pre sign-up confirme le compte (backend/presignup/handler.py).
  lambda_config {
    pre_sign_up = aws_lambda_function.presignup.arn
  }
}

resource "aws_lambda_permission" "cognito_presignup" {
  statement_id  = "AllowCognitoPreSignUp"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.presignup.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.pool.arn
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.name_prefix}-client"
  user_pool_id = aws_cognito_user_pool.pool.id

  # Client d'application sans secret (contrat : srv-cognito.notes).
  generate_secret = false

  # SRP (Amplify Auth / SDK Cognito) et USER_PASSWORD_AUTH, avec renouvellement
  # de jetons par refresh token.
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  # Éviter de révéler l'existence d'un compte dans les erreurs.
  prevent_user_existence_errors = "ENABLED"
}
