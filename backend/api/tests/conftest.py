"""Fixtures de la Lambda API : événements payload v2 et validateur injecté.

Aucun compte AWS, aucun appel réseau : les repositories et la validation des
tickers sont simulés dans les tests (exigence WS4).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.common.http import ApiError

CLAIMS = {
    "sub": "user-1",
    "cognito:username": "amira",
    "username": "amira",
    "name": "Amira",
}

VALID_TICKERS = frozenset({"RY.TO", "AAPL", "BTC-USD"})


def event(
    route_key: str,
    *,
    path_parameters: dict[str, str] | None = None,
    query_string_parameters: dict[str, str] | None = None,
    body: dict[str, Any] | str | None = None,
    claims: dict[str, Any] | None = CLAIMS,
    request_id: str = "request-1",
) -> dict[str, Any]:
    """Construit un événement HTTP API payload v2 minimal mais fidèle."""
    return {
        "version": "2.0",
        "routeKey": route_key,
        "rawPath": route_key.split(" ", 1)[1],
        "requestContext": {
            "requestId": request_id,
            "authorizer": {"jwt": {"claims": claims or {}}},
        },
        "pathParameters": path_parameters,
        "queryStringParameters": query_string_parameters,
        "body": None if body is None else json.dumps(body, ensure_ascii=False),
        "isBase64Encoded": False,
    }


def body_of(response: dict[str, Any]) -> Any:
    """Corps JSON d'une réponse de test."""
    return json.loads(response["body"])


@pytest.fixture
def ticker_validator():
    """Validateur injectable : enregistre les tickers et applique une liste fixe."""
    calls: list[list[str]] = []

    def validate(tickers: list[str]) -> None:
        calls.append(list(tickers))
        unknown = sorted({ticker for ticker in tickers if ticker not in VALID_TICKERS})
        if unknown:
            raise ApiError("ASSET_NOT_FOUND", f"Ticker inconnu : {unknown[0]}.")

    validate.calls = calls  # type: ignore[attr-defined]
    return validate
