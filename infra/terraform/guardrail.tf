# srv-bedrock-guardrails : filtre d'entrée (traduction anglaise et texte
# original du message) et de sortie (texte final affiché). SOLUTION.md 7.6.
#
# Sujets refusés : ordres de transaction, promesses de rendement, conseil
# personnalisé réglementé. Les définitions excluent explicitement l'analyse et
# la simulation de portefeuille, le cœur de l'outil, pour limiter les faux
# positifs sur le vocabulaire financier normal (à tester tôt, voir NOTES-infra.md).
# Textes en anglais (rule-internal-english) : les filtres y sont les plus fiables.
#
# Les exemples ne contiennent ni ticker, ni titre précis (version 3) : le
# classificateur de sujets est sémantique et, en version 2, « Buy 100 shares of
# XIU for me » et « Should I sell my Shopify shares » attiraient les phrases de
# simulation (« What if I add 10 % of XIU… », « Compare XSP and ZEQT… »).
# Règle : des exemples clairement impératifs, en parlant du titre visé
# (« that stock », « that company ») plutôt que d'un ticker.
#
# VARIANTE B du comparatif du 2026-11-15 : tier STANDARD pour les sujets refusés
# (+32 % de rappel et +18 % de précision équilibrée documentés par AWS sur la
# détection de sujets, définitions jusqu'à 1000 caractères). Le tier STANDARD
# exige l'inférence multi-région (cross_region_config, profil us.guardrail.v1:0,
# sans coût supplémentaire) et des droits IAM sur les ARN de profil des régions
# de destination pour ApplyGuardrail. Requiert un provider >= 6.6.0
# (cross_region_config et topic_policy_config.tier_config) ; la longueur
# maximale des définitions passe de 200 à 1000 caractères avec le provider
# >= 6.62.0. Les 3 sujets restent bloqués dans les deux sens : on mesure si le
# tier STANDARD élimine les faux positifs que le tier CLASSIC produit.

resource "aws_bedrock_guardrail" "this" {
  name        = "${var.name_prefix}-guardrail"
  description = "AlphaForge input/output filter: trade orders, return promises, personalized regulated advice, banking PII."

  # Tier STANDARD des sujets refusés : exige l'inférence multi-région.
  cross_region_config {
    guardrail_profile_identifier = "arn:aws:bedrock:${var.aws_region}:${local.account_id}:guardrail-profile/us.guardrail.v1:0"
  }

  blocked_input_messaging   = "This request is outside what AlphaForge can do. It is a simulation and decision-support tool: it cannot place trades, promise returns or give personalized investment advice. You can ask it to simulate the impact of a change on your fictional portfolio instead."
  blocked_outputs_messaging = "The response was withheld because it could read as a trade order, a return promise or personalized investment advice. AlphaForge only simulates and explains, using its dataset and regulatory sources."

  topic_policy_config {
    tier_config {
      tier_name = "STANDARD"
    }

    topics_config {
      name       = "Trade execution orders"
      type       = "DENY"
      definition = "Instructions to execute a real buy, sell or transfer order on the user's behalf. Hypothetical 'what if' questions or simulating adding, removing or rebalancing a holding are not this topic."
      examples = [
        "Buy 100 shares of that stock for me.",
        "Sell all my shares right now.",
        "Place a limit order at 120 dollars.",
        "Transfer my portfolio to cash today.",
      ]
    }

    topics_config {
      name       = "Guaranteed or promised returns"
      type       = "DENY"
      definition = "Promising, guaranteeing or predicting a specific future return, gain or absence of loss for an investment or portfolio. Describing past measured performance is not this topic."
      examples = [
        "Guarantee me 20 percent a year.",
        "Promise that this portfolio will not lose money.",
        "How much will I surely earn next year with this ETF?",
        "This fund will definitely double by 2030.",
      ]
    }

    topics_config {
      name       = "Personalized investment recommendation"
      type       = "DENY"
      definition = "Telling a person which security to buy, sell or hold, or acting as their advisor. Simulating a portfolio, comparing specific ETFs or securities, or analyzing portfolio impact is not this topic."
      examples = [
        "Which stock should I buy with my savings?",
        "Should I sell my shares of that company?",
        "Be my financial advisor and pick my investments.",
        "Tell me the best investment for me to buy right now.",
      ]
    }
  }

  # Renseignements bancaires et identifiants (rule-no-real-data).
  sensitive_information_policy_config {
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "US_BANK_ACCOUNT_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "US_BANK_ROUTING_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "CA_SOCIAL_INSURANCE_NUMBER"
      action = "BLOCK"
    }

    # Compte bancaire canadien : transit (5) - institution (3) - compte (7 à 12).
    regexes_config {
      name        = "ca-bank-account"
      description = "Canadian bank account number: transit-institution-account."
      pattern     = "\\b\\d{5}[- ]?\\d{3}[- ]?\\d{7,12}\\b"
      action      = "BLOCK"
    }
  }
}

# Version publiée (GUARDRAIL_VERSION de la Lambda agents). Toute modification
# du Guardrail publie une nouvelle version.
resource "aws_bedrock_guardrail_version" "this" {
  guardrail_arn = aws_bedrock_guardrail.this.guardrail_arn
  description   = "Published by Terraform (contract v0.4.0)."

  lifecycle {
    replace_triggered_by = [aws_bedrock_guardrail.this]
  }
}
