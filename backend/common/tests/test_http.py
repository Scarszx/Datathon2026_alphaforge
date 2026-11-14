"""Tests de backend/common/http.py : réponses JSON, CORS, format d'erreur du contrat."""

import json

import pytest

from backend.common import http


def test_json_response():
    reponse = http.json_response(200, {"ok": True, "msg": "ça marche"})
    assert reponse["statusCode"] == 200
    assert reponse["headers"]["Content-Type"].startswith("application/json")
    assert reponse["headers"]["Access-Control-Allow-Origin"]
    assert json.loads(reponse["body"]) == {"ok": True, "msg": "ça marche"}
    # accents préservés (UTF-8 lisible), pas de séquence \u00e7a
    assert "ça marche" in reponse["body"]


def test_codes_et_statuts_du_contrat():
    attendu = {
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "VALIDATION_ERROR": 400,
        "CONVERSATION_NOT_FOUND": 404,
        "PORTFOLIO_NOT_FOUND": 404,
        "ASSET_NOT_FOUND": 404,
        "AGENT_TIMEOUT": 504,
        "INTERNAL": 500,
    }
    assert http.HTTP_STATUS_BY_CODE == attendu


def test_error_response_au_format_du_contrat():
    erreur = http.ApiError(
        "VALIDATION_ERROR", "content dépasse 2000 caractères", request_id="req-123"
    )
    reponse = http.error_response(erreur)
    assert reponse["statusCode"] == 400
    corps = json.loads(reponse["body"])
    assert corps["error"] == {
        "code": "VALIDATION_ERROR",
        "message": "content dépasse 2000 caractères",
        "requestId": "req-123",
    }


def test_erreur_sans_request_id():
    reponse = http.error_response(http.ApiError("INTERNAL", "boum"))
    assert json.loads(reponse["body"])["error"]["requestId"] is None


def test_code_inconnu_refuse():
    with pytest.raises(ValueError, match="inconnu du contrat"):
        http.ApiError("MAUVAIS_CODE", "…")


def test_request_id_depuis_evenement():
    evenement = {"requestContext": {"requestId": "abc-42"}}
    assert http.request_id_from_event(evenement) == "abc-42"
    assert http.request_id_from_event({}) is None
