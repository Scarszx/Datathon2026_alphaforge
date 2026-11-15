"""Routes /portfolios et /portfolios/{portfolioId}/holdings.

Le portefeuille 'main' est créé au premier GET. Un portefeuille d'un autre
utilisateur est invisible (404). Le front envoie l'état complet de sa table :
la liste est remplacée, jamais fusionnée.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.api.validation import (
    parse_json_body,
    path_parameter,
    validate_holdings,
)
from backend.common.http import ApiError, json_response
from backend.common.repositories import portfolios as repo

def _not_found() -> ApiError:
    """Nouvelle erreur à chaque appel : ne pas partager le requestId."""
    return ApiError("PORTFOLIO_NOT_FOUND", "Portefeuille inconnu.")


def list_portfolios(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """GET /v1/portfolios : crée 'main' vide s'il n'existe pas, puis liste."""
    repo.ensure_main_portfolio(user_id)
    return json_response(200, {"items": repo.list_portfolios(user_id)})


def put_holdings(
    event: dict[str, Any],
    user_id: str,
    ticker_validator: Callable[[list[str]], None],
) -> dict[str, Any]:
    """PUT /v1/portfolios/{portfolioId}/holdings : remplace les positions.

    Le corps est validé d'abord, la propriété ensuite, et seulement après les
    tickers sont vérifiés contre l'univers injecté (S3 en production, liste
    fixe en test).
    """
    holdings = validate_holdings(parse_json_body(event))
    portfolio_id = path_parameter(event, "portfolioId")
    if repo.get_portfolio(user_id, portfolio_id) is None:
        raise _not_found()
    ticker_validator([holding["ticker"] for holding in holdings])
    portfolio = repo.replace_holdings(user_id, portfolio_id, holdings)
    return json_response(200, portfolio)
