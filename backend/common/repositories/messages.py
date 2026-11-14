"""Accès à la table Messages (contrat : db-messages).

Clé : partition sessionId, tri messageId (ULID, donc ordre chronologique).
Le message de l'assistant porte son `explanation` (contrat : schema-message) ;
si un item approche 400 Ko, déplacer explanation dans une table à part.
"""

from __future__ import annotations

from typing import Any


def list_messages(session_id: str, limit: int = 50, cursor: str | None = None) -> dict[str, Any]:
    """Liste les messages d'une conversation, ordre chronologique (par messageId).

    Retourne { items: [schema-message], nextCursor: str | None }.
    `cursor` est la chaîne opaque de la page précédente (None = première page).
    """
    raise NotImplementedError


def put_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    status: str,
    explanation: dict[str, Any] | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Écrit un message (messageId = new_message_id() si non fourni) et le retourne.

    role : 'user' ou 'assistant'. status : 'done', 'pending' ou 'error'.
    explanation n'est présent que pour role = 'assistant'.
    """
    raise NotImplementedError


def delete_messages(session_id: str) -> None:
    """Supprime tous les messages d'une conversation (avec la conversation,
    contrat : api-conversations-delete)."""
    raise NotImplementedError
