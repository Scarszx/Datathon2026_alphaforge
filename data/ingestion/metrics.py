"""Calculs d'indicateurs précalculés (1 an) et règle de publication_date macro (WS3)."""

from __future__ import annotations

import math
from datetime import date
import pandas as pd

MONTHLY_MACRO_SERIES: frozenset[str] = frozenset({
    "STATIC_TOTALCPICHANGE",
    "CPIAUCSL",
    "UNRATE",
})

PUBLICATION_DATE_RULE_DESCRIPTION: str = (
    "Monthly series (STATIC_TOTALCPICHANGE, CPIAUCSL, UNRATE) are dated to the first day "
    "of the reference month (YYYY-MM-01). To prevent look-ahead bias (rule R10), "
    "publication_date is set to the 28th of the month following the reference month "
    "(YYYY-(MM+1)-28). This conservative approximation accounts for Canadian CPI releases "
    "occurring after the 20th (e.g. May 2024 released on June 25) and U.S. release delays "
    "(e.g. autumn 2025 federal shutdown). Daily and business-daily series have "
    "publication_date = date."
)


def compute_monthly_publication_date(ref_date_str: str) -> str:
    """Calcule le 28 du mois suivant pour une date de référence mensuelle YYYY-MM-DD."""
    d = date.fromisoformat(str(ref_date_str)[:10])
    if d.month == 12:
        pub = date(d.year + 1, 1, 28)
    else:
        pub = date(d.year, d.month + 1, 28)
    return pub.isoformat()


def add_macro_publication_date(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la colonne snake_case `publication_date` au DataFrame macro."""
    df = macro_df.copy()
    df["date"] = df["date"].astype(str).str.slice(0, 10)
    is_monthly = df["series_id"].isin(MONTHLY_MACRO_SERIES) | (
        df.get("frequency", pd.Series("", index=df.index)).astype(str).str.lower() == "monthly"
    )
    pub_dates: list[str] = []
    for idx, row in df.iterrows():
        if bool(is_monthly.loc[idx]):
            pub_dates.append(compute_monthly_publication_date(str(row["date"])))
        else:
            pub_dates.append(str(row["date"]))
    df["publication_date"] = pub_dates
    return df


def compute_1y_indicators(prices_df: pd.DataFrame) -> dict[str, float | None]:
    """Calcule return_1y, volatility_1y (√252 sur adj_close) et max_drawdown_1y sur 1 an."""
    if prices_df is None or prices_df.empty or "adj_close" not in prices_df.columns:
        return {"return_1y": None, "volatility_1y": None, "max_drawdown_1y": None}

    df = prices_df.dropna(subset=["adj_close"]).copy()
    if len(df) < 2:
        return {"return_1y": None, "volatility_1y": None, "max_drawdown_1y": None}

    df[" _dt"] = pd.to_datetime(df["date"])
    df = df.sort_values(" _dt")
    max_dt = df[" _dt"].iloc[-1]
    cutoff_dt = max_dt - pd.DateOffset(years=1)
    window_df = df[df[" _dt"] >= cutoff_dt]
    if len(window_df) < 2:
        window_df = df

    adj = window_df["adj_close"].astype(float)
    if (adj <= 0).any() or len(adj) < 2:
        return {"return_1y": None, "volatility_1y": None, "max_drawdown_1y": None}

    total_return = float((adj.iloc[-1] / adj.iloc[0]) - 1.0)
    daily_returns = adj.pct_change().dropna()
    if len(daily_returns) < 2:
        volatility = 0.0
    else:
        volatility = float(daily_returns.std(ddof=1) * math.sqrt(252.0))

    drawdowns = (adj / adj.cummax()) - 1.0
    max_drawdown = float(drawdowns.min())

    return {
        "return_1y": round(total_return, 6),
        "volatility_1y": round(volatility, 6),
        "max_drawdown_1y": round(max_drawdown, 6),
    }
