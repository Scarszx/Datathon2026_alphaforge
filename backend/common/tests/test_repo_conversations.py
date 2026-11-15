"""Tests de repositories/conversations.py (moto)."""

import itertools

import pytest

from backend.common.http import ApiError
from backend.common.repositories import _dynamo, conversations


@pytest.fixture
def tick(monkeypatch):
    """Horloge déterministe : chaque appel avance d'une seconde."""
    seconds = itertools.count()

    def fake_now():
        s = next(seconds)
        return f"2026-11-14T10:{s // 60:02d}:{s % 60:02d}Z"

    monkeypatch.setattr(_dynamo, "now_iso", fake_now)


def test_create_conversation(dynamo):
    conv = conversations.create_conversation("u1", "Mon portefeuille")
    assert set(conv) == {"sessionId", "title", "createdAt", "updatedAt"}
    assert conv["title"] == "Mon portefeuille"
    assert conv["createdAt"] == conv["updatedAt"]
    assert len(conv["sessionId"]) == 36


def test_create_conversation_sans_titre(dynamo):
    assert conversations.create_conversation("u1")["title"] is None


def test_get_conversation(dynamo):
    conv = conversations.create_conversation("u1", "A")
    assert conversations.get_conversation("u1", conv["sessionId"]) == conv
    assert conversations.get_conversation("u1", "inexistante") is None


def test_list_conversations_plus_recentes_d_abord(dynamo, tick):
    ids = [conversations.create_conversation("u1", f"c{i}")["sessionId"] for i in range(3)]
    page = conversations.list_conversations("u1")
    assert [c["sessionId"] for c in page["items"]] == ids[::-1]
    assert page["nextCursor"] is None


def test_touch_conversation_fait_remonter(dynamo, tick):
    first = conversations.create_conversation("u1", "ancienne")
    conversations.create_conversation("u1", "récente")
    conversations.touch_conversation("u1", first["sessionId"])
    page = conversations.list_conversations("u1")
    assert page["items"][0]["sessionId"] == first["sessionId"]
    assert page["items"][0]["updatedAt"] > first["updatedAt"]


def test_touch_conversation_absente(dynamo):
    with pytest.raises(ApiError) as err:
        conversations.touch_conversation("u1", "inexistante")
    assert err.value.code == "CONVERSATION_NOT_FOUND"
    assert conversations.list_conversations("u1")["items"] == []


def test_list_conversations_pagination(dynamo, tick):
    ids = [conversations.create_conversation("u1", f"c{i}")["sessionId"] for i in range(5)]
    seen, cursor = [], None
    for _ in range(3):
        page = conversations.list_conversations("u1", limit=2, cursor=cursor)
        assert len(page["items"]) <= 2
        seen += [c["sessionId"] for c in page["items"]]
        cursor = page["nextCursor"]
        if cursor is None:
            break
    assert seen == ids[::-1]
    assert cursor is None


@pytest.mark.parametrize("cursor", ["pas-du-base64!!", "e30", "WyJhIl0"])
def test_list_conversations_curseur_invalide(dynamo, cursor):
    with pytest.raises(ApiError) as err:
        conversations.list_conversations("u1", cursor=cursor)
    assert err.value.code == "VALIDATION_ERROR"


def test_curseur_d_un_autre_utilisateur_refuse(dynamo, tick):
    for i in range(3):
        conversations.create_conversation("u1", f"c{i}")
    cursor = conversations.list_conversations("u1", limit=1)["nextCursor"]
    with pytest.raises(ApiError) as err:
        conversations.list_conversations("u2", cursor=cursor)
    assert err.value.code == "VALIDATION_ERROR"


def test_rename_conversation(dynamo):
    conv = conversations.create_conversation("u1", "A")
    renamed = conversations.rename_conversation("u1", conv["sessionId"], "B")
    assert renamed["title"] == "B"
    assert renamed["updatedAt"] == conv["updatedAt"]
    assert conversations.get_conversation("u1", conv["sessionId"])["title"] == "B"


def test_rename_conversation_absente(dynamo):
    with pytest.raises(ApiError) as err:
        conversations.rename_conversation("u1", "inexistante", "B")
    assert err.value.code == "CONVERSATION_NOT_FOUND"


def test_delete_conversation(dynamo):
    conv = conversations.create_conversation("u1", "A")
    conversations.delete_conversation("u1", conv["sessionId"])
    assert conversations.get_conversation("u1", conv["sessionId"]) is None
    with pytest.raises(ApiError) as err:
        conversations.delete_conversation("u1", conv["sessionId"])
    assert err.value.code == "CONVERSATION_NOT_FOUND"


def test_isolation_entre_utilisateurs(dynamo):
    conv = conversations.create_conversation("u1", "secret")
    sid = conv["sessionId"]
    assert conversations.get_conversation("u2", sid) is None
    assert conversations.list_conversations("u2")["items"] == []
    for action in (
        lambda: conversations.rename_conversation("u2", sid, "piratée"),
        lambda: conversations.touch_conversation("u2", sid),
        lambda: conversations.delete_conversation("u2", sid),
    ):
        with pytest.raises(ApiError) as err:
            action()
        assert err.value.code == "CONVERSATION_NOT_FOUND"
    assert conversations.get_conversation("u1", sid) == conv
    assert conversations.get_conversation("u2", sid) is None


def test_set_user_language(dynamo):
    conv = conversations.create_conversation("u1", "t")
    assert "userLanguage" not in conv
    conversations.set_user_language("u1", conv["sessionId"], "fr")
    stored = conversations.get_conversation("u1", conv["sessionId"])
    assert stored["userLanguage"] == "fr"
    assert stored["updatedAt"] == conv["updatedAt"]


def test_set_user_language_conversation_d_un_autre_utilisateur(dynamo):
    conv = conversations.create_conversation("u1", "t")
    with pytest.raises(ApiError) as exc:
        conversations.set_user_language("u2", conv["sessionId"], "fr")
    assert exc.value.code == "CONVERSATION_NOT_FOUND"
