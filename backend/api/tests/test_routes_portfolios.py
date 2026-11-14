"""Tests des routes portefeuilles (repositories et tickers simulés)."""

from __future__ import annotations

import pytest

from backend.api.app import handle_request
from backend.api.routes import portfolios
from backend.common.http import ApiError

from .conftest import body_of, event

PORTFOLIO = {
    "portfolioId": "main",
    "name": "Principal",
    "baseCurrency": "CAD",
    "holdings": [{"ticker": "RY.TO", "quantity": 10, "avgCost": 125.5}],
    "updatedAt": "2026-11-14T09:30:00Z",
}


@pytest.fixture
def fake_portfolios(monkeypatch):
    """Replacements du repository Portfolios."""
    calls: dict[str, list] = {"ensure": [], "list": [], "get": [], "replace": []}

    def ensure_main_portfolio(user_id: str, base_currency: str = "CAD"):
        calls["ensure"].append({"userId": user_id, "baseCurrency": base_currency})

    def list_portfolios(user_id: str):
        calls["list"].append(user_id)
        return [PORTFOLIO]

    def get_portfolio(user_id: str, portfolio_id: str):
        calls["get"].append({"userId": user_id, "portfolioId": portfolio_id})
        return PORTFOLIO if user_id == "user-1" and portfolio_id == "main" else None

    def replace_holdings(user_id: str, portfolio_id: str, holdings: list):
        calls["replace"].append(
            {"userId": user_id, "portfolioId": portfolio_id, "holdings": holdings}
        )
        return {**PORTFOLIO, "holdings": holdings}

    monkeypatch.setattr(portfolios.repo, "ensure_main_portfolio", ensure_main_portfolio)
    monkeypatch.setattr(portfolios.repo, "list_portfolios", list_portfolios)
    monkeypatch.setattr(portfolios.repo, "get_portfolio", get_portfolio)
    monkeypatch.setattr(portfolios.repo, "replace_holdings", replace_holdings)
    return calls


def test_list_portfolios_cree_main_et_retourne_items(fake_portfolios):
    response = handle_request(event("GET /v1/portfolios"))
    assert response["statusCode"] == 200
    assert body_of(response) == {"items": [PORTFOLIO]}
    assert fake_portfolios["ensure"] == [{"userId": "user-1", "baseCurrency": "CAD"}]
    assert fake_portfolios["list"] == ["user-1"]


def test_put_holdings_valide_et_remplace_la_liste(
    fake_portfolios, ticker_validator
):
    holdings = {"holdings": [{"ticker": "RY.TO", "quantity": 10, "avgCost": 125.5}]}
    response = handle_request(
        event(
            "PUT /v1/portfolios/{portfolioId}/holdings",
            path_parameters={"portfolioId": "main"},
            body=holdings,
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 200
    assert body_of(response)["holdings"] == holdings["holdings"]
    assert ticker_validator.calls == [["RY.TO"]]
    assert fake_portfolios["replace"] == [
        {"userId": "user-1", "portfolioId": "main", "holdings": holdings["holdings"]}
    ]


def test_put_holdings_accepte_une_liste_vide(fake_portfolios, ticker_validator):
    response = handle_request(
        event(
            "PUT /v1/portfolios/{portfolioId}/holdings",
            path_parameters={"portfolioId": "main"},
            body={"holdings": []},
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 200
    assert body_of(response)["holdings"] == []
    assert fake_portfolios["replace"][0]["holdings"] == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"holdings": "deux"},
        {"holdings": [{}]},
        {"holdings": [{"ticker": 12, "quantity": 1, "avgCost": 1}]},
        {"holdings": [{"ticker": "RY.TO", "quantity": 0, "avgCost": 1}]},
        {"holdings": [{"ticker": "RY.TO", "quantity": -1, "avgCost": 1}]},
        {"holdings": [{"ticker": "RY.TO", "quantity": True, "avgCost": 1}]},
        {"holdings": [{"ticker": "RY.TO", "quantity": 1, "avgCost": None}]},
        {"holdings": [{"ticker": "RY.TO", "quantity": 1, "avgCost": "12"}]},
        {"holdings": [{"ticker": "RY.TO", "quantity": 1, "avgCost": 1, "extra": 2}]},
    ],
)
def test_put_holdings_refuse_les_corps_invalides(fake_portfolios, body):
    response = handle_request(
        event(
            "PUT /v1/portfolios/{portfolioId}/holdings",
            path_parameters={"portfolioId": "main"},
            body=body,
        ),
        ticker_validator=lambda tickers: None,
    )
    assert response["statusCode"] == 400
    assert body_of(response)["error"]["code"] == "VALIDATION_ERROR"
    assert fake_portfolios["get"] == []
    assert fake_portfolios["replace"] == []


def test_deux_404_successifs_recoivent_leur_request_id(
    fake_portfolios, ticker_validator
):
    body = {"holdings": [{"ticker": "RY.TO", "quantity": 1, "avgCost": 1}]}

    def request_for(request_id: str, sub: str):
        return handle_request(
            event(
                "PUT /v1/portfolios/{portfolioId}/holdings",
                path_parameters={"portfolioId": "main"},
                body=body,
                claims={"sub": sub},
                request_id=request_id,
            ),
            ticker_validator=ticker_validator,
        )

    first = request_for("req-AAA", "user-2")
    second = request_for("req-BBB", "user-3")
    assert body_of(first)["error"]["requestId"] == "req-AAA"
    assert body_of(second)["error"]["requestId"] == "req-BBB"


def test_put_holdings_d_un_portefeuille_etranger_est_invisible(
    fake_portfolios, ticker_validator
):
    response = handle_request(
        event(
            "PUT /v1/portfolios/{portfolioId}/holdings",
            path_parameters={"portfolioId": "main"},
            body={"holdings": [{"ticker": "RY.TO", "quantity": 1, "avgCost": 1}]},
            claims={"sub": "user-2"},
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 404
    assert body_of(response)["error"]["code"] == "PORTFOLIO_NOT_FOUND"
    assert ticker_validator.calls == []
    assert fake_portfolios["replace"] == []


def test_put_holdings_refuse_un_ticker_inconnu(
    fake_portfolios, ticker_validator, monkeypatch
):
    replaced: list = []
    monkeypatch.setattr(portfolios.repo, "replace_holdings", lambda *args: replaced.append(args))
    response = handle_request(
        event(
            "PUT /v1/portfolios/{portfolioId}/holdings",
            path_parameters={"portfolioId": "main"},
            body={"holdings": [{"ticker": "BAD", "quantity": 1, "avgCost": 1}]},
        ),
        ticker_validator=ticker_validator,
    )
    assert response["statusCode"] == 404
    assert body_of(response)["error"]["code"] == "ASSET_NOT_FOUND"
    assert ticker_validator.calls == [["BAD"]]
    assert replaced == []


def test_put_holdings_sans_validateur_utilise_le_module_univers(
    fake_portfolios, monkeypatch
):
    calls: list[list[str]] = []

    def fake_validate_tickers(tickers: list[str]):
        calls.append(tickers)

    monkeypatch.setattr("backend.api.universe.validate_tickers", fake_validate_tickers)
    response = handle_request(
        event(
            "PUT /v1/portfolios/{portfolioId}/holdings",
            path_parameters={"portfolioId": "main"},
            body={"holdings": [{"ticker": "RY.TO", "quantity": 1, "avgCost": 1}]},
        )
    )
    assert response["statusCode"] == 200
    assert calls == [["RY.TO"]]
