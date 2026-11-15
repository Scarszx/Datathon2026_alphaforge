"""Génère le mini-jeu de test SYNTHÉTIQUE (aucune donnée de marché réelle).

Pourquoi synthétique : le contrat interdit de redistribuer les prix Yahoo dans
le dépôt (storage-dataset.notes). Les séries sont tirées d'un générateur à graine
fixe, avec des régimes qui imitent la forme des crises (krach COVID 2020, année
2022, cycle de hausse des taux, krach crypto) pour exercer le moteur et les
règles. Les chiffres n'ont AUCUNE valeur de marché.

Même disposition que le contrat (section storage). Usage :
    python -m backend.agents.tests.fixtures.make_fixtures
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).with_name("dataset")
VERSION = "fixture-synthetic"
START, END = "2016-11-14", "2026-11-12"
SEED = 20261114

# ticker: (name, asset_class, market, currency, sector, prix initial, mu, sigma, beta,
#          choc covid (log), choc 2022 (log))
ASSETS = {
    "XIU.TO": ("Synthetic TSX 60 ETF", "etf_equity", "TSX", "CAD", "Broad market (Canada)", 22.0, 0.07, 0.14, 0.9, -0.38, -0.10),
    "RY.TO": ("Synthetic Royal Bank", "equity", "TSX", "CAD", "Financials", 95.0, 0.08, 0.18, 0.8, -0.35, -0.12),
    "TD.TO": ("Synthetic TD Bank", "equity", "TSX", "CAD", "Financials", 70.0, 0.06, 0.19, 0.8, -0.38, -0.14),
    "ENB.TO": ("Synthetic Enbridge", "equity", "TSX", "CAD", "Energy", 55.0, 0.05, 0.20, 0.6, -0.40, 0.05),
    "XBB.TO": ("Synthetic Canadian Bond ETF", "etf_bond", "TSX", "CAD", "Bonds (Canada aggregate)", 31.0, 0.025, 0.05, 0.1, -0.04, -0.13),
    "ZST.TO": ("Synthetic Ultra Short Bond ETF", "etf_bond", "TSX", "CAD", "Bonds (Canada ultra short-term)", 49.0, 0.02, 0.008, 0.0, -0.005, 0.01),
    "SPY": ("Synthetic S&P 500 ETF", "etf_equity", "NYSE Arca", "USD", "Broad market (U.S.)", 220.0, 0.10, 0.16, 1.0, -0.40, -0.21),
    "QQQ": ("Synthetic Nasdaq-100 ETF", "etf_equity", "NASDAQ", "USD", "Broad market (U.S. growth/tech-heavy)", 120.0, 0.14, 0.21, 1.0, -0.33, -0.37),
    "ESGV": ("Synthetic ESG U.S. ETF", "etf_equity", "Cboe BZX", "USD", "Broad market (U.S., ESG-screened)", 50.0, 0.10, 0.17, 1.0, -0.40, -0.25),
    "AGG": ("Synthetic U.S. Aggregate Bond ETF", "etf_bond", "NYSE Arca", "USD", "Bonds (U.S. aggregate)", 108.0, 0.02, 0.05, 0.1, -0.05, -0.14),
    "NVDA": ("Synthetic NVIDIA", "equity", "NASDAQ", "USD", "Information Technology", 25.0, 0.45, 0.50, 0.9, -0.45, -0.85),
    "AAPL": ("Synthetic Apple", "equity", "NASDAQ", "USD", "Information Technology", 28.0, 0.25, 0.29, 0.9, -0.35, -0.30),
    "BTC-USD": ("Synthetic Bitcoin", "crypto", "Crypto (24/7)", "USD", "Crypto asset", 700.0, 0.60, 0.70, 0.3, -0.55, -1.10),
}

COVID = ("2020-02-20", "2020-03-23")
Y2022 = ("2022-01-03", "2022-12-30")

# Taux directeur synthétique (forme du cycle 2020-2025, valeurs fictives).
POLICY_STEPS = [
    ("2016-11-14", 0.50), ("2020-03-04", 0.25),
    ("2022-03-02", 0.50), ("2022-04-13", 1.00), ("2022-06-01", 1.50), ("2022-07-13", 2.50),
    ("2022-09-07", 3.25), ("2022-10-26", 3.75), ("2022-12-07", 4.25), ("2023-01-25", 4.50),
    ("2023-07-12", 5.00), ("2024-06-05", 4.75), ("2024-12-11", 3.25), ("2025-03-12", 2.75),
]

ETF_ENRICHED = {
    "fixture": True,
    "note": "Synthetic test values, not issuer data.",
    "etfs": {
        "XIU.TO": {
            "sourceUrl": "https://example.test/fixture/xiu", "asOfDate": "2026-10-31", "merPct": 0.18,
            "sectorWeights": {"Financials": 33.0, "Energy": 17.0, "Industrials": 12.0, "Materials": 11.0,
                              "Information Technology": 9.0, "Other": 18.0},
            "countryWeights": {"CA": 100.0},
            "topHoldings": [{"ticker": "RY.TO", "name": "Royal Bank", "weight": 7.0},
                            {"ticker": "TD.TO", "name": "TD Bank", "weight": 5.5},
                            {"ticker": "ENB.TO", "name": "Enbridge", "weight": 4.0}],
        },
        "SPY": {
            "sourceUrl": "https://example.test/fixture/spy", "asOfDate": "2026-10-31", "merPct": 0.09,
            "sectorWeights": {"Information Technology": 32.0, "Financials": 13.0, "Health Care": 11.0,
                              "Consumer Discretionary": 10.0, "Other": 34.0},
            "countryWeights": {"US": 100.0},
            "topHoldings": [{"ticker": "NVDA", "name": "NVIDIA", "weight": 7.0},
                            {"ticker": "AAPL", "name": "Apple", "weight": 6.5}],
        },
        "QQQ": {
            "sourceUrl": "https://example.test/fixture/qqq", "asOfDate": "2026-10-31", "merPct": 0.20,
            "sectorWeights": {"Information Technology": 50.0, "Communication Services": 16.0, "Other": 34.0},
            "countryWeights": {"US": 97.0, "Other": 3.0},
            "topHoldings": [{"ticker": "NVDA", "name": "NVIDIA", "weight": 9.0},
                            {"ticker": "AAPL", "name": "Apple", "weight": 8.0}],
        },
        "ESGV": {
            "sourceUrl": "https://example.test/fixture/esgv", "asOfDate": "2026-10-31", "merPct": 0.09,
            "sectorWeights": {"Information Technology": 35.0, "Other": 65.0},
            "countryWeights": {"US": 100.0},
            "topHoldings": [{"ticker": "NVDA", "name": "NVIDIA", "weight": 7.5}],
            "exclusions": ["fossil fuels", "weapons", "tobacco"],
            "esgMethodologyUrl": "https://example.test/fixture/esgv-methodology",
        },
        "XBB.TO": {
            "sourceUrl": "https://example.test/fixture/xbb", "asOfDate": "2026-10-31", "merPct": 0.10,
            "sectorWeights": {"Government bonds": 70.0, "Corporate bonds": 30.0},
            "countryWeights": {"CA": 100.0}, "topHoldings": [],
        },
    },
}


def _calendar(ticker: str) -> pd.DatetimeIndex:
    if ticker.endswith("-USD"):
        return pd.date_range(START, END, freq="D")
    days = pd.bdate_range(START, END)
    # Calendriers non alignés (contrat) : fête du Canada pour .TO, 4 juillet pour les US.
    holiday = (7, 1) if ticker.endswith(".TO") else (7, 4)
    return days[~((days.month == holiday[0]) & (days.day == holiday[1]))]


def _regime_drift(days: pd.DatetimeIndex, window: tuple[str, str], shock: float) -> np.ndarray:
    mask = (days >= window[0]) & (days <= window[1])
    count = int(mask.sum())
    drift = np.zeros(len(days))
    if count:
        drift[mask] = shock / count
    return drift


def build() -> None:
    rng = np.random.default_rng(SEED)
    all_days = pd.date_range(START, END, freq="D")
    market = pd.Series(rng.standard_normal(len(all_days)), index=all_days)
    (OUT / "prices").mkdir(parents=True, exist_ok=True)
    universe_rows = []
    for i, (ticker, spec) in enumerate(ASSETS.items(), start=1):
        name, asset_class, mkt, currency, sector, p0, mu, sigma, beta, covid, y2022 = spec
        days = _calendar(ticker)
        periods = 365 if ticker.endswith("-USD") else 252
        z = beta * market.reindex(days).to_numpy() + np.sqrt(1 - beta**2) * rng.standard_normal(len(days))
        noise = sigma / np.sqrt(periods) * z
        drift = np.full(len(days), mu / periods)
        for window in (COVID, Y2022):
            # Dans une fenêtre de crise, le bruit est recentré et la tendance
            # retirée : le choc réalisé vaut exactement le choc spécifié.
            mask = (days >= window[0]) & (days <= window[1])
            noise[mask] -= noise[mask].mean()
            drift[mask] = 0.0
        log_ret = drift + noise
        log_ret += _regime_drift(days, COVID, covid) + _regime_drift(days, Y2022, y2022)
        adj = p0 * np.exp(np.cumsum(log_ret))
        frame = pd.DataFrame({
            "date": days.date, "open": adj, "high": adj * 1.01, "low": adj * 0.99,
            "close": adj * 1.02, "adj_close": adj, "volume": 1_000_000, "currency": currency,
        })
        frame.to_parquet(OUT / "prices" / f"{ticker}.parquet", index=False)
        universe_rows.append({
            "asset_id": f"F{i:02d}", "ticker": ticker, "name": name, "asset_class": asset_class,
            "market": mkt, "currency": currency, "sector": sector,
        })
    pd.DataFrame(universe_rows).to_parquet(OUT / "universe.parquet", index=False)

    fx_days = pd.bdate_range(START, END)
    fx = 1.32 + np.cumsum(rng.normal(0, 0.003, len(fx_days)))
    (OUT / "fx").mkdir(exist_ok=True)
    pd.DataFrame({"date": fx_days.date, "usdcad": fx, "cadusd": 1 / fx}).to_parquet(
        OUT / "fx" / "usdcad.parquet", index=False
    )

    rows = []
    steps = pd.Series({pd.Timestamp(d): v for d, v in POLICY_STEPS})
    for series_id in ("V39079", "DFF"):
        days = pd.bdate_range(START, END) if series_id == "V39079" else pd.date_range(START, END)
        values = steps.reindex(steps.index.union(days)).ffill().reindex(days)
        for day, value in values.items():
            rows.append({"date": day.date(), "series_id": series_id, "value": float(value), "unit": "percent",
                         "frequency": "daily", "label": f"Synthetic {series_id}", "source": "synthetic",
                         "publication_date": day.date()})
    months = pd.date_range(START, END, freq="MS")
    for k, month in enumerate(months):
        rows.append({"date": month.date(), "series_id": "CPIAUCSL", "value": 250.0 + k * 0.4, "unit": "index",
                     "frequency": "monthly", "label": "Synthetic CPI", "source": "synthetic",
                     "publication_date": (month + pd.DateOffset(months=1, days=12)).date()})
    (OUT / "macro").mkdir(exist_ok=True)
    pd.DataFrame(rows).to_parquet(OUT / "macro" / "macro.parquet", index=False)

    (OUT / "etf_enriched.json").write_text(json.dumps(ETF_ENRICHED, indent=2), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({
        "version": VERSION, "synthetic": True, "periodStart": START, "periodEnd": END,
        "tickers": list(ASSETS), "source": "make_fixtures.py (seeded generator, no market data)",
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build()
    print(f"Fixtures written to {OUT}")
