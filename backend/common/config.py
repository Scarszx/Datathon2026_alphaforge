"""Lecture des variables d'environnement, à l'appel (jamais à l'import).

Les noms ci-dessous sont fixés par WS0 (docs/workstreams.md) et partagés par
tous les chantiers : le backend/api, le backend/agents et l'infra Terraform
définissent exactement ces variables dans les Lambdas. Tout le reste du code
lit la configuration via ces fonctions, jamais avec `os.environ` directement.
"""

from __future__ import annotations

import os


class MissingEnvVar(RuntimeError):
    """Variable d'environnement requise absente : déploiement incomplet."""


def _required(name: str) -> str:
    """Retourne la variable d'environnement, ou lève MissingEnvVar si absente."""
    value = os.environ.get(name)
    if not value:
        raise MissingEnvVar(f"Variable d'environnement requise absente : {name}")
    return value


# --- Tables DynamoDB (contrat : db-users, db-conversations, db-messages, db-portfolios, db-analyses) ---


def users_table() -> str:
    """Nom de la table Users (partition : userId)."""
    return _required("USERS_TABLE")


def conversations_table() -> str:
    """Nom de la table Conversations (partition : userId, tri : sessionId)."""
    return _required("CONVERSATIONS_TABLE")


def messages_table() -> str:
    """Nom de la table Messages (partition : sessionId, tri : messageId)."""
    return _required("MESSAGES_TABLE")


def portfolios_table() -> str:
    """Nom de la table Portfolios (partition : userId, tri : portfolioId)."""
    return _required("PORTFOLIOS_TABLE")


def analyses_table() -> str:
    """Nom de la table Analyses (partition : sessionId, tri : itemKey).

    itemKey = MANDATE#<version sur 3 chiffres> ou RUN#<runId> (contrat v0.4.0).
    """
    return _required("ANALYSES_TABLE")


# --- Jeu de données (contrat : storage-dataset) ---


def dataset_bucket() -> str:
    """Nom du bucket S3 privé qui héberge le jeu de données."""
    return _required("DATASET_BUCKET")


def dataset_version() -> str:
    """Version du jeu de données à lire (préfixe dataset/{version}/ du bucket)."""
    return _required("DATASET_VERSION")


# --- Modèles Bedrock (contrat v0.4.0 : Claude Sonnet 5.5, région us-east-1) ---
# Un modèle par agent, lu dans la config pour pouvoir en changer sans toucher au code.
# Valeur attendue en déploiement : un profil d'inférence, ex. global.anthropic.claude-sonnet-5-5.


def model_orchestrator() -> str | None:
    """Profil d'inférence Bedrock de agent-orchestrator, None tant que non configuré."""
    return os.environ.get("MODEL_ORCHESTRATOR")


def model_auditor() -> str | None:
    """Profil d'inférence Bedrock de agent-auditor, None tant que non configuré."""
    return os.environ.get("MODEL_AUDITOR")


def model_writer() -> str | None:
    """Profil d'inférence Bedrock de agent-writer, None tant que non configuré."""
    return os.environ.get("MODEL_WRITER")


def model_analyst() -> str | None:
    """DÉPRÉCIÉ (contrat v0.4.0 : agent-analyst retiré, remplacé par module-engine).

    Conservé tant que l'infra (WS1) définit encore MODEL_ANALYST. Ne pas l'utiliser.
    """
    return os.environ.get("MODEL_ANALYST")


def model_governance() -> str | None:
    """DÉPRÉCIÉ (contrat v0.4.0 : agent-governance remplacé par agent-auditor).

    Conservé tant que l'infra (WS1) définit encore MODEL_GOVERNANCE. Ne pas l'utiliser.
    """
    return os.environ.get("MODEL_GOVERNANCE")


# --- Knowledge Base et Guardrails Bedrock (contrat : srv-bedrock-kb, srv-bedrock-guardrails) ---


def kb_id() -> str | None:
    """Identifiant de la Knowledge Base réglementaire, None tant que non configuré."""
    return os.environ.get("KB_ID")


def guardrail_id() -> str | None:
    """Identifiant du Guardrail Bedrock, None tant que non configuré."""
    return os.environ.get("GUARDRAIL_ID")


def guardrail_version() -> str | None:
    """Version publiée du Guardrail Bedrock, None tant que non configurée."""
    return os.environ.get("GUARDRAIL_VERSION")


def rules_config_path() -> str | None:
    """Chemin optionnel du fichier de seuils des règles R1-R10 (hypothèses d'équipe).

    None = le module de règles utilise son fichier de configuration embarqué.
    """
    return os.environ.get("RULES_CONFIG_PATH")


# --- Divers ---


def log_level() -> str:
    """Niveau de journalisation, INFO par défaut."""
    return os.environ.get("LOG_LEVEL", "INFO")
