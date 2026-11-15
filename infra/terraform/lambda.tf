# srv-api-light et srv-agent-runtime : deux Lambdas Python 3.12 arm64.
# Les zips sont construits par infra/scripts/build_lambdas.sh ; tant que les
# handlers n'existent pas encore (WS4, WS5), les zips sont factices (README).
# Les groupes de journaux (cloudwatch.tf) sont créés avant les fonctions pour
# éviter leur création automatique au premier appel.

locals {
  api_zip    = "${path.module}/build/api.zip"
  agents_zip = "${path.module}/build/agents.zip"

  # Variables communes aux deux Lambdas (noms exacts de backend/common/config.py).
  # La Lambda API valide les tickers avec une copie embarquée dans son zip
  # (backend/api/tickers.json) : elle ne lit pas S3 et n'a ni DATASET_BUCKET
  # ni DATASET_VERSION ; la Lambda agents les conserve.
  common_env_vars = {
    USERS_TABLE         = local.table_names.users
    CONVERSATIONS_TABLE = local.table_names.conversations
    MESSAGES_TABLE      = local.table_names.messages
    PORTFOLIOS_TABLE    = local.table_names.portfolios
    ANALYSES_TABLE      = local.table_names.analyses
    MODEL_ORCHESTRATOR  = var.model_orchestrator
    LOG_LEVEL           = var.log_level
  }
  api_env_vars = local.common_env_vars
  # Lambda agents : jeu de données, modèles de l'auditeur et du rédacteur,
  # Knowledge Base et Guardrail (noms de backend/common/config.py, WS0b).
  agents_env_vars = merge(local.common_env_vars, {
    DATASET_BUCKET        = local.dataset_bucket
    DATASET_VERSION       = var.dataset_version
    MODEL_AUDITOR         = var.model_auditor
    MODEL_WRITER          = var.model_writer
    KB_ID                 = aws_bedrockagent_knowledge_base.regulation.id
    KB_CORPUS_VERSION     = var.kb_citable_corpus_version
    GUARDRAIL_ID          = aws_bedrock_guardrail.this.guardrail_id
    GUARDRAIL_VERSION     = aws_bedrock_guardrail_version.this.version
    LANGFUSE_PUBLIC_KEY   = var.langfuse_public_key
    LANGFUSE_BASE_URL     = var.langfuse_base_url
    LANGFUSE_SECRET_PARAM = var.langfuse_secret_param
  })
}

resource "aws_lambda_function" "api" {
  function_name = "${var.name_prefix}-api"
  description   = "AlphaForge API légère (CRUD, srv-api-light)"
  role          = aws_iam_role.api.arn

  runtime       = "python3.12"
  architectures = ["arm64"]
  handler       = "backend/api/app.handler"
  memory_size   = 256
  timeout       = 10

  filename = local.api_zip
  # Zip absent tant que build_lambdas.sh n'a pas tourné : validate passe,
  # le plan exige les zips (voir infra/README.md).
  source_code_hash = can(filebase64sha256(local.api_zip)) ? filebase64sha256(local.api_zip) : null

  environment {
    variables = local.api_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
  ]
}

resource "aws_lambda_function" "agents" {
  function_name = "${var.name_prefix}-agents"
  description   = "AlphaForge orchestration et outils (srv-agent-runtime)"
  role          = aws_iam_role.agents.arn

  runtime       = "python3.12"
  architectures = ["arm64"]
  handler       = "backend/agents/app.handler"
  memory_size   = 2048
  # 180 s : la complétion asynchrone d'un run (auditeur, rédacteur, traduction,
  # vérificateur) dépasse les 30 s de l'API Gateway. Les routes HTTP restent
  # bornées par l'API Gateway (30 s) et par les limites des agents.
  timeout = 180

  filename         = local.agents_zip
  source_code_hash = can(filebase64sha256(local.agents_zip)) ? filebase64sha256(local.agents_zip) : null

  # Couche AWS SDK for pandas (pandas + pyarrow), en variable.
  layers = var.pandas_layer_arn != null ? [var.pandas_layer_arn] : null

  environment {
    variables = local.agents_env_vars
  }

  depends_on = [
    aws_cloudwatch_log_group.agents,
  ]
}
