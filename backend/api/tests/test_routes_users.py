"""Tests des routes /me et /me/profile (repositories simulés)."""

from __future__ import annotations

import pytest

from backend.api.app import handle_request
from backend.api.routes import users

from .conftest import body_of, event


@pytest.fixture
def fake_users(monkeypatch):
    """Replacements des fonctions du repository Users."""
    calls: dict[str, list] = {"put": [], "update": []}

    def put_user_if_absent(
        user_id: str,
        username: str,
        display_name: str | None = None,
        base_currency: str = "CAD",
    ):
        calls["put"].append(
            {
                "userId": user_id,
                "username": username,
                "displayName": display_name,
                "baseCurrency": base_currency,
            }
        )
        return {
            "userId": user_id,
            "username": username,
            "displayName": display_name,
            "baseCurrency": base_currency,
            "investorProfile": None,
        }

    def update_investor_profile(user_id: str, investor_profile: dict):
        calls["update"].append({"userId": user_id, "profile": investor_profile})
        return {
            "userId": user_id,
            "username": "amira",
            "displayName": "Amira",
            "baseCurrency": "CAD",
            "investorProfile": investor_profile,
        }

    monkeypatch.setattr(users.repo, "get_user", lambda user_id: None)
    monkeypatch.setattr(users.repo, "put_user_if_absent", put_user_if_absent)
    monkeypatch.setattr(
        users.repo, "update_investor_profile", update_investor_profile
    )
    return calls


def test_get_me_cree_le_profil_au_premier_appel(fake_users):
    response = handle_request(event("GET /v1/me"))
    assert response["statusCode"] == 200
    assert body_of(response) == {
        "userId": "user-1",
        "username": "amira",
        "displayName": "Amira",
        "baseCurrency": "CAD",
        "investorProfile": None,
    }
    assert fake_users["put"] == [
        {
            "userId": "user-1",
            "username": "amira",
            "displayName": "Amira",
            "baseCurrency": "CAD",
        }
    ]


def test_get_me_sans_claim_username_replie_sur_sub(fake_users, monkeypatch):
    monkeypatch.setattr(users.repo, "get_user", lambda user_id: None)
    response = handle_request(
        event("GET /v1/me", claims={"sub": "user-fallback", "name": "Amira"})
    )
    assert body_of(response)["username"] == "user-fallback"


def test_put_profile_valide_et_remplace_le_profil(fake_users):
    profile = {
        "riskTolerance": 5,
        "riskCapacity": 4,
        "province": "QC",
        "horizonMinYears": 15,
        "horizonMaxYears": 30,
        "objective": "croissance à long terme",
        "constraints": ["diversification minimale"],
        "preferences": ["IA"],
        "excludedAssetClasses": [],
    }
    response = handle_request(event("PUT /v1/me/profile", body=profile))
    assert response["statusCode"] == 200
    assert body_of(response)["investorProfile"] == profile
    assert fake_users["update"] == [
        {"userId": "user-1", "profile": profile}
    ]


def _profile(**fields):
    base = {"riskTolerance": 4, "riskCapacity": 3, "horizonMinYears": 15, "objective": "x"}
    base.update(fields)
    return {k: v for k, v in base.items() if v is not None}


@pytest.mark.parametrize(
    "profile",
    [
        {},
        _profile(riskTolerance=None),  # tolérance obligatoire (lot C)
        _profile(riskCapacity=None),  # capacité obligatoire (lot C)
        {"riskLevel": "high", "horizonMinYears": 15, "objective": "x"},  # l'ancien niveau seul ne suffit plus
        _profile(horizonMinYears="15"),
        _profile(objective=12),
        _profile(typo=True),
        _profile(horizonMaxYears=True),
        _profile(constraints=["ok", 12]),
        _profile(riskTolerance=0),
        _profile(riskCapacity=6),
        _profile(riskCapacity=2.5),
        _profile(riskLevel=3),  # non chaîne
        _profile(province="CA"),
        _profile(province="US"),
    ],
)
def test_put_profile_refuse_les_corps_invalides(fake_users, profile):
    response = handle_request(event("PUT /v1/me/profile", body=profile))
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_users["put"] == []
    assert fake_users["update"] == []


def test_put_profile_sans_risk_level_est_accepte(fake_users):
    response = handle_request(event("PUT /v1/me/profile", body=_profile()))
    assert response["statusCode"] == 200
    assert "riskLevel" not in body_of(response)["investorProfile"]


def test_put_profile_risk_level_ancien_client_accepte_puis_ignore(fake_users):
    for legacy in ("high", "extreme"):
        response = handle_request(event("PUT /v1/me/profile", body=_profile(riskLevel=legacy)))
        assert response["statusCode"] == 200
        assert "riskLevel" not in body_of(response)["investorProfile"]
    assert all("riskLevel" not in call["profile"] for call in fake_users["update"])
