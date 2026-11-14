"""Tests des routes conversations et messages (repositories simulés)."""

from __future__ import annotations

import pytest

from backend.api.app import handle_request
from backend.api.routes import conversations
from backend.common.http import ApiError

from .conftest import body_of, event

CONVERSATION = {
    "sessionId": "5dd2f4a1-8c34-4b28-8a52-c42b7892d3f1",
    "title": "Portefeuille",
    "createdAt": "2026-11-14T09:30:00Z",
    "updatedAt": "2026-11-14T09:35:00Z",
}
MESSAGE = {
    "messageId": "01JAAAAAAAAAAAAAAAAAAAAAAA",
    "sessionId": CONVERSATION["sessionId"],
    "role": "assistant",
    "content": "Réponse simulée.",
    "status": "done",
    "createdAt": "2026-11-14T09:35:01Z",
}


@pytest.fixture
def fake_conversations(monkeypatch):
    """Replacements du repository Conversations."""
    calls: dict[str, list] = {"list": [], "create": [], "rename": [], "delete": []}

    def list_conversations(user_id: str, limit: int = 20, cursor: str | None = None):
        calls["list"].append({"userId": user_id, "limit": limit, "cursor": cursor})
        return {"items": [CONVERSATION], "nextCursor": None}

    def create_conversation(user_id: str, title: str | None = None):
        calls["create"].append({"userId": user_id, "title": title})
        return {**CONVERSATION, "title": title}

    def get_conversation(user_id: str, session_id: str):
        return CONVERSATION if user_id == "user-1" and session_id == CONVERSATION["sessionId"] else None

    def rename_conversation(user_id: str, session_id: str, title: str):
        calls["rename"].append({"userId": user_id, "sessionId": session_id, "title": title})
        return {**CONVERSATION, "title": title}

    def delete_conversation(user_id: str, session_id: str):
        calls["delete"].append({"userId": user_id, "sessionId": session_id})

    monkeypatch.setattr(conversations.repo, "list_conversations", list_conversations)
    monkeypatch.setattr(conversations.repo, "create_conversation", create_conversation)
    monkeypatch.setattr(conversations.repo, "get_conversation", get_conversation)
    monkeypatch.setattr(conversations.repo, "rename_conversation", rename_conversation)
    monkeypatch.setattr(conversations.repo, "delete_conversation", delete_conversation)
    return calls


def test_list_conversations_envoie_limit_et_cursor(fake_conversations):
    query = {"limit": "2", "cursor": "curseur-opaque"}
    response = handle_request(event("GET /v1/conversations", query_string_parameters=query))
    assert response["statusCode"] == 200
    assert body_of(response) == {"items": [CONVERSATION], "nextCursor": None}
    assert fake_conversations["list"] == [
        {"userId": "user-1", "limit": 2, "cursor": "curseur-opaque"}
    ]


@pytest.mark.parametrize("query", [{"limit": "0"}, {"limit": "101"}, {"limit": "deux"}])
def test_list_conversations_refuse_limit_invalide(fake_conversations, query):
    response = handle_request(
        event("GET /v1/conversations", query_string_parameters=query)
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_conversations["list"] == []


def test_create_conversation_renvoie_201(fake_conversations):
    response = handle_request(
        event("POST /v1/conversations", body={"title": "Nouvelle"})
    )
    assert response["statusCode"] == 201
    assert body_of(response)["title"] == "Nouvelle"
    assert fake_conversations["create"] == [{"userId": "user-1", "title": "Nouvelle"}]


def test_create_conversation_sans_corps_est_acceptee(fake_conversations):
    response = handle_request(event("POST /v1/conversations"))
    assert response["statusCode"] == 201
    assert body_of(response)["title"] is None
    assert fake_conversations["create"] == [{"userId": "user-1", "title": None}]


def test_create_conversation_refuse_champ_inconnu(fake_conversations):
    response = handle_request(
        event("POST /v1/conversations", body={"titre": "faute"})
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_conversations["create"] == []


def test_rename_conversation(fake_conversations):
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event("PATCH /v1/conversations/{sessionId}", path_parameters=path, body={"title": "B"})
    )
    assert response["statusCode"] == 200
    assert body_of(response)["title"] == "B"
    assert fake_conversations["rename"] == [
        {"userId": "user-1", "sessionId": CONVERSATION["sessionId"], "title": "B"}
    ]


@pytest.mark.parametrize(
    "body", [{}, {"title": None}, {"title": 12}, {"title": "A", "extra": 1}]
)
def test_rename_conversation_valide_le_titre(fake_conversations, body):
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event("PATCH /v1/conversations/{sessionId}", path_parameters=path, body=body)
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_conversations["rename"] == []


@pytest.mark.parametrize(
    "path",
    [{"sessionId": "pas-un-uuid"}, {"sessionId": "00000000-0000-0000-0000-000000000000"}],
)
def test_session_id_doit_etre_un_uuid_v4(fake_conversations, path):
    response = handle_request(
        event("PATCH /v1/conversations/{sessionId}", path_parameters=path, body={"title": "A"})
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_conversations["rename"] == []


def test_delete_conversation_supprime_messages_puis_conversation(
    fake_conversations, monkeypatch
):
    deleted_messages: list[str] = []
    monkeypatch.setattr(
        conversations.messages_repo, "delete_messages", deleted_messages.append
    )
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event("DELETE /v1/conversations/{sessionId}", path_parameters=path)
    )
    assert response["statusCode"] == 204
    assert response["body"] == ""
    assert deleted_messages == [CONVERSATION["sessionId"]]
    assert fake_conversations["delete"] == [
        {"userId": "user-1", "sessionId": CONVERSATION["sessionId"]}
    ]


def test_delete_conversation_etrangere_est_invisible(fake_conversations, monkeypatch):
    deleted_messages: list[str] = []
    monkeypatch.setattr(
        conversations.messages_repo, "delete_messages", deleted_messages.append
    )
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event("DELETE /v1/conversations/{sessionId}", path_parameters=path, claims={"sub": "user-2"})
    )
    assert response["statusCode"] == 404
    assert body_of(response)["error"]["code"] == "CONVERSATION_NOT_FOUND"
    assert deleted_messages == []
    assert fake_conversations["delete"] == []


def test_list_messages_verifie_la_propriete(fake_conversations, monkeypatch):
    listed: list[str] = []
    monkeypatch.setattr(
        conversations.messages_repo,
        "list_messages",
        lambda session_id, limit=50, cursor=None: (listed.append(session_id) or {"items": [MESSAGE], "nextCursor": None}),
    )
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event("GET /v1/conversations/{sessionId}/messages", path_parameters=path)
    )
    assert response["statusCode"] == 200
    assert body_of(response) == {"items": [MESSAGE], "nextCursor": None}
    assert listed == [CONVERSATION["sessionId"]]


def test_list_messages_d_une_conversation_etrangere(fake_conversations, monkeypatch):
    listed: list[str] = []
    monkeypatch.setattr(
        conversations.messages_repo,
        "list_messages",
        lambda session_id, limit=50, cursor=None: listed.append(session_id),
    )
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event(
            "GET /v1/conversations/{sessionId}/messages",
            path_parameters=path,
            claims={"sub": "user-2"},
        )
    )
    assert response["statusCode"] == 404
    assert listed == []


def test_list_messages_refuse_limit_invalide(fake_conversations):
    path = {"sessionId": CONVERSATION["sessionId"]}
    response = handle_request(
        event(
            "GET /v1/conversations/{sessionId}/messages",
            path_parameters=path,
            query_string_parameters={"limit": "0"},
        )
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
