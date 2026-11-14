"""Tests du handler : routage, authentification et erreurs génériques."""

from __future__ import annotations

from backend.api.app import ROUTES, handle_request
from backend.common.http import HTTP_STATUS_BY_CODE

from .conftest import body_of, event


def test_routes_couvrivent_les_dix_routes_du_contrat():
    assert set(ROUTES) == {
        "GET /v1/me",
        "PUT /v1/me/profile",
        "GET /v1/conversations",
        "POST /v1/conversations",
        "PATCH /v1/conversations/{sessionId}",
        "DELETE /v1/conversations/{sessionId}",
        "GET /v1/conversations/{sessionId}/messages",
        "GET /v1/portfolios",
        "PUT /v1/portfolios/{portfolioId}/holdings",
        "GET /v1/agents",
    }


def test_requete_sans_jwt_est_refusee():
    response = handle_request(event("GET /v1/me", claims=None))
    assert response["statusCode"] == 401
    assert body_of(response)["error"]["code"] == "UNAUTHORIZED"
    assert body_of(response)["error"]["requestId"] == "request-1"


def test_route_inconnue_recoit_une_erreur_de_validation():
    response = handle_request(event("GET /v1/inconnue"))
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"


def test_corps_json_invalide_est_une_erreur_de_validation():
    invalid = event("PUT /v1/me/profile", body="{pas du json")
    response = handle_request(invalid)
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"


def test_les_codes_restent_ceux_du_contrat():
    assert HTTP_STATUS_BY_CODE["ASSET_NOT_FOUND"] == 404
    assert HTTP_STATUS_BY_CODE["PORTFOLIO_NOT_FOUND"] == 404
