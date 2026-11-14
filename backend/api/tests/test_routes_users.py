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
        "riskLevel": "high",
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


@pytest.mark.parametrize(
    "profile",
    [
        {},
        {"riskLevel": "extreme", "horizonMinYears": 15, "objective": "x"},
        {"riskLevel": "high", "horizonMinYears": "15", "objective": "x"},
        {"riskLevel": "high", "horizonMinYears": 15, "objective": 12},
        {"riskLevel": "high", "horizonMinYears": 15, "objective": "x", "typo": True},
        {
            "riskLevel": "high",
            "horizonMinYears": 15,
            "horizonMaxYears": True,
            "objective": "x",
        },
        {
            "riskLevel": "high",
            "horizonMinYears": 15,
            "objective": "x",
            "constraints": ["ok", 12],
        },
    ],
)
def test_put_profile_refuse_les_corps_invalides(fake_users, profile):
    response = handle_request(event("PUT /v1/me/profile", body=profile))
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_users["put"] == []
    assert fake_users["update"] == []
