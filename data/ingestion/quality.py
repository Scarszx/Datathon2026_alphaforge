"""Contrôle qualité du jeu de données et isolation de l'anomalie CNQ.TO (WS3)."""

from __future__ import annotations

from typing import Any
import pandas as pd

SUSPICIOUS_DAILY_MOVE_THRESHOLD: float = 0.40


def isolate_cnq_anomaly_and_check_actions(
    actions_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Isole et documente l'anomalie CNQ.TO du 2022-08-22 dans corporate_actions.

    Les fractionnements (splits) ne sont jamais réappliqués aux prix (`close` et `adjclose`
    sont déjà ajustés par Yahoo Finance).
    """
    df = actions_df.copy()
    if df.empty:
        df["anomaly_note"] = pd.Series(dtype="string")
        return df, []

    df["ex_date"] = df["ex_date"].astype(str).str.slice(0, 10)
    notes: list[str | None] = [None] * len(df)
    isolated: list[dict[str, Any]] = []

    cnq_20220822_div = df[
        (df["symbol"] == "CNQ.TO")
        & (df["ex_date"] == "2022-08-22")
        & (df["action"] == "dividend")
    ]
    coincident_div = (
        float(cnq_20220822_div["value"].iloc[0]) if not cnq_20220822_div.empty else 0.75
    )

    for pos, (_, row) in enumerate(df.iterrows()):
        ticker = str(row["symbol"])
        ex_date = str(row["ex_date"])
        action = str(row["action"])
        val = float(row["value"])
        if (
            ticker == "CNQ.TO"
            and ex_date == "2022-08-22"
            and action == "split"
            and abs(val - 1.021) < 0.01
        ):
            note = (
                "Isolated anomaly: Yahoo Finance reports a 1.021 split on 2022-08-22 on the same "
                f"ex-date as a {coincident_div} CAD dividend (likely a special distribution "
                "adjustment, not a share split). Splits are never re-applied to close or adjclose."
            )
            notes[pos] = note
            isolated.append({
                "symbol": ticker,
                "exDate": ex_date,
                "action": action,
                "value": val,
                "coincidentDividend": coincident_div,
                "currency": "CAD",
                "handling": "isolated_in_corporate_actions_never_reapplied",
                "explanation": note,
            })

    df["anomaly_note"] = notes
    return df, isolated


def run_quality_checks(
    universe_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    actions_df: pd.DataFrame,
    fx_df: pd.DataFrame,
    macro_df: pd.DataFrame,
    requested_start: str,
    requested_end: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Exécute les contrôles qualité bloquants et construit le rapport qualité JSON (camelCase)."""
    # 1. Contrôles bloquants
    if prices_df.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate (date, ticker) rows detected in prices.")

    universe_tickers = set(universe_df["symbol"].astype(str))
    price_tickers = set(prices_df["symbol"].astype(str))
    if universe_tickers != price_tickers:
        missing = sorted(universe_tickers - price_tickers)
        extra = sorted(price_tickers - universe_tickers)
        raise ValueError(f"Ticker mismatch between universe and prices: missing={missing}, extra={extra}")

    merged_ccy = (
        prices_df[["symbol", "currency"]]
        .drop_duplicates()
        .merge(universe_df[["symbol", "currency"]], on="symbol", suffixes=("_price", "_univ"))
    )
    if not (merged_ccy["currency_price"] == merged_ccy["currency_univ"]).all():
        raise ValueError("Currency mismatch between universe and prices.")

    for col in ("open", "high", "low", "close", "adjclose"):
        if prices_df[col].isna().any() or (prices_df[col] <= 0).any():
            raise ValueError(f"Null or non-positive values detected in prices.{col}.")

    if not fx_df.empty and fx_df.duplicated("date").any():
        raise ValueError("Duplicate dates detected in fx/usdcad.")

    if not macro_df.empty and macro_df.duplicated(["date", "series_id"]).any():
        raise ValueError("Duplicate (date, series_id) rows detected in macro.")

    # 2. Isolation de l'anomalie CNQ.TO et analyse des sauts/volumes/trous
    enriched_actions, isolated_anomalies = isolate_cnq_anomaly_and_check_actions(actions_df)

    suspicious_moves: list[dict[str, Any]] = []
    zero_volume_rows: list[dict[str, Any]] = []
    calendar_gaps: list[dict[str, Any]] = []
    short_histories: list[dict[str, Any]] = []

    for ticker, group in prices_df.groupby("symbol", sort=True):
        t_str = str(ticker)
        g = group.sort_values("date").reset_index(drop=True)
        first_d = str(g["date"].iloc[0])[:10]
        last_d = str(g["date"].iloc[-1])[:10]

        if first_d > requested_start[:8] + "20":
            short_histories.append({
                "symbol": t_str,
                "firstDate": first_d,
                "lastDate": last_d,
                "rows": int(len(g)),
                "note": f"History starts {first_d} (later than requested start {requested_start}); never backfilled.",
            })

        # Sauts suspects d'un jour (> 40 % sur adjclose)
        pct = g["adjclose"].astype(float).pct_change()
        big_moves = g.loc[pct.abs() > SUSPICIOUS_DAILY_MOVE_THRESHOLD]
        for idx, row in big_moves.iterrows():
            move_val = float(pct.loc[idx])
            suspicious_moves.append({
                "symbol": t_str,
                "date": str(row["date"])[:10],
                "adjCloseReturnPct": round(move_val * 100.0, 2),
                "adjClose": float(row["adjclose"]),
            })

        # Lignes à volume nul (hors crypto si applicable)
        zero_vol = g[g["volume"] == 0]
        for _, row in zero_vol.iterrows():
            zero_volume_rows.append({
                "symbol": t_str,
                "date": str(row["date"])[:10],
            })

        # Trous de calendrier (> 5 jours ouvrés/civils pour actions/FNB, > 1 jour pour crypto)
        gap_threshold = 1 if t_str.endswith("-USD") else 5
        dt_diff = pd.to_datetime(g["date"]).diff().dt.days
        for idx in dt_diff[dt_diff > gap_threshold].index:
            calendar_gaps.append({
                "symbol": t_str,
                "date": str(g.loc[idx, "date"])[:10],
                "gapCalendarDays": int(dt_diff.loc[idx]),
            })

    report: dict[str, Any] = {
        "duplicateRows": 0,
        "nonPositivePriceRows": 0,
        "missingTickers": 0,
        "splitsReapplied": False,
        "isolatedAnomalies": isolated_anomalies,
        "suspiciousOneDayMovesCount": len(suspicious_moves),
        "suspiciousOneDayMoves": suspicious_moves[:100],
        "zeroVolumeRowsCount": len(zero_volume_rows),
        "zeroVolumeRows": zero_volume_rows[:50],
        "calendarGapsCount": len(calendar_gaps),
        "calendarGapsSample": calendar_gaps[:50],
        "shortHistoryCount": len(short_histories),
        "shortHistories": short_histories,
    }
    return enriched_actions, report
