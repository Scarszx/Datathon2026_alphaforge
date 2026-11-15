"""Routes /conversations et /conversations/{sessionId}/messages.

Une ressource d'un autre utilisateur est invisible : elle produit le 404 du
contrat et jamais ses données. La suppression enchaîne messages, analyses puis
conversation (la couche WS2/WS2b n'est pas atomique ; voir NOTES-db.md).
"""

from __future__ import annotations

from typing import Any

from backend.api.validation import (
    parse_json_body,
    parse_pagination,
    session_id,
    validate_conversation_create,
    validate_conversation_update,
)
from backend.common.http import ApiError, CORS_HEADERS, json_response
from backend.common.repositories import analyses as analyses_repo
from backend.common.repositories import conversations as repo
from backend.common.repositories import messages as messages_repo


def _not_found() -> ApiError:
    """Nouvelle erreur à chaque appel : ne pas partager le requestId."""
    return ApiError("CONVERSATION_NOT_FOUND", "Conversation inconnue.")


def _no_content() -> dict[str, Any]:
    """Réponse 204 du contrat : pas de corps, en-têtes CORS communs."""
    return {"statusCode": 204, "headers": dict(CORS_HEADERS), "body": ""}


def _ensure_owner(user_id: str, session_id: str) -> None:
    if repo.get_conversation(user_id, session_id) is None:
        raise _not_found()


def list_conversations(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """GET /v1/conversations : pages triées par updatedAt décroissant."""
    limit, cursor = parse_pagination(event, default_limit=20)
    page = repo.list_conversations(user_id, limit=limit, cursor=cursor)
    return json_response(200, page)


def create_conversation(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """POST /v1/conversations : création sans corps acceptée (title facultatif)."""
    body = parse_json_body(event, required=False, allow_empty=True)
    title = validate_conversation_create(body)
    conversation = repo.create_conversation(user_id, title=title)
    return json_response(201, conversation)


def rename_conversation(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """PATCH /v1/conversations/{sessionId} : renomme la conversation."""
    session_id_value = session_id(event)
    body = parse_json_body(event)
    title = validate_conversation_update(body)
    conversation = repo.rename_conversation(user_id, session_id_value, title)
    return json_response(200, conversation)


def delete_conversation(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """DELETE /v1/conversations/{sessionId} : supprime messages, analyses puis conversation."""
    session_id_value = session_id(event)
    _ensure_owner(user_id, session_id_value)
    messages_repo.delete_messages(session_id_value)
    analyses_repo.delete_analyses(session_id_value, user_id)
    repo.delete_conversation(user_id, session_id_value)
    return _no_content()


def list_messages(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """GET /v1/conversations/{sessionId}/messages : ordre chronologique."""
    session_id_value = session_id(event)
    _ensure_owner(user_id, session_id_value)
    limit, cursor = parse_pagination(event, default_limit=50)
    page = messages_repo.list_messages(session_id_value, limit=limit, cursor=cursor)
    return json_response(200, page)
