"""Tests des routes /conversations/{sessionId}/mandates (repositories et tickers simulés)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.api.app import handle_request
from backend.api.routes import mandates

from .conftest import body_of, event

SESSION_ID = "5dd2f4a1-8c34-4b28-8a52-c42b7892d3f1"
CONVERSATION = {
    "sessionId": SESSION_ID,
    "title": "Simulation Robert",
    "createdAt": "2026-11-14T09:30:00Z",
    "updatedAt": "2026-11-14T09:35:00Z",
}


def valid_mandate_body(**overrides: Any) -> dict[str, Any]:
    """Corps schema-mandate-create-request valide par défaut."""
    base: dict[str, Any] = {
        "portfolioId": "main",
        "mode": "add_asset",
        "objective": "project",
        "objectiveDetail": "buy a condo in 3 years",
        "horizonYears": 3,
        "riskTolerance": 3,
        "riskCapacity": 1,
        "constraints": ["no leverage"],
        "preferences": {
            "esg": False,
            "excludedSectors": [],
            "excludedAssetClasses": ["crypto"],
        },
        "province": "QC",
        "userLanguage": "fr",
        "operations": [
            {
                "action": "add",
                "ticker": "RY.TO",
                "amount": 15000,
                "currency": "CAD",
            }
        ],
        "fieldSources": {
            "horizonYears": "user_answer",
            "riskTolerance": "persona",
            "riskCapacity": "user_answer",
        },
    }
    base.update(overrides)
    return base


@pytest.fixture
def fake_mandate_repos(monkeypatch):
    """Simule les repositories conversations et analyses en mémoire."""
    stored: list[dict[str, Any]] = []

    def get_conversation(user_id: str, session_id: str):
        if user_id == "user-1" and session_id == SESSION_ID:
            return CONVERSATION
        return None

    def get_latest_mandate(session_id: str, user_id: str):
        owned = [
            item
            for item in stored
            if item["sessionId"] == session_id and item["_userId"] == user_id
        ]
        return owned[-1]["public"] if owned else None

    def put_mandate(session_id: str, user_id: str, mandate_record: dict[str, Any]):
        version = len([item for item in stored if item["sessionId"] == session_id]) + 1
        public = {
            "sessionId": session_id,
            "version": version,
            "mandate": mandate_record["mandate"],
            "riskProfile": mandate_record["riskProfile"],
            "effectiveMaxLossPct": mandate_record["effectiveMaxLossPct"],
            "warnings": mandate_record["warnings"],
            "changedFields": mandate_record["changedFields"],
            "confirmedAt": mandate_record["confirmedAt"],
        }
        stored.append({"sessionId": session_id, "_userId": user_id, "public": public})
        return public

    def list_mandates(session_id: str, user_id: str):
        return [
            item["public"]
            for item in reversed(stored)
            if item["sessionId"] == session_id and item["_userId"] == user_id
        ]

    monkeypatch.setattr(
        mandates.conversations_repo, "get_conversation", get_conversation
    )
    monkeypatch.setattr(
        mandates.analyses_repo, "get_latest_mandate", get_latest_mandate
    )
    monkeypatch.setattr(mandates.analyses_repo, "put_mandate", put_mandate)
    monkeypatch.setattr(mandates.analyses_repo, "list_mandates", list_mandates)
    return stored


def test_create_mandate_calcule_risk_profile_et_perte_par_defaut(
    fake_mandate_repos, ticker_validator
):
    body = valid_mandate_body()
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    created = body_of(response)
    assert set(created) == {
        "sessionId",
        "version",
        "mandate",
        "riskProfile",
        "effectiveMaxLossPct",
        "warnings",
        "changedFields",
        "confirmedAt",
    }
    assert created["sessionId"] == SESSION_ID
    assert created["version"] == 1
    assert created["riskProfile"] == 1  # min(3, 1) (R1)
    assert created["effectiveMaxLossPct"] == 20  # 3 ans -> palier 3-8 ans = 20 %
    assert created["warnings"] == []
    assert created["changedFields"] == []
    assert ticker_validator.calls == [["RY.TO"]]


@pytest.mark.parametrize(
    ("horizon_years", "expected_loss_pct"),
    [
        (1, 10),
        (2.5, 10),
        (3, 20),
        (8, 20),
        (10, 35),
        (20, 35),
    ],
)
def test_default_max_loss_pct_suit_les_paliers_d_horizon(
    fake_mandate_repos, ticker_validator, horizon_years, expected_loss_pct
):
    body = valid_mandate_body(
        objective="income",
        objectiveDetail="regular income",
        horizonYears=horizon_years,
    )
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    assert body_of(response)["effectiveMaxLossPct"] == expected_loss_pct


def test_create_mandate_conserve_max_acceptable_loss_saisi(
    fake_mandate_repos, ticker_validator
):
    body = valid_mandate_body(maxAcceptableLossPct=12.5)
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    assert body_of(response)["effectiveMaxLossPct"] == 12.5


def test_create_mandate_versions_successives_et_changed_fields(
    fake_mandate_repos, ticker_validator
):
    path = {"sessionId": SESSION_ID}
    v1_body = valid_mandate_body()
    r1 = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters=path,
            body=v1_body,
        ),
        ticker_validator=ticker_validator,
    )
    assert body_of(r1)["version"] == 1
    assert body_of(r1)["changedFields"] == []

    # Curseur « et si » : modification de horizonYears et maxAcceptableLossPct
    v2_body = valid_mandate_body(
        horizonYears=10,
        maxAcceptableLossPct=25,
        fieldSources={
            "horizonYears": "slider",
            "maxAcceptableLossPct": "slider",
        },
    )
    r2 = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters=path,
            body=v2_body,
        ),
        ticker_validator=ticker_validator,
    )
    created_v2 = body_of(r2)
    assert created_v2["version"] == 2
    assert created_v2["changedFields"] == ["horizonYears", "maxAcceptableLossPct"]

    # Liste des mandats : plus récente d'abord (v2 puis v1)
    list_resp = handle_request(
        event("GET /v1/conversations/{sessionId}/mandates", path_parameters=path)
    )
    assert list_resp["statusCode"] == 200
    items = body_of(list_resp)["items"]
    assert [item["version"] for item in items] == [2, 1]


def test_create_mandate_detecte_les_incoherences_dans_warnings(
    fake_mandate_repos, ticker_validator
):
    # Projet à 3 ans mais horizon réglé à 10 ans
    body = valid_mandate_body(
        objective="project",
        objectiveDetail="buy a condo in 3 years",
        horizonYears=10,
    )
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    warnings = body_of(response)["warnings"]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "HORIZON_EXCEEDS_PROJECT"
    assert "exceeds the project timeline" in warnings[0]["message"]
    assert warnings[0]["params"] == {"horizonYears": 10, "projectYears": 3}


def test_create_mandate_warnings_croissance_court_terme_et_perte_elevee(
    fake_mandate_repos, ticker_validator
):
    body = valid_mandate_body(
        objective="growth",
        objectiveDetail="aggressive growth",
        horizonYears=2,
        maxAcceptableLossPct=25,
    )
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    warnings = body_of(response)["warnings"]
    assert [w["code"] for w in warnings] == ["SHORT_HORIZON_GROWTH", "LOSS_EXCEEDS_DEFAULT"]
    assert all(isinstance(w["message"], str) and w["message"] for w in warnings)


def test_create_mandate_mode_diagnose_valide_subject_ticker(
    fake_mandate_repos, ticker_validator
):
    body = valid_mandate_body(
        mode="diagnose",
        operations=[],
        subjectTicker="AAPL",
    )
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    assert ticker_validator.calls == [["AAPL"]]


def test_create_mandate_refuse_ticker_inconnu_en_validation_error(
    fake_mandate_repos, ticker_validator
):
    body = valid_mandate_body(
        operations=[{"action": "add", "ticker": "INCONNU", "amount": 1000}]
    )
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert "INCONNU" in body_of(response)["error"]["message"]
    assert fake_mandate_repos == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"portfolioId": ""},
        {"mode": "invalid_mode"},
        {"objective": "speculation"},
        {"horizonYears": 0},
        {"horizonYears": -3},
        {"horizonYears": True},
        {"riskTolerance": 0},
        {"riskTolerance": 6},
        {"riskTolerance": False},
        {"riskCapacity": 0},
        {"riskCapacity": 6},
        {"province": "CA"},  # CA exclu des provinces de mandat
        {"province": "NY"},
        {"userLanguage": "fra"},
        {"userLanguage": "FR"},
        {"userLanguage": "12"},
        {"maxAcceptableLossPct": 0},
        {"maxAcceptableLossPct": 120},
        {"preferences": {"esg": "yes"}},
        {"preferences": {"unknown": True}},
        {"operations": [{"action": "buy", "ticker": "RY.TO"}]},
        {"operations": [{"action": "add", "ticker": ""}]},
        {"operations": [{"action": "add", "ticker": "RY.TO", "amount": -10}]},
        {"operations": [{"action": "set_weight", "ticker": "RY.TO", "weight": 150}]},
        {"operations": [{"action": "add", "ticker": "RY.TO", "currency": "EUR"}]},
        {"fieldSources": {"horizonYears": "invalid_source"}},
        {"champInconnu": 123},
    ],
)
def test_create_mandate_refuse_les_corps_invalides(
    fake_mandate_repos, ticker_validator, overrides
):
    body = valid_mandate_body(**overrides)
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=body,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_mandate_repos == []


def test_create_et_list_mandates_verifient_la_propriete_de_la_conversation(
    fake_mandate_repos, ticker_validator
):
    path = {"sessionId": SESSION_ID}
    post_resp = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters=path,
            body=valid_mandate_body(),
            claims={"sub": "user-2"},
        ),
        ticker_validator=ticker_validator,
    )
    assert post_resp["statusCode"] == 404
    assert body_of(post_resp)["error"]["code"] == "CONVERSATION_NOT_FOUND"
    assert ticker_validator.calls == []
    assert fake_mandate_repos == []

    get_resp = handle_request(
        event(
            "GET /v1/conversations/{sessionId}/mandates",
            path_parameters=path,
            claims={"sub": "user-2"},
        )
    )
    assert get_resp["statusCode"] == 404
    assert body_of(get_resp)["error"]["code"] == "CONVERSATION_NOT_FOUND"


def test_rules_config_path_personnalise_est_pris_en_compte(
    fake_mandate_repos, ticker_validator, tmp_path, monkeypatch
):
    custom_cfg = tmp_path / "custom_rules.json"
    custom_cfg.write_text(
        json.dumps(
            {
                "maxAcceptableLossPctByHorizon": [
                    {"maxHorizonYearsExclusive": 3, "maxAcceptableLossPct": 8},
                    {"maxHorizonYearsInclusive": 8, "maxAcceptableLossPct": 15},
                    {"defaultMaxAcceptableLossPct": 30},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("RULES_CONFIG_PATH", str(custom_cfg))
    response = handle_request(
        event(
            "POST /v1/conversations/{sessionId}/mandates",
            path_parameters={"sessionId": SESSION_ID},
            body=valid_mandate_body(horizonYears=5),
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 201
    assert body_of(response)["effectiveMaxLossPct"] == 15


def test_create_mandate_compare_category_choisie_par_l_utilisateur(fake_mandate_repos, ticker_validator):
    def post(**overrides):
        return handle_request(
            event("POST /v1/conversations/{sessionId}/mandates", path_parameters={"sessionId": SESSION_ID},
                  body=valid_mandate_body(**overrides)),
            ticker_validator=ticker_validator,
        )

    assert "compareCategory" not in body_of(post())["mandate"]
    ok = post(compareCategory="aggregate-bonds")
    assert ok["statusCode"] == 201 and body_of(ok)["mandate"]["compareCategory"] == "aggregate-bonds"
    # Demander la comparaison crée une nouvelle version et le champ figure parmi les champs modifiés.
    assert body_of(ok)["version"] == 2 and "compareCategory" in body_of(ok)["changedFields"]
    for bad in ("XBB.TO", "bonds", 3, True):
        assert post(compareCategory=bad)["statusCode"] == 400
