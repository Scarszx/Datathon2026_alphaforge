"""Route GET /v1/portfolios/{portfolioId}/summary (api-portfolio-summary), calcul déterministe sans modèle.

Tout est exprimé dans baseCurrency, avec le taux USD/CAD du jeu de données
(dernier taux connu reporté). Valeur au dernier cours (close), performance et
risque sur adj_close, quantités actuelles conservées sur la période
(simulation de détention, pas l'historique réel des transactions).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.agents.data.store import DataStore
from backend.agents.engine import analytics as an
from backend.agents.engine.concentration import by_asset_class, concentration
from backend.common.http import ApiError, json_response
from backend.common.repositories import portfolios as portfolios_repo
from backend.common.validation import path_parameter

RANGES = {"1m": pd.DateOffset(months=1), "6m": pd.DateOffset(months=6), "1y": pd.DateOffset(years=1), "5y": pd.DateOffset(years=5)}
MAX_POINTS = 260


def _convert(value: float, currency: str, base: str, rate: float) -> float:
    if currency == base:
        return value
    return value * rate if base == "CAD" else value / rate


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None or value != value else round(float(value), digits)


def build_summary(store: DataStore, portfolio: dict[str, Any], range_key: str) -> dict[str, Any]:
    base = portfolio.get("baseCurrency") or "CAD"
    as_of = store.last_date()
    rate = an.fx_rate_on(store, as_of)
    rows, warnings = [], []
    values_cad: dict[str, float] = {}
    for holding in portfolio.get("holdings", []):
        ticker = holding["ticker"]
        if not store.has_ticker(ticker):
            warnings.append(f"{ticker} is not in the dataset universe.")
            continue
        asset = store.asset(ticker)
        currency = an.listing_currency(store, ticker)
        prices = store.prices(ticker)
        known = prices[prices.index <= as_of]
        if known.empty:
            warnings.append(f"No price for {ticker}.")
            continue
        price = float(known["close"].iloc[-1])
        previous = float(known["close"].iloc[-2]) if len(known) > 1 else price
        stale = (as_of - known.index[-1]).days > 5
        if stale:
            warnings.append(f"Last price used for {ticker}: {known.index[-1].date().isoformat()}.")
        quantity = float(holding["quantity"])
        value_native = price * quantity
        cost_native = float(holding["avgCost"]) * quantity
        value = _convert(value_native, currency, base, rate)
        cost = _convert(cost_native, currency, base, rate)
        values_cad[ticker] = _convert(value_native, currency, "CAD", rate)
        rows.append({
            "ticker": ticker, "name": asset.get("name"), "assetClass": asset.get("asset_class"), "quantity": quantity,
            "avgCost": holding["avgCost"], "currency": currency, "price": _round(price, 4), "value": _round(value),
            "weight": None, "pnl": _round(value - cost), "pnlPct": _round((value / cost - 1) * 100 if cost else None),
            "dayChangePct": _round((price / previous - 1) * 100 if previous else None), "sector": asset.get("sector"),
            "stale": stale, "_dayChange": _convert((price - previous) * quantity, currency, base, rate),
        })
    total_value = sum(r["value"] for r in rows)
    total_cost = sum(r["value"] - r["pnl"] for r in rows)
    day_change = sum(r.pop("_dayChange") for r in rows)
    for row in rows:
        row["weight"] = _round(row["value"] / total_value * 100 if total_value else None)

    performance: dict[str, Any] = {"range": range_key, "points": []}
    risk: dict[str, Any] = {"volatility": None, "maxDrawdown": None}
    if values_cad:
        start = as_of - RANGES[range_key]
        aligned = an.aligned_cad_prices(store, list(values_cad), pd.Timestamp(start), as_of)
        if not aligned.frame.empty:
            quantities_cad = {t: values_cad[t] / float(aligned.frame[t].iloc[-1]) for t in aligned.frame.columns}
            series_cad = sum(aligned.frame[t] * q for t, q in quantities_cad.items())
            fx = store.fx_usdcad()
            if base == "USD":
                fx_rates = fx.reindex(fx.index.union(series_cad.index)).ffill().reindex(series_cad.index)
                series = series_cad / fx_rates
            else:
                series = series_cad
            sampled = series if len(series) <= MAX_POINTS else series.iloc[:: max(1, len(series) // MAX_POINTS + 1)]
            performance["points"] = [{"date": d.date().isoformat(), "value": round(float(v), 2)} for d, v in sampled.items()]
            dd, _, _ = an.max_drawdown(series)
            risk = {"volatility": _round(an.annualized_volatility(series.pct_change().dropna(), 252)), "maxDrawdown": _round(dd)}
            if aligned.shortened_by:
                warnings.append("Performance window shortened by the history of " + ", ".join(aligned.shortened_by) + ".")

    conc = concentration(store, values_cad) if values_cad else {"bySector": [], "byCurrency": []}
    return {
        "portfolioId": portfolio["portfolioId"], "baseCurrency": base, "asOf": as_of.date().isoformat(),
        "totals": {
            "value": _round(total_value), "cost": _round(total_cost), "pnl": _round(total_value - total_cost),
            "pnlPct": _round((total_value / total_cost - 1) * 100 if total_cost else None),
            "dayChange": _round(day_change),
            "dayChangePct": _round(day_change / (total_value - day_change) * 100 if total_value - day_change else None),
        },
        "holdings": rows,
        "allocation": {"byAssetClass": by_asset_class(store, values_cad) if values_cad else [],
                       "bySector": conc["bySector"], "byCurrency": conc["byCurrency"]},
        "performance": performance,
        "risk": risk,
        "warnings": warnings,
        "explanation": {
            "sources": [
                {"id": "prices_daily", "dataset": store.source_label("prices"), "asOf": as_of.date().isoformat(),
                 "note": "close for value, adj_close for performance and risk, listing currency"},
                {"id": "fx_usdcad", "dataset": store.source_label("fx/usdcad.parquet"), "note": "last known USD/CAD rate carried forward"},
            ],
            "assumptions": [
                "Current quantities held over the whole range (no transaction history).",
                "Volatility annualized with sqrt(252) on common trading days.",
            ],
            "limitations": ["Past performance describes the past; it does not predict future returns."],
            "steps": [], "checks": [],
        },
    }


def portfolio_summary(event: dict[str, Any], user_id: str, store: DataStore) -> dict[str, Any]:
    portfolio_id = path_parameter(event, "portfolioId")
    range_key = (event.get("queryStringParameters") or {}).get("range", "1y")
    if range_key not in RANGES:
        raise ApiError("VALIDATION_ERROR", "range doit être l'un de : 1m, 6m, 1y, 5y.")
    portfolio = portfolios_repo.get_portfolio(user_id, portfolio_id)
    if portfolio is None:
        raise ApiError("PORTFOLIO_NOT_FOUND", "Portefeuille inconnu.")
    return json_response(200, build_summary(store, portfolio, range_key))
