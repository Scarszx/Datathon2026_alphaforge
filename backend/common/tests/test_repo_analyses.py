"""Tests WS2b du repository Analyses (moto, sans compte AWS)."""

from __future__ import annotations

import boto3
import pytest

from backend.common.http import ApiError
from backend.common.repositories import analyses

TABLE = "Analyses-test"
SESSION = "sess-1"
ALICE = "user-alice"
BOB = "user-bob"


@pytest.fixture
def table(dynamo, monkeypatch):
    """Table Analyses simulée (le conftest partagé ne crée que les tables v0.3)."""
    monkeypatch.setenv("ANALYSES_TABLE", TABLE)
    boto3.client("dynamodb").create_table(
        TableName=TABLE,
        KeySchema=[
            {"AttributeName": "sessionId", "KeyType": "HASH"},
            {"AttributeName": "itemKey", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "sessionId", "AttributeType": "S"},
            {"AttributeName": "itemKey", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return boto3.resource("dynamodb").Table(TABLE)


def _mandate(**overrides):
    body = {
        "mandate": {
            "portfolioId": "main",
            "mode": "add_asset",
            "objective": "growth",
            "horizonYears": 10,
            "riskTolerance": 4,
            "riskCapacity": 3,
            "province": "QC",
            "userLanguage": "fr",
        },
        "riskProfile": 3,
        "effectiveMaxLossPct": 25.5,
        "warnings": [],
        "changedFields": [],
        "confirmedAt": "2026-11-14T09:30:00Z",
    }
    body.update(overrides)
    return body


def _run(run_id="01JRUN0000000000000000000A", **overrides):
    body = {
        "runId": run_id,
        "sessionId": SESSION,
        "mandateVersion": 1,
        "status": "partial",
        "datasetVersion": "2026-11-12",
        "userLanguage": "fr",
        "scenarios": [{"index": 0, "label": "Actuel", "verdict": "pass"}],
        "verdicts": [{"rule": "R1", "status": "pass", "reasonCode": "OK"}],
        "evidence": [{"id": "EV-01", "kind": "metric", "label": "Vol", "value": 0.152, "source": "ds"}],
        "createdAt": "2026-11-14T09:31:00Z",
    }
    body.update(overrides)
    return body


INTERNAL = {"userId", "type", "itemKey"}


# --- Mandats ---------------------------------------------------------------


def test_put_mandate_attribue_les_versions(table):
    m1 = analyses.put_mandate(SESSION, ALICE, _mandate())
    m2 = analyses.put_mandate(SESSION, ALICE, _mandate(changedFields=["horizonYears"]))
    m3 = analyses.put_mandate(SESSION, ALICE, _mandate())
    assert [m1["version"], m2["version"], m3["version"]] == [1, 2, 3]
    assert m1["sessionId"] == SESSION
    assert not INTERNAL & set(m1)
    stored = table.get_item(Key={"sessionId": SESSION, "itemKey": "MANDATE#002"})["Item"]
    assert stored["type"] == "mandate"
    assert stored["userId"] == ALICE
    assert stored["changedFields"] == ["horizonYears"]


def test_put_mandate_ignore_version_et_cles_fournies(table):
    m = analyses.put_mandate(SESSION, ALICE, _mandate(version=42, userId=BOB, itemKey="X"))
    assert m["version"] == 1
    assert analyses.get_mandate(SESSION, ALICE, 1) is not None
    assert analyses.get_mandate(SESSION, BOB, 1) is None


def test_put_mandate_confirmed_at_par_defaut(table):
    body = _mandate()
    del body["confirmedAt"]
    assert analyses.put_mandate(SESSION, ALICE, body)["confirmedAt"].endswith("Z")


def test_get_mandate(table):
    analyses.put_mandate(SESSION, ALICE, _mandate())
    m = analyses.get_mandate(SESSION, ALICE, 1)
    assert m["mandate"]["objective"] == "growth"
    assert m["effectiveMaxLossPct"] == 25.5  # Decimal relu en float
    assert m["mandate"]["horizonYears"] == 10
    assert not INTERNAL & set(m)
    assert analyses.get_mandate(SESSION, ALICE, 2) is None


def test_get_latest_mandate(table):
    assert analyses.get_latest_mandate(SESSION, ALICE) is None
    analyses.put_mandate(SESSION, ALICE, _mandate())
    analyses.put_mandate(SESSION, ALICE, _mandate(riskProfile=2))
    latest = analyses.get_latest_mandate(SESSION, ALICE)
    assert latest["version"] == 2
    assert latest["riskProfile"] == 2


def test_get_latest_mandate_ignore_les_runs(table):
    analyses.put_mandate(SESSION, ALICE, _mandate())
    analyses.put_run(SESSION, ALICE, _run())  # RUN# > MANDATE# en ordre lexical
    assert analyses.get_latest_mandate(SESSION, ALICE)["version"] == 1


def test_list_mandates_plus_recente_dabord(table):
    for _ in range(11):
        analyses.put_mandate(SESSION, ALICE, _mandate())
    analyses.put_run(SESSION, ALICE, _run())
    versions = [m["version"] for m in analyses.list_mandates(SESSION, ALICE)]
    assert versions == list(range(11, 0, -1))  # MANDATE#010 et #011 après #009
    assert analyses.list_mandates("autre-session", ALICE) == []


# --- Concurrence -------------------------------------------------------------


def test_put_mandate_concurrent_reessaie_avec_la_version_suivante(table, monkeypatch):
    analyses.put_mandate(SESSION, ALICE, _mandate(riskProfile=1))
    real = analyses._latest_mandate_item
    calls = {"n": 0}

    def stale_then_real(session_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # lecture périmée : un autre appel a déjà écrit la v1
        return real(session_id)

    monkeypatch.setattr(analyses, "_latest_mandate_item", stale_then_real)
    m = analyses.put_mandate(SESSION, ALICE, _mandate(riskProfile=5))
    assert m["version"] == 2
    assert calls["n"] == 2
    # la v1 d'origine n'a pas été écrasée
    assert analyses.get_mandate(SESSION, ALICE, 1)["riskProfile"] == 1
    assert analyses.get_mandate(SESSION, ALICE, 2)["riskProfile"] == 5


def test_put_mandate_abandonne_apres_trop_de_conflits(table, monkeypatch):
    analyses.put_mandate(SESSION, ALICE, _mandate())
    monkeypatch.setattr(analyses, "_latest_mandate_item", lambda session_id: None)
    with pytest.raises(ApiError) as err:
        analyses.put_mandate(SESSION, ALICE, _mandate())
    assert err.value.code == "INTERNAL"
    assert len(analyses.list_mandates(SESSION, ALICE)) == 1


# --- Runs ------------------------------------------------------------------


def test_put_run_et_get_run(table):
    created = analyses.put_run(SESSION, ALICE, _run())
    assert created["runId"] == "01JRUN0000000000000000000A"
    assert not INTERNAL & set(created)
    run = analyses.get_run(SESSION, ALICE, "01JRUN0000000000000000000A")
    assert run["status"] == "partial"
    assert run["evidence"][0]["value"] == 0.152
    assert run["userLanguage"] == "fr"
    stored = table.get_item(Key={"sessionId": SESSION, "itemKey": "RUN#01JRUN0000000000000000000A"})["Item"]
    assert stored["type"] == "run"
    assert analyses.get_run(SESSION, ALICE, "inconnu") is None


def test_put_run_created_at_par_defaut(table):
    body = _run()
    del body["createdAt"]
    assert analyses.put_run(SESSION, ALICE, body)["createdAt"].endswith("Z")


def test_put_run_refuse_un_doublon(table):
    analyses.put_run(SESSION, ALICE, _run())
    with pytest.raises(ApiError) as err:
        analyses.put_run(SESSION, ALICE, _run(status="done"))
    assert err.value.code == "INTERNAL"
    assert analyses.get_run(SESSION, ALICE, "01JRUN0000000000000000000A")["status"] == "partial"


def test_update_run_partial_vers_done(table):
    analyses.put_run(SESSION, ALICE, _run())
    done = analyses.update_run(
        SESSION,
        ALICE,
        "01JRUN0000000000000000000A",
        {
            "status": "done",
            "narrative": {"sections": [], "language": "fr"},
            "verifier": {
                "placeholdersResolved": 3,
                "placeholdersTotal": 3,
                "handwrittenNumbers": 0,
                "forbiddenPhrases": 0,
                "placeholdersMatch": True,
            },
            "verdicts": [{"rule": "R1", "status": "pass", "reasonCode": "OK", "citations": ["KB-01"]}],
            "completedAt": "2026-11-14T09:32:00Z",
        },
    )
    assert done["status"] == "done"
    assert done["verifier"]["placeholdersMatch"] is True
    assert done["verdicts"][0]["citations"] == ["KB-01"]
    # champs non touchés conservés
    assert done["scenarios"][0]["label"] == "Actuel"
    assert done["createdAt"] == "2026-11-14T09:31:00Z"
    assert not INTERNAL & set(done)
    assert analyses.get_run(SESSION, ALICE, "01JRUN0000000000000000000A") == done


def test_update_run_inconnu(table):
    with pytest.raises(ApiError) as err:
        analyses.update_run(SESSION, ALICE, "inconnu", {"status": "error"})
    assert err.value.code == "RUN_NOT_FOUND"
    # pas d'item fantôme créé
    assert analyses.get_run(SESSION, ALICE, "inconnu") is None


@pytest.mark.parametrize("champ", ["userId", "sessionId", "itemKey", "type", "runId"])
def test_update_run_refuse_les_champs_de_cle(table, champ):
    analyses.put_run(SESSION, ALICE, _run())
    with pytest.raises(ValueError):
        analyses.update_run(SESSION, ALICE, "01JRUN0000000000000000000A", {champ: "x"})


def test_update_run_sans_champ(table):
    analyses.put_run(SESSION, ALICE, _run())
    assert analyses.update_run(SESSION, ALICE, "01JRUN0000000000000000000A", {})["status"] == "partial"
    with pytest.raises(ApiError) as err:
        analyses.update_run(SESSION, ALICE, "inconnu", {})
    assert err.value.code == "RUN_NOT_FOUND"


# --- Suppression -------------------------------------------------------------


def test_delete_analyses(table):
    for _ in range(3):
        analyses.put_mandate(SESSION, ALICE, _mandate())
    analyses.put_run(SESSION, ALICE, _run("RUN-A"))
    analyses.put_run(SESSION, ALICE, _run("RUN-B"))
    analyses.put_mandate("sess-2", ALICE, _mandate())

    analyses.delete_analyses(SESSION, ALICE)

    assert table.query(KeyConditionExpression="sessionId = :s", ExpressionAttributeValues={":s": SESSION})["Count"] == 0
    assert analyses.get_mandate("sess-2", ALICE, 1) is not None
    analyses.delete_analyses("vide", ALICE)  # session vide : sans erreur


# --- Isolation entre utilisateurs ----------------------------------------------


def test_isolation_entre_utilisateurs(table):
    analyses.put_mandate(SESSION, ALICE, _mandate())
    analyses.put_run(SESSION, ALICE, _run())
    run_id = "01JRUN0000000000000000000A"

    assert analyses.get_mandate(SESSION, BOB, 1) is None
    assert analyses.get_latest_mandate(SESSION, BOB) is None
    assert analyses.list_mandates(SESSION, BOB) == []
    assert analyses.get_run(SESSION, BOB, run_id) is None
    with pytest.raises(ApiError) as err:
        analyses.update_run(SESSION, BOB, run_id, {"status": "done"})
    assert err.value.code == "RUN_NOT_FOUND"

    analyses.delete_analyses(SESSION, BOB)
    assert analyses.get_mandate(SESSION, ALICE, 1) is not None
    assert analyses.get_run(SESSION, ALICE, run_id)["status"] == "partial"
