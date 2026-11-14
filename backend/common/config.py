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


# --- Tables DynamoDB (contrat : db-users, db-conversations, db-messages, db-portfolios) ---


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


# --- Jeu de données (contrat : storage-dataset) ---


def dataset_bucket() -> str:
    """Nom du bucket S3 privé qui héberge le jeu de données."""
    return _required("DATASET_BUCKET")


def dataset_version() -> str:
    """Version du jeu de données à lire (préfixe dataset/{version}/ du bucket)."""
    return _required("DATASET_VERSION")


# --- Modèles Bedrock (contrat : agents, model = A_CHOISIR) ---


def model_orchestrator() -> str | None:
    """Identifiant du modèle Bedrock de l'orchestrateur, None tant que non configuré."""
    return os.environ.get("MODEL_ORCHESTRATOR")


def model_analyst() -> str | None:
    """Identifiant du modèle Bedrock de l'analyste, None tant que non configuré."""
    return os.environ.get("MODEL_ANALYST")


def model_governance() -> str | None:
    """Identifiant du modèle Bedrock de la gouvernance, None tant que non configuré."""
    return os.environ.get("MODEL_GOVERNANCE")


# --- Divers ---


def log_level() -> str:
    """Niveau de journalisation, INFO par défaut."""
    return os.environ.get("LOG_LEVEL", "INFO")
