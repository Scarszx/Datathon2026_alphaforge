"""Tests de repositories/users.py (moto)."""

import pytest

from backend.common.http import ApiError
from backend.common.repositories import users

PROFILE = {
    "riskLevel": "moderate",
    "horizonMinYears": 5,
    "horizonMaxYears": 10,
    "objective": "croissance à long terme",
    "constraints": ["pas de levier"],
    "preferences": ["ESG"],
    "excludedAssetClasses": ["crypto"],
}


def test_get_user_absent(dynamo):
    assert users.get_user("u1") is None


def test_put_user_if_absent_cree_l_utilisateur(dynamo):
    user = users.put_user_if_absent("u1", "amira", display_name="Amira", base_currency="USD")
    assert user == {
        "userId": "u1",
        "username": "amira",
        "displayName": "Amira",
        "baseCurrency": "USD",
        "investorProfile": None,
    }
    assert users.get_user("u1") == user


def test_put_user_if_absent_idempotent_sans_ecraser(dynamo):
    users.put_user_if_absent("u1", "amira")
    users.update_investor_profile("u1", PROFILE)
    again = users.put_user_if_absent("u1", "autre-nom", base_currency="USD")
    assert again["username"] == "amira"
    assert again["baseCurrency"] == "CAD"
    assert again["investorProfile"] == PROFILE


def test_update_investor_profile_conserve_les_autres_attributs(dynamo):
    users.put_user_if_absent("u1", "amira", display_name="Amira")
    user = users.update_investor_profile("u1", PROFILE)
    assert user["investorProfile"] == PROFILE
    assert user["displayName"] == "Amira"
    assert user["username"] == "amira"
    assert users.get_user("u1")["investorProfile"] == PROFILE


def test_update_investor_profile_utilisateur_absent(dynamo):
    with pytest.raises(ApiError) as err:
        users.update_investor_profile("inconnu", PROFILE)
    assert err.value.code == "INTERNAL"
    assert users.get_user("inconnu") is None


def test_isolation_entre_utilisateurs(dynamo):
    users.put_user_if_absent("u1", "amira")
    users.put_user_if_absent("u2", "mateo")
    users.update_investor_profile("u1", PROFILE)
    assert users.get_user("u2")["investorProfile"] is None
