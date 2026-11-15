"""Tests de backend/common/auth.py : userId = claim sub du JWT (payload v2)."""

import pytest

from backend.common import auth
from backend.common.http import ApiError


def evenement(claims=None, authorizer=None):
    """Événement API Gateway HTTP API (payload v2) factice."""
    contexte: dict = {"requestId": "req-1"}
    if authorizer is not None:
        contexte["authorizer"] = authorizer
    return {"requestContext": contexte}


def test_user_id_depuis_le_claim_sub():
    evenement_jwt = evenement(
        authorizer={"jwt": {"claims": {"sub": "user-amira", "username": "amira"}}}
    )
    assert auth.get_user_id(evenement_jwt) == "user-amira"


def test_evenement_sans_jwt():
    with pytest.raises(ApiError) as excinfo:
        auth.get_user_id(evenement())
    assert excinfo.value.code == "UNAUTHORIZED"


def test_jwt_sans_claim_sub():
    evenement_jwt = evenement(authorizer={"jwt": {"claims": {"username": "amira"}}})
    with pytest.raises(ApiError) as excinfo:
        auth.get_user_id(evenement_jwt)
    assert excinfo.value.code == "UNAUTHORIZED"
    assert excinfo.value.message
