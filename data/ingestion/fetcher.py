"""Téléchargement réseau (yfinance par lots avec cache/reprise, Banque du Canada Valet, FRED)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
import io
import json
from pathlib import Path
import time
from typing import Any
import urllib.request

import pandas as pd
import requests

BOC_SERIES: dict[str, tuple[str, str, str]] = {
    "FXUSDCAD": ("USD/CAD daily exchange rate (CAD per 1 USD)", "CAD per USD", "daily"),
    "V39079": ("Bank of Canada target for the overnight rate", "percent", "daily (changes on announcement dates)"),
    "BD.CDN.2YR.DQ.YLD": ("Government of Canada benchmark bond yield, 2-year", "percent", "business daily"),
    "BD.CDN.10YR.DQ.YLD": ("Government of Canada benchmark bond yield, 10-year", "percent", "business daily"),
    "STATIC_TOTALCPICHANGE": ("Canada total CPI, % change y/y (unadjusted)", "percent", "monthly"),
}

FRED_SERIES: dict[str, tuple[str, str, str]] = {
    "DFF": ("U.S. effective federal funds rate", "percent", "daily"),
    "DGS2": ("U.S. Treasury constant maturity yield, 2-year", "percent", "business daily"),
    "DGS10": ("U.S. Treasury constant maturity yield, 10-year", "percent", "business daily"),
    "CPIAUCSL": ("U.S. CPI, all urban consumers (index 1982-84=100, SA)", "index", "monthly"),
    "UNRATE": ("U.S. unemployment rate (SA)", "percent", "monthly"),
}

GICS_SECTOR_MAP: dict[str, str] = {
    "Technology": "Information Technology",
    "Financial Services": "Financials",
    "Financial": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Healthcare": "Health Care",
    "Basic Materials": "Materials",
    "Communication Services": "Communication Services",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
}


def _http_get_bytes(url: str, timeout: int = 60, max_retries: int = 3) -> bytes:
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers={"User-Agent": "curl/8.0"}, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt + 1 < max_retries:
                time.sleep(1.5 * (attempt + 1))
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_boc_series(series_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Télécharge une série de l'API Valet de la Banque du Canada."""
    url = (
        f"https://www.bankofcanada.ca/valet/observations/{series_id}/json"
        f"?start_date={start_date}&end_date={end_date}"
    )
    data = json.loads(_http_get_bytes(url))
    rows = [
        (o["d"], o[series_id]["v"])
        for o in data.get("observations", [])
        if series_id in o and o[series_id].get("v") not in (None, "")
    ]
    return pd.DataFrame(rows, columns=["date", "value"]).astype({"value": float})


def fetch_fred_series(series_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Télécharge une série depuis FRED (fredgraph.csv)."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}&coed={end_date}"
    df = pd.read_csv(io.BytesIO(_http_get_bytes(url)))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().reset_index(drop=True)


def download_fx_and_macro(
    start_date: str,
    end_date: str,
    cache_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Télécharge FXUSDCAD et les 9 séries macro sur 10 ans avec cache disque."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    fx_cache = cache_dir / "fx_usdcad.parquet"
    macro_cache = cache_dir / "macro_raw.parquet"

    if fx_cache.exists() and macro_cache.exists():
        return pd.read_parquet(fx_cache), pd.read_parquet(macro_cache)

    fx = fetch_boc_series("FXUSDCAD", start_date, end_date).rename(columns={"value": "usdcad"})
    fx["usdcad"] = fx["usdcad"].round(6)
    fx["cadusd"] = (1.0 / fx["usdcad"]).round(6)
    fx = fx.sort_values("date").reset_index(drop=True)

    frames: list[pd.DataFrame] = []
    for sid, (label, unit, freq) in BOC_SERIES.items():
        if sid == "FXUSDCAD":
            continue
        d = fetch_boc_series(sid, start_date, end_date)
        d["series_id"] = sid
        d["label"] = label
        d["unit"] = unit
        d["frequency"] = freq
        d["source"] = "Bank of Canada Valet API"
        frames.append(d)

    for sid, (label, unit, freq) in FRED_SERIES.items():
        d = fetch_fred_series(sid, start_date, end_date)
        d["series_id"] = sid
        d["label"] = label
        d["unit"] = unit
        d["frequency"] = freq
        d["source"] = "FRED, Federal Reserve Bank of St. Louis"
        frames.append(d)

    macro = pd.concat(frames, ignore_index=True)[
        ["date", "series_id", "value", "unit", "frequency", "label", "source"]
    ]
    macro = macro.sort_values(["series_id", "date"]).reset_index(drop=True)

    fx.to_parquet(fx_cache, index=False)
    macro.to_parquet(macro_cache, index=False)
    return fx, macro


def _extract_ticker_frames(
    raw_df: pd.DataFrame,
    ticker: str,
    currency: str,
    is_multi: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extrait les DataFrames de prix et d'actions pour un ticker depuis la réponse yfinance."""
    empty_prices = pd.DataFrame(
        columns=["date", "symbol", "open", "high", "low", "close", "adjclose", "volume", "currency"]
    )
    empty_actions = pd.DataFrame(columns=["ex_date", "symbol", "action", "value", "unit"])

    if raw_df is None or raw_df.empty:
        return empty_prices, empty_actions

    try:
        sub = raw_df[ticker] if is_multi else raw_df
    except KeyError:
        return empty_prices, empty_actions

    if sub is None or sub.empty or "Close" not in sub.columns:
        return empty_prices, empty_actions

    d = sub.dropna(subset=["Close"]).reset_index()
    if d.empty:
        return empty_prices, empty_actions

    date_col = "Date" if "Date" in d.columns else d.columns[0]
    d["date_str"] = pd.to_datetime(d[date_col]).dt.date.astype(str)
    adj_col = "Adj Close" if "Adj Close" in d.columns else "Close"
    vol_series = pd.to_numeric(d.get("Volume", 0), errors="coerce").fillna(0).astype("int64")

    p = pd.DataFrame({
        "date": d["date_str"],
        "symbol": ticker,
        "open": pd.to_numeric(d["Open"], errors="coerce").round(6),
        "high": pd.to_numeric(d["High"], errors="coerce").round(6),
        "low": pd.to_numeric(d["Low"], errors="coerce").round(6),
        "close": pd.to_numeric(d["Close"], errors="coerce").round(6),
        "adjclose": pd.to_numeric(d[adj_col], errors="coerce").round(6),
        "volume": vol_series,
        "currency": currency,
    })

    action_rows: list[dict[str, Any]] = []
    for col, kind in (("Dividends", "dividend"), ("Stock Splits", "split")):
        if col in d.columns:
            vals = pd.to_numeric(d[col], errors="coerce").fillna(0.0)
            active = d.loc[vals > 0, ["date_str", col]]
            for _, r in active.iterrows():
                action_rows.append({
                    "ex_date": str(r["date_str"]),
                    "symbol": ticker,
                    "action": kind,
                    "value": round(float(r[col]), 6),
                    "unit": f"{currency} per share" if kind == "dividend" else "split ratio (new:old)",
                })

    actions = (
        pd.DataFrame(action_rows, columns=["ex_date", "symbol", "action", "value", "unit"])
        if action_rows
        else empty_actions
    )
    return p, actions


def download_prices_in_batches(
    candidates: list[dict[str, str]],
    start_date: str,
    end_date: str,
    cache_dir: Path,
    batch_size: int = 75,
    pause_seconds: float = 2.0,
    max_retries: int = 2,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Télécharge les prix journaliers et actions via yfinance par lots de 50-100.

    - Sauvegarde chaque lot dans `cache_dir/batches/` pour reprise sur interruption.
    - Pause entre les lots.
    - Réessaie les tickers qui ont échoué dans un lot.
    """
    import yfinance as yf

    batches_dir = cache_dir / "batches"
    batches_dir.mkdir(parents=True, exist_ok=True)
    end_excl = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()
    ccy_map = {c["symbol"]: c["currency"] for c in candidates}
    tickers = [c["symbol"] for c in candidates]

    prices_by_ticker: dict[str, pd.DataFrame] = {}
    all_actions: list[pd.DataFrame] = []

    total_batches = (len(tickers) + batch_size - 1) // batch_size
    for b_idx in range(total_batches):
        batch_tickers = tickers[b_idx * batch_size : (b_idx + 1) * batch_size]
        p_file = batches_dir / f"batch_{b_idx:03d}_prices.parquet"
        a_file = batches_dir / f"batch_{b_idx:03d}_actions.parquet"
        m_file = batches_dir / f"batch_{b_idx:03d}_meta.json"

        if p_file.exists() and a_file.exists() and m_file.exists():
            meta = json.loads(m_file.read_text(encoding="utf-8"))
            if meta.get("tickers") == batch_tickers and meta.get("start") == start_date and meta.get("end") == end_date:
                cached_p = pd.read_parquet(p_file)
                cached_a = pd.read_parquet(a_file)
                for t, grp in cached_p.groupby("symbol"):
                    prices_by_ticker[str(t)] = grp.reset_index(drop=True)
                if not cached_a.empty:
                    all_actions.append(cached_a)
                continue

        raw = yf.download(
            batch_tickers,
            start=start_date,
            end=end_excl,
            auto_adjust=False,
            actions=True,
            group_by="symbol",
            progress=False,
            threads=True,
        )
        is_multi = len(batch_tickers) > 1
        batch_prices: list[pd.DataFrame] = []
        batch_actions: list[pd.DataFrame] = []
        failed_tickers: list[str] = []

        for t in batch_tickers:
            p_df, a_df = _extract_ticker_frames(raw, t, ccy_map[t], is_multi=is_multi)
            if p_df.empty:
                failed_tickers.append(t)
            else:
                prices_by_ticker[t] = p_df
                batch_prices.append(p_df)
                if not a_df.empty:
                    batch_actions.append(a_df)

        # Réessai individuel des échecs du lot
        for t in failed_tickers:
            for attempt in range(max_retries):
                time.sleep(1.0 * (attempt + 1))
                try:
                    retry_raw = yf.download(
                        t,
                        start=start_date,
                        end=end_excl,
                        auto_adjust=False,
                        actions=True,
                        group_by="symbol",
                        progress=False,
                        threads=False,
                    )
                    # yfinance avec 1 ticker peut grouper par ticker ou non selon la version
                    has_top_ticker = isinstance(retry_raw.columns, pd.MultiIndex) and t in retry_raw.columns.get_level_values(0)
                    p_df, a_df = _extract_ticker_frames(retry_raw, t, ccy_map[t], is_multi=has_top_ticker)
                    if not p_df.empty:
                        prices_by_ticker[t] = p_df
                        batch_prices.append(p_df)
                        if not a_df.empty:
                            batch_actions.append(a_df)
                        break
                except Exception:  # noqa: BLE001
                    continue

        merged_p = (
            pd.concat(batch_prices, ignore_index=True)
            if batch_prices
            else pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "adjclose", "volume", "currency"])
        )
        merged_a = (
            pd.concat(batch_actions, ignore_index=True)
            if batch_actions
            else pd.DataFrame(columns=["ex_date", "symbol", "action", "value", "unit"])
        )
        merged_p.to_parquet(p_file, index=False)
        merged_a.to_parquet(a_file, index=False)
        m_file.write_text(
            json.dumps({"tickers": batch_tickers, "start": start_date, "end": end_date}, indent=2),
            encoding="utf-8",
        )
        if not merged_a.empty:
            all_actions.append(merged_a)

        if b_idx + 1 < total_batches and pause_seconds > 0:
            time.sleep(pause_seconds)

    actions_df = (
        pd.concat(all_actions, ignore_index=True).sort_values(["symbol", "ex_date"]).reset_index(drop=True)
        if all_actions
        else pd.DataFrame(columns=["ex_date", "symbol", "action", "value", "unit"])
    )
    return prices_by_ticker, actions_df


def fetch_sp500_top(n: int, cache_dir: Path, max_workers: int = 8) -> list[str]:
    """Les `n` plus grosses capitalisations du S&P 500 (Wikipédia + yfinance), symboles au format Yahoo.

    Cache JSON : la liste classée est figée pour la version du jeu de données.
    """
    import yfinance as yf

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"sp500_top{n}.json"
    if cache_file.exists():
        try:
            return list(json.loads(cache_file.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass

    html = _http_get_bytes("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies").decode("utf-8")
    table = pd.read_html(io.StringIO(html), attrs={"id": "constituents"})[0]
    symbols = table["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist()

    def _cap(t: str) -> float:
        try:
            return float(yf.Ticker(t).fast_info.market_cap)
        except Exception:  # noqa: BLE001
            return float("nan")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        caps = dict(zip(symbols, pool.map(_cap, symbols)))
    top = pd.Series(caps).dropna().nlargest(n).index.tolist()
    cache_file.write_text(json.dumps(top, indent=2), encoding="utf-8")
    return top


def fetch_yfinance_info(
    symbols: list[str],
    cache_dir: Path,
    max_workers: int = 8,
) -> dict[str, dict[str, str]]:
    """Métadonnées Yahoo (`name`, `sector`, `industry`, `country`) par symbole, avec cache JSON.

    Le secteur est ramené à la nomenclature GICS (GICS_SECTOR_MAP). Les champs absents sont omis.
    """
    import yfinance as yf

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "yfinance_info.json"
    cached: dict[str, dict[str, str]] = {}
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cached = {}

    missing = [t for t in symbols if t not in cached]

    def _fetch_one(t: str) -> tuple[str, dict[str, str]]:
        try:
            info = yf.Ticker(t).info or {}
        except Exception:  # noqa: BLE001
            return t, {}
        raw_sec = str(info.get("sector") or "").strip()
        out = {
            "name": str(info.get("shortName") or "").strip(),
            "sector": GICS_SECTOR_MAP.get(raw_sec, raw_sec),
            "industry": str(info.get("industry") or "").strip(),
            "country": str(info.get("country") or "").strip(),
        }
        return t, {k: v for k, v in out.items() if v}

    if missing:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_fetch_one, t) for t in missing]
            for fut in as_completed(futures):
                t, meta = fut.result()
                cached[t] = meta
        cache_file.write_text(json.dumps(cached, indent=2, sort_keys=True), encoding="utf-8")
    return {t: cached[t] for t in symbols if cached.get(t)}
