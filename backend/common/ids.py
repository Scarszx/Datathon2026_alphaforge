"""Identifiants du contrat (conventions.identifiers) :

- sessionId : UUID v4 généré par le serveur ;
- messageId : ULID, triable par ordre chronologique (utile pour la clé de tri
  de la table Messages et pour la pagination) ;
- runId : ULID d'une exécution d'analyse (clé RUN#<runId> de la table Analyses).
"""

from __future__ import annotations

import uuid

import ulid
from ulid import ULID


def new_session_id() -> str:
    """Retourne un sessionId au format UUID v4."""
    return str(uuid.uuid4())


def new_message_id() -> str:
    """Retourne un messageId au format ULID (26 caractères, triable)."""
    return str(ULID())


def new_run_id() -> str:
    """Retourne un runId au format ULID (26 caractères, triable)."""
    return str(ULID())
