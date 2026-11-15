"""Script reproductible d'ingestion du jeu de données de marché AlphaForge AI (WS3).

Usage :
    # Mode hors ligne (à partir du jeu fourni alphaforge_starter ou d'une fixture) :
    .venv/bin/python -m data.ingestion.build_dataset --mode offline

    # Mode complet (nos actifs + top 400 du S&P 500 + ^GSPC depuis 2015 via yfinance, Valet BoC et FRED) :
    .venv/bin/python -m data.ingestion.build_dataset --mode full
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

from data.ingestion.fetcher import (
    download_fx_and_macro,
    download_prices_in_batches,
    fetch_sp500_top,
    fetch_yfinance_info,
)
from data.ingestion.metrics import (
    MONTHLY_MACRO_SERIES,
    PUBLICATION_DATE_RULE_DESCRIPTION,
    add_macro_publication_date,
    compute_1y_indicators,
)
from data.ingestion.quality import run_quality_checks
from data.ingestion.validators import (
    MIN_HISTORY_ROWS_DEFAULT,
    deduce_market_and_currency,
    load_universe_candidates,
    validate_candidate_prices,
    validate_etf_enriched,
)

DATA_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STARTER_DIR = (
    Path("/home/rr-djk/Documents/hackathons/Datathon2026_alphaforge")
    / "mes_docs_perso"
    / "Datathon2026"
    / "alphaforge_starter"
)
DEFAULT_UNIVERSE_YAML = DATA_DIR / "ingestion" / "universe.yaml"
DEFAULT_ETF_SOURCE_JSON = DATA_DIR / "ingestion" / "etf_enriched.source.json"
DEFAULT_OUTPUT_DIR = DATA_DIR / "output"

DEFAULT_FULL_START = "2015-01-01"
SP500_TOP_N = 400
INDEX_SYMBOLS = ("^GSPC",)
INDEX_NAMES = {"^GSPC": "S&P 500"}
DEFAULT_OFFLINE_START = "2021-11-12"
DEFAULT_END = "2026-11-13"


def _country_fallback(symbol: str) -> str:
    return "Canada" if symbol.upper().endswith(".TO") else "United States"


def _merge_candidates(base: list[dict[str, str]], sp500_top: list[str]) -> list[dict[str, str]]:
    """Nos candidats d'abord, puis les titres du S&P 500 absents, puis les indices (sans doublon)."""
    seen = {c["symbol"] for c in base}
    merged = list(base)

    def add(symbol: str, asset_class: str, name: str) -> None:
        if symbol in seen:
            return
        seen.add(symbol)
        market, currency = deduce_market_and_currency(symbol)
        merged.append({
            "symbol": symbol, "name": name, "asset_class": asset_class, "market": market,
            "currency": currency, "sector": "Unknown", "category": "sp500_top" if asset_class == "equity" else "index",
        })

    for symbol in sp500_top:
        add(symbol, "equity", symbol)
    for symbol in INDEX_SYMBOLS:
        add(symbol, "index", INDEX_NAMES.get(symbol, symbol))
    return merged


def _load_offline_inputs(
    starter_dir: Path,
) -> tuple[list[dict[str, str]], dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Charge les fichiers CSV du jeu de départ (ou d'un dossier fixture)."""
    u_df = pd.read_csv(starter_dir / "assets_universe.csv")
    p_df = pd.read_csv(starter_dir / "prices_daily.csv").rename(
        columns={"ticker": "symbol", "adj_close": "adjclose"}
    )
    a_df = pd.read_csv(starter_dir / "corporate_actions.csv").rename(columns={"ticker": "symbol"})
    fx_df = pd.read_csv(starter_dir / "fx_usdcad_daily.csv")
    m_df = pd.read_csv(starter_dir / "macro_rates.csv")

    candidates: list[dict[str, str]] = []
    for _, row in u_df.iterrows():
        ticker = str(row["ticker"]).strip()
        market, currency = deduce_market_and_currency(ticker)
        candidates.append({
            "symbol": ticker,
            "name": str(row.get("name", ticker)).strip(),
            "asset_class": str(row.get("asset_class", "equity")).strip(),
            "market": str(row.get("market") if pd.notna(row.get("market")) else market).strip(),
            "currency": str(row.get("currency") if pd.notna(row.get("currency")) else currency).strip(),
            "sector": str(row.get("sector", "Unknown")).strip(),
            "sector_source": "starter",
        })

    prices_by_ticker: dict[str, pd.DataFrame] = {}
    if not p_df.empty:
        p_df["date"] = p_df["date"].astype(str).str.slice(0, 10)
        for t, grp in p_df.groupby("symbol"):
            prices_by_ticker[str(t)] = grp.sort_values("date").reset_index(drop=True)

    return candidates, prices_by_ticker, a_df, fx_df, m_df


def build_dataset(
    mode: str = "full",
    starter_dir: Path = DEFAULT_STARTER_DIR,
    universe_yaml: Path = DEFAULT_UNIVERSE_YAML,
    etf_source_json: Path = DEFAULT_ETF_SOURCE_JSON,
    output_root: Path = DEFAULT_OUTPUT_DIR,
    version: str | None = None,
    start_date: str | None = None,
    end_date: str = DEFAULT_END,
    min_history_rows: int = MIN_HISTORY_ROWS_DEFAULT,
    batch_size: int = 75,
    pause_seconds: float = 2.0,
    strict_etf: bool = False,
) -> dict[str, Any]:
    """Exécute le pipeline d'ingestion complet ou hors ligne et retourne le manifeste."""
    if mode not in ("offline", "full"):
        raise ValueError(f"Unsupported mode: {mode!r}")

    extracted_at = date.today().isoformat()
    dataset_version = version or extracted_at
    req_start = start_date or (DEFAULT_OFFLINE_START if mode == "offline" else DEFAULT_FULL_START)
    req_end = end_date

    out_dir = output_root / dataset_version
    cache_dir = output_root / ".cache" / dataset_version
    out_dir.mkdir(parents=True, exist_ok=True)

    if mode == "offline":
        candidates, prices_by_ticker, raw_actions, fx_df, raw_macro = _load_offline_inputs(starter_dir)
        yf_info: dict[str, dict[str, str]] = {}
    else:
        candidates = _merge_candidates(
            load_universe_candidates(universe_yaml),
            fetch_sp500_top(SP500_TOP_N, cache_dir=cache_dir),
        )
        prices_by_ticker, raw_actions = download_prices_in_batches(
            candidates=candidates,
            start_date=req_start,
            end_date=req_end,
            cache_dir=cache_dir,
            batch_size=batch_size,
            pause_seconds=pause_seconds,
        )
        fx_df, raw_macro = download_fx_and_macro(
            start_date=req_start,
            end_date=req_end,
            cache_dir=cache_dir,
        )
        yahoo_symbols = [c["symbol"] for c in candidates if c["asset_class"] != "crypto"]
        yf_info = fetch_yfinance_info(yahoo_symbols, cache_dir=cache_dir)

    # Validation de chaque candidat et calcul des indicateurs 1 an
    retained_rows: list[dict[str, Any]] = []
    excluded_tickers: list[dict[str, Any]] = []
    retained_prices_list: list[pd.DataFrame] = []
    first_date_by_ticker: dict[str, str] = {}

    for cand in candidates:
        ticker = cand["symbol"]
        p_df = prices_by_ticker.get(ticker)
        val_res = validate_candidate_prices(ticker, p_df, min_rows=min_history_rows)
        if not val_res["valid"] or p_df is None:
            excluded_tickers.append({
                "symbol": ticker,
                "name": cand.get("name", ticker),
                "assetClass": cand.get("asset_class", "equity"),
                "reason": val_res["reason"],
                "firstDate": val_res["first_date"],
                "lastDate": val_res["last_date"],
                "rows": val_res["rows"],
            })
            continue

        clean_p = p_df.dropna(subset=["close", "adjclose"]).sort_values("date").reset_index(drop=True)
        clean_p["date"] = clean_p["date"].astype(str).str.slice(0, 10)
        clean_p["symbol"] = ticker
        clean_p["currency"] = cand["currency"]
        for c in ("open", "high", "low", "close", "adjclose"):
            clean_p[c] = pd.to_numeric(clean_p[c], errors="coerce").round(6)
        clean_p["volume"] = pd.to_numeric(clean_p["volume"], errors="coerce").fillna(0).astype("int64")
        clean_p = clean_p[
            ["date", "symbol", "open", "high", "low", "close", "adjclose", "volume", "currency"]
        ]

        indicators = compute_1y_indicators(clean_p)

        # Métadonnées : Yahoo en priorité pour actions, FNB et indice ; repli sur la liste de candidats
        meta = yf_info.get(ticker, {})
        sector = cand["sector"]
        sector_source = cand.get("sector_source", "universe.yaml")
        name = cand["name"]
        industry: str | None = None
        country: str | None = None
        if mode == "offline":
            sector_source = cand.get("sector_source", "starter")
            if cand["asset_class"] != "crypto":
                country = _country_fallback(ticker)
        elif cand["asset_class"] != "crypto":
            if meta.get("sector"):
                sector, sector_source = meta["sector"], "yfinance"
            name = meta.get("name") or name
            industry = meta.get("industry")
            country = meta.get("country") or _country_fallback(ticker)

        first_d = str(val_res["first_date"])
        last_d = str(val_res["last_date"])
        first_date_by_ticker[ticker] = first_d

        retained_rows.append({
            "symbol": ticker,
            "name": name,
            "asset_class": cand["asset_class"],
            "market": cand["market"],
            "currency": cand["currency"],
            "sector": sector,
            "sector_source": sector_source,
            "industry": industry,
            "country": country,
            "first_date": first_d,
            "last_date": last_d,
            "return_1y": indicators["return_1y"],
            "volatility_1y": indicators["volatility_1y"],
            "max_drawdown_1y": indicators["max_drawdown_1y"],
        })
        retained_prices_list.append(clean_p)

    if not retained_rows:
        raise RuntimeError("No candidate passed validation.")

    universe_df = pd.DataFrame(retained_rows)
    universe_df.insert(0, "asset_id", [f"A{i:02d}" for i in range(1, len(universe_df) + 1)])

    prices_df = pd.concat(retained_prices_list, ignore_index=True).sort_values(["symbol", "date"]).reset_index(drop=True)

    # Filtrer corporate_actions aux seuls tickers retenus
    retained_set = set(universe_df["symbol"])
    if not raw_actions.empty:
        actions_df = raw_actions[raw_actions["symbol"].isin(retained_set)].copy()
        actions_df["ex_date"] = actions_df["ex_date"].astype(str).str.slice(0, 10)
        actions_df = actions_df.sort_values(["symbol", "ex_date"]).reset_index(drop=True)
    else:
        actions_df = pd.DataFrame(columns=["ex_date", "symbol", "action", "value", "unit"])

    # Macro avec publication_date (snake_case)
    macro_df = add_macro_publication_date(raw_macro)
    macro_df = macro_df[
        ["date", "series_id", "value", "unit", "frequency", "label", "source", "publication_date"]
    ].sort_values(["series_id", "date"]).reset_index(drop=True)

    fx_df = fx_df.copy()
    fx_df["date"] = fx_df["date"].astype(str).str.slice(0, 10)
    fx_df["usdcad"] = pd.to_numeric(fx_df["usdcad"], errors="coerce").round(6)
    fx_df["cadusd"] = pd.to_numeric(fx_df["cadusd"], errors="coerce").round(6)
    fx_df = fx_df[["date", "usdcad", "cadusd"]].sort_values("date").reset_index(drop=True)

    # Contrôle qualité et isolation de l'anomalie CNQ.TO 2022-08-22
    enriched_actions_df, quality_report = run_quality_checks(
        universe_df=universe_df,
        prices_df=prices_df,
        actions_df=actions_df,
        fx_df=fx_df,
        macro_df=macro_df,
        requested_start=req_start,
        requested_end=req_end,
    )

    # Validation et génération de etf_enriched.json
    etf_raw = json.loads(etf_source_json.read_text(encoding="utf-8"))
    asset_class_map = dict(zip(universe_df["symbol"], universe_df["asset_class"]))
    etf_output, etf_errors, etf_warnings = validate_etf_enriched(
        source_data=etf_raw,
        universe_asset_classes=asset_class_map,
        strict=strict_etf,
    )
    if etf_errors:
        raise ValueError(f"etf_enriched validation failed: {etf_errors}")
    quality_report["etfEnrichedWarningsCount"] = len(etf_warnings)
    quality_report["etfEnrichedWarnings"] = etf_warnings

    # Écriture de l'arborescence Parquet et JSON conforme à storage-dataset
    universe_df.to_parquet(out_dir / "universe.parquet", index=False)

    prices_dir = out_dir / "prices"
    prices_dir.mkdir(parents=True, exist_ok=True)
    for ticker, grp in prices_df.groupby("symbol", sort=False):
        grp.reset_index(drop=True).to_parquet(prices_dir / f"{ticker}.parquet", index=False)

    prices_all_dir = out_dir / "prices_all"
    prices_all_dir.mkdir(parents=True, exist_ok=True)
    prices_with_year = prices_df.copy()
    prices_with_year["_year"] = prices_with_year["date"].str.slice(0, 4)
    for year_str, grp in prices_with_year.groupby("_year", sort=True):
        year_dir = prices_all_dir / f"year={year_str}"
        year_dir.mkdir(parents=True, exist_ok=True)
        grp.drop(columns=["_year"]).reset_index(drop=True).to_parquet(
            year_dir / "part-0.parquet", index=False
        )

    fx_dir = out_dir / "fx"
    fx_dir.mkdir(parents=True, exist_ok=True)
    fx_df.to_parquet(fx_dir / "usdcad.parquet", index=False)

    macro_dir = out_dir / "macro"
    macro_dir.mkdir(parents=True, exist_ok=True)
    macro_df.to_parquet(macro_dir / "macro.parquet", index=False)

    enriched_actions_df.to_parquet(out_dir / "corporate_actions.parquet", index=False)

    (out_dir / "etf_enriched.json").write_text(
        json.dumps(etf_output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    actual_start = str(prices_df["date"].min())[:10]
    actual_end = str(prices_df["date"].max())[:10]

    manifest: dict[str, Any] = {
        "version": dataset_version,
        "extractedAt": extracted_at,
        "mode": mode,
        "period": {
            "requestedStart": req_start,
            "requestedEnd": req_end,
            "actualStart": actual_start,
            "actualEnd": actual_end,
        },
        "counts": {
            "candidatesTotal": len(candidates),
            "retainedCount": len(universe_df),
            "excludedCount": len(excluded_tickers),
            "priceRows": int(len(prices_df)),
            "corporateActionRows": int(len(enriched_actions_df)),
            "fxRows": int(len(fx_df)),
            "macroRows": int(len(macro_df)),
        },
        "currencies": ["CAD", "USD"],
        "retainedTickers": universe_df["symbol"].tolist(),
        "excludedTickers": excluded_tickers,
        "firstDateByTicker": first_date_by_ticker,
        "shortHistoryTickers": quality_report["shortHistories"],
        "publicationDateRule": {
            "monthlySeries": sorted(MONTHLY_MACRO_SERIES),
            "monthlyRule": "YYYY-(MM+1)-28 (28th of the month following the reference month)",
            "dailyRule": "publication_date = date",
            "description": PUBLICATION_DATE_RULE_DESCRIPTION,
        },
        "sources": [
            {
                "id": "ext-yahoo-finance",
                "name": "Yahoo Finance via yfinance",
                "url": "https://finance.yahoo.com",
                "retrievedOn": extracted_at,
                "coverage": f"{actual_start} to {actual_end}",
                "frequency": "daily (trading days per market; crypto 7 days/week UTC)",
                "termsOfUse": "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html (personal/educational use)",
            },
            {
                "id": "ext-bank-of-canada",
                "name": "Bank of Canada Valet API",
                "url": "https://www.bankofcanada.ca/valet/docs",
                "retrievedOn": extracted_at,
                "coverage": f"{fx_df['date'].min() if not fx_df.empty else req_start} to {fx_df['date'].max() if not fx_df.empty else req_end}",
                "series": ["FXUSDCAD", "V39079", "BD.CDN.2YR.DQ.YLD", "BD.CDN.10YR.DQ.YLD", "STATIC_TOTALCPICHANGE"],
                "termsOfUse": "https://www.bankofcanada.ca/terms/",
            },
            {
                "id": "ext-fred",
                "name": "FRED, Federal Reserve Bank of St. Louis",
                "url": "https://fred.stlouisfed.org",
                "retrievedOn": extracted_at,
                "series": ["DFF", "DGS2", "DGS10", "CPIAUCSL", "UNRATE"],
                "termsOfUse": "https://fred.stlouisfed.org/legal/",
            },
            {
                "id": "etf-issuer-factsheets",
                "name": "ETF Issuer Fact Sheets (iShares, Vanguard, SPDR, Invesco, BMO)",
                "retrievedOn": extracted_at,
                "note": "Manual lookup in data/ingestion/etf_enriched.source.json for the 15 key ETFs; other ETFs marked 'composition non disponible'.",
            },
        ],
        "processing": [
            "Prices kept in native listing currency (.TO = CAD, others = USD); no forward-fill and no calendar alignment.",
            "Column names follow the team calculation code: symbol (not ticker) and adjclose (not adj_close).",
            "Universe = our candidates (universe.yaml) + the 400 largest S&P 500 market caps at extraction (Wikipedia list, Yahoo fast_info market cap) + the ^GSPC index (asset_class='index', not investable). History starts 2015-01-01 for all.",
            "industry and country come from Yahoo Finance (Ticker.info) for equities, ETFs and the index; country falls back to the listing suffix (.TO = Canada, else United States); both are null for crypto.",
            "adjclose back-adjusted by Yahoo Finance for splits and dividends; close adjusted for splits only; splits in corporate_actions.parquet are never re-applied.",
            "1-year indicators in universe.parquet (return_1y, volatility_1y, max_drawdown_1y) computed on the last 1 year of adjclose with sqrt(252) annualization.",
            "Candidate validation rejects tickers with no data, non-positive prices, or fewer than min_history_rows observations; shorter histories (< 10 years, e.g. ZEQT.TO launched in 2022) are retained without backfill and flagged via first_date / firstDate.",
            "Sectors enriched from yfinance metadata (sector_source='yfinance') with fallback to universe.yaml (sector_source='universe.yaml').",
            "Monthly macro series (STATIC_TOTALCPICHANGE, CPIAUCSL, UNRATE) assigned publication_date = 28th of the following month (conservative rule R10); daily series assigned publication_date = date.",
            "CNQ.TO 2022-08-22 1.021 split on the day of a 0.75 CAD dividend isolated in corporate_actions.parquet (anomaly_note) and qualityReport.isolatedAnomalies.",
        ],
        "qualityReport": quality_report,
    }

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("offline", "full"),
        default="full",
        help="Mode d'exécution : 'offline' (depuis starter_dir) ou 'full' (réseau, ~250 actifs sur 10 ans).",
    )
    parser.add_argument(
        "--starter-dir",
        type=Path,
        default=DEFAULT_STARTER_DIR,
        help="Dossier du jeu de départ pour le mode hors ligne.",
    )
    parser.add_argument(
        "--universe-yaml",
        type=Path,
        default=DEFAULT_UNIVERSE_YAML,
        help="Chemin de universe.yaml (mode full).",
    )
    parser.add_argument(
        "--etf-source",
        type=Path,
        default=DEFAULT_ETF_SOURCE_JSON,
        help="Chemin de etf_enriched.source.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Dossier racine de sortie (data/output).",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Version du jeu (YYYY-MM-DD, défaut = date d'extraction).",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Date de début YYYY-MM-DD (défaut : 2016-11-12 en full, 2021-11-12 en offline).",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=DEFAULT_END,
        help="Date de fin YYYY-MM-DD (défaut : 2026-11-13).",
    )
    parser.add_argument(
        "--min-history-days",
        type=int,
        default=MIN_HISTORY_ROWS_DEFAULT,
        help="Seuil minimal d'observations pour retenir un candidat (défaut : 252).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=75,
        help="Taille des lots yfinance (50 à 100, défaut : 75).",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=2.0,
        help="Pause en secondes entre les lots yfinance.",
    )
    parser.add_argument(
        "--strict-etf",
        action="store_true",
        help="Échoue si une fiche de etf_enriched.source.json est encore un gabarit vide.",
    )
    args = parser.parse_args(argv)

    manifest = build_dataset(
        mode=args.mode,
        starter_dir=args.starter_dir,
        universe_yaml=args.universe_yaml,
        etf_source_json=args.etf_source,
        output_root=args.output_dir,
        version=args.version,
        start_date=args.start,
        end_date=args.end,
        min_history_rows=args.min_history_days,
        batch_size=args.batch_size,
        pause_seconds=args.pause_seconds,
        strict_etf=args.strict_etf,
    )
    counts = manifest["counts"]
    period = manifest["period"]
    print(
        f"[WS3] Dataset version={manifest['version']} mode={manifest['mode']} "
        f"period={period['actualStart']}..{period['actualEnd']} "
        f"retained={counts['retainedCount']}/{counts['candidatesTotal']} "
        f"(excluded={counts['excludedCount']}) "
        f"price_rows={counts['priceRows']} fx_rows={counts['fxRows']} macro_rows={counts['macroRows']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
