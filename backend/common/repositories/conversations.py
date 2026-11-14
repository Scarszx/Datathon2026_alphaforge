"""Accès à la table Conversations (contrat : db-conversations).

Clé : partition userId, tri sessionId. Index local sur updatedAt pour trier
par récence (contrat : api-conversations-list, plus récentes d'abord).
"""

from __future__ import annotations

from typing import Any


def list_conversations(user_id: str, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
    """Liste les conversations de l'utilisateur, plus récentes d'abord.

    Retourne { items: [schema-conversation], nextCursor: str | None }.
    `cursor` est la chaîne opaque de la page précédente (None = première page).
    """
    raise NotImplementedError


def create_conversation(user_id: str, title: str | None = None) -> dict[str, Any]:
    """Crée une conversation (sessionId = new_session_id()) et la retourne."""
    raise NotImplementedError


def get_conversation(user_id: str, session_id: str) -> dict[str, Any] | None:
    """Retourne la conversation si elle appartient à user_id, sinon None.

    Une conversation d'un autre utilisateur est invisible (comme inexistante).
    """
    raise NotImplementedError


def rename_conversation(user_id: str, session_id: str, title: str) -> dict[str, Any]:
    """Renomme la conversation et la retourne.

    Lève ApiError('CONVERSATION_NOT_FOUND') si absente ou non possédée.
    """
    raise NotImplementedError


def touch_conversation(user_id: str, session_id: str) -> None:
    """Met à jour updatedAt (appelé après l'ajout d'un message, contrat :
    srv-agent-runtime a le mode read_update sur db-conversations)."""
    raise NotImplementedError


def delete_conversation(user_id: str, session_id: str) -> None:
    """Supprime la conversation (pas ses messages : voir messages.delete_messages).

    Lève ApiError('CONVERSATION_NOT_FOUND') si absente ou non possédée.
    """
    raise NotImplementedError
