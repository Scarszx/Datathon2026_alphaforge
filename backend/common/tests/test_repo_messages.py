"""Tests de repositories/messages.py (moto)."""

import pytest

from backend.common.http import ApiError
from backend.common.repositories import messages

EXPLANATION = {
    "sources": [{"id": "prices_daily", "dataset": "prices/RY.TO.parquet@2026-11-12"}],
    "assumptions": ["volatilité annualisée sur 252 jours"],
    "limitations": ["le rendement passé ne prédit pas le futur"],
    "steps": [
        {
            "agentId": "agent-analyst",
            "tool": "compute_metrics",
            "params": {"tickers": ["RY.TO"], "weight": 0.25},
            "status": "ok",
            "durationMs": 120,
        }
    ],
    "checks": [],
}


def test_put_message_utilisateur(dynamo):
    msg = messages.put_message("s1", "u1", "user", "Bonjour", "done")
    assert set(msg) == {"messageId", "sessionId", "role", "content", "status", "createdAt"}
    assert msg["sessionId"] == "s1"
    assert len(msg["messageId"]) == 26  # ULID


def test_put_message_assistant_avec_explanation(dynamo):
    msg = messages.put_message("s1", "u1", "assistant", "Réponse", "done", explanation=EXPLANATION)
    assert msg["explanation"] == EXPLANATION
    stored = messages.list_messages("s1")["items"][0]
    assert stored["explanation"] == EXPLANATION
    assert stored["explanation"]["steps"][0]["params"]["weight"] == 0.25
    assert "userId" not in stored


def test_put_message_message_id_fourni(dynamo):
    msg = messages.put_message("s1", "u1", "user", "x", "pending", message_id="01J000000000000000000000AA")
    assert msg["messageId"] == "01J000000000000000000000AA"


@pytest.mark.parametrize(
    "role,status,explanation",
    [("system", "done", None), ("user", "ok", None), ("user", "done", {"steps": []})],
)
def test_put_message_valeurs_invalides(dynamo, role, status, explanation):
    with pytest.raises(ValueError):
        messages.put_message("s1", "u1", role, "x", status, explanation=explanation)


def test_list_messages_ordre_chronologique(dynamo):
    ids = [messages.put_message("s1", "u1", "user", f"m{i}", "done")["messageId"] for i in range(4)]
    page = messages.list_messages("s1")
    assert [m["messageId"] for m in page["items"]] == ids
    assert [m["content"] for m in page["items"]] == ["m0", "m1", "m2", "m3"]
    assert page["nextCursor"] is None


def test_list_messages_pagination(dynamo):
    ids = [messages.put_message("s1", "u1", "user", f"m{i}", "done")["messageId"] for i in range(5)]
    seen, cursor = [], None
    while True:
        page = messages.list_messages("s1", limit=2, cursor=cursor)
        assert len(page["items"]) <= 2
        seen += [m["messageId"] for m in page["items"]]
        cursor = page["nextCursor"]
        if cursor is None:
            break
    assert seen == ids


def test_list_messages_curseur_invalide_ou_d_une_autre_session(dynamo):
    for i in range(3):
        messages.put_message("s1", "u1", "user", f"m{i}", "done")
    cursor = messages.list_messages("s1", limit=1)["nextCursor"]
    for bad in ("%%%", cursor and "x" + cursor):
        with pytest.raises(ApiError):
            messages.list_messages("s1", cursor=bad)
    with pytest.raises(ApiError) as err:
        messages.list_messages("s2", cursor=cursor)
    assert err.value.code == "VALIDATION_ERROR"


def test_list_messages_isole_par_session(dynamo):
    messages.put_message("s1", "u1", "user", "a", "done")
    messages.put_message("s2", "u2", "user", "b", "done")
    assert [m["content"] for m in messages.list_messages("s1")["items"]] == ["a"]
    assert [m["content"] for m in messages.list_messages("s2")["items"]] == ["b"]


def test_delete_messages(dynamo):
    for i in range(30):
        messages.put_message("s1", "u1", "user", f"m{i}", "done")
    messages.put_message("s2", "u1", "user", "garder", "done")
    messages.delete_messages("s1")
    assert messages.list_messages("s1")["items"] == []
    assert len(messages.list_messages("s2")["items"]) == 1


def test_delete_messages_session_vide(dynamo):
    messages.delete_messages("vide")
