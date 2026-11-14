"""Tests de repositories/portfolios.py (moto)."""

import pytest

from backend.common.http import ApiError
from backend.common.repositories import portfolios

HOLDINGS = [
    {"ticker": "RY.TO", "quantity": 10, "avgCost": 135.42},
    {"ticker": "BTC-USD", "quantity": 0.015, "avgCost": 61234.5},
]


def test_ensure_main_portfolio_cree_main_vide(dynamo):
    p = portfolios.ensure_main_portfolio("u1")
    assert set(p) == {"portfolioId", "name", "baseCurrency", "holdings", "updatedAt"}
    assert p["portfolioId"] == "main"
    assert p["baseCurrency"] == "CAD"
    assert p["holdings"] == []
    assert p["name"]


def test_ensure_main_portfolio_idempotent(dynamo):
    portfolios.ensure_main_portfolio("u1")
    portfolios.replace_holdings("u1", "main", HOLDINGS)
    again = portfolios.ensure_main_portfolio("u1", base_currency="USD")
    assert again["holdings"] == HOLDINGS
    assert again["baseCurrency"] == "CAD"
    assert len(portfolios.list_portfolios("u1")) == 1


def test_get_portfolio(dynamo):
    created = portfolios.ensure_main_portfolio("u1")
    assert portfolios.get_portfolio("u1", "main") == created
    assert portfolios.get_portfolio("u1", "autre") is None


def test_list_portfolios(dynamo):
    assert portfolios.list_portfolios("u1") == []
    portfolios.ensure_main_portfolio("u1")
    assert [p["portfolioId"] for p in portfolios.list_portfolios("u1")] == ["main"]


def test_replace_holdings_remplace_tout(dynamo, monkeypatch):
    from backend.common.repositories import _dynamo

    created = portfolios.ensure_main_portfolio("u1")
    portfolios.replace_holdings("u1", "main", HOLDINGS)
    monkeypatch.setattr(_dynamo, "now_iso", lambda: "2099-01-01T00:00:00Z")
    updated = portfolios.replace_holdings("u1", "main", [{"ticker": "AAPL", "quantity": 3, "avgCost": 190.0}])
    assert updated["holdings"] == [{"ticker": "AAPL", "quantity": 3, "avgCost": 190}]
    assert updated["updatedAt"] == "2099-01-01T00:00:00Z" != created["updatedAt"]
    assert portfolios.get_portfolio("u1", "main") == updated


def test_replace_holdings_nombres_decimaux(dynamo):
    portfolios.ensure_main_portfolio("u1")
    p = portfolios.replace_holdings("u1", "main", HOLDINGS)
    assert p["holdings"] == HOLDINGS
    assert isinstance(p["holdings"][1]["quantity"], float)


def test_replace_holdings_liste_vide(dynamo):
    portfolios.ensure_main_portfolio("u1")
    portfolios.replace_holdings("u1", "main", HOLDINGS)
    assert portfolios.replace_holdings("u1", "main", [])["holdings"] == []


def test_replace_holdings_portefeuille_absent(dynamo):
    with pytest.raises(ApiError) as err:
        portfolios.replace_holdings("u1", "main", HOLDINGS)
    assert err.value.code == "PORTFOLIO_NOT_FOUND"
    assert portfolios.list_portfolios("u1") == []


def test_isolation_entre_utilisateurs(dynamo):
    portfolios.ensure_main_portfolio("u1")
    portfolios.replace_holdings("u1", "main", HOLDINGS)
    assert portfolios.get_portfolio("u2", "main") is None
    assert portfolios.list_portfolios("u2") == []
    with pytest.raises(ApiError) as err:
        portfolios.replace_holdings("u2", "main", [])
    assert err.value.code == "PORTFOLIO_NOT_FOUND"
    assert portfolios.ensure_main_portfolio("u2")["holdings"] == []
    assert portfolios.get_portfolio("u1", "main")["holdings"] == HOLDINGS
