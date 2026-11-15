# db-users, db-conversations, db-messages, db-portfolios, db-analyses : clés et attributs
# exactement comme dans la section databases du contrat.

resource "aws_dynamodb_table" "users" {
  name         = local.table_names.users
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "conversations" {
  name         = local.table_names.conversations
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "sessionId"

  attribute {
    name = "userId"
    type = "S"
  }
  attribute {
    name = "sessionId"
    type = "S"
  }
  attribute {
    name = "updatedAt"
    type = "S"
  }

  # Index local pour trier par récence (contrat : api-conversations-list,
  # plus récentes d'abord).
  local_secondary_index {
    name            = "updatedAt-index"
    range_key       = "updatedAt"
    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "messages" {
  name         = local.table_names.messages
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sessionId"
  range_key    = "messageId"

  attribute {
    name = "sessionId"
    type = "S"
  }
  attribute {
    name = "messageId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "portfolios" {
  name         = local.table_names.portfolios
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "portfolioId"

  attribute {
    name = "userId"
    type = "S"
  }
  attribute {
    name = "portfolioId"
    type = "S"
  }
}

# db-analyses (contrat v0.4.0) : mandats et runs d'une session.
# itemKey = MANDATE#<version sur 3 chiffres> ou RUN#<runId>.
resource "aws_dynamodb_table" "analyses" {
  name         = local.table_names.analyses
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sessionId"
  range_key    = "itemKey"

  attribute {
    name = "sessionId"
    type = "S"
  }
  attribute {
    name = "itemKey"
    type = "S"
  }
}
