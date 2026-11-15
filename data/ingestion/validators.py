"""Validation des candidats de l'univers et de etf_enriched.json (WS3)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
import pandas as pd
import yaml

KEY_ETFS: tuple[str, ...] = (
    "XIU.TO",
    "SPY",
    "QQQ",
    "ESGV",
    "XBB.TO",
    "ZST.TO",
    "AGG",
    "TLT",
    "GLD",
    "XSP.TO",
    "ZEQT.TO",
    "XEQT.TO",
    "VFV.TO",
    "ZAG.TO",
    "XIC.TO",
)

MIN_HISTORY_ROWS_DEFAULT: int = 252


def deduce_market_and_currency(ticker: str) -> tuple[str, str]:
    """Déduit (market, currency) à partir du suffixe du ticker."""
    t = ticker.strip().upper()
    if t.endswith(".TO"):
        return "TSX", "CAD"
    if t.endswith("-USD"):
        return "Crypto (24/7)", "USD"
    return "US", "USD"


def load_universe_candidates(yaml_path: Path) -> list[dict[str, str]]:
    """Charge et déduplique la liste des candidats depuis universe.yaml."""
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    categories = raw.get("categories", {})
    seen: set[str] = set()
    candidates: list[dict[str, str]] = []
    for cat_name, cat_data in categories.items():
        default_asset_class = str(cat_data.get("asset_class", "equity"))
        default_sector = str(cat_data.get("default_sector", cat_name))
        for item in cat_data.get("candidates", []):
            ticker = str(item["ticker"]).strip()
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            market, currency = deduce_market_and_currency(ticker)
            candidates.append({
                "ticker": ticker,
                "name": str(item.get("name", ticker)).strip(),
                "asset_class": str(item.get("asset_class", default_asset_class)).strip(),
                "market": str(item.get("market", market)).strip(),
                "currency": str(item.get("currency", currency)).strip(),
                "sector": str(item.get("sector", default_sector)).strip(),
                "category": cat_name,
            })
    return candidates


def validate_candidate_prices(
    ticker: str,
    df: pd.DataFrame | None,
    min_rows: int = MIN_HISTORY_ROWS_DEFAULT,
) -> dict[str, Any]:
    """Valide les données de prix d'un candidat.

    Un ticker sans données, avec des prix <= 0 ou avec moins de `min_rows`
    observations est écarté avec une raison explicite.
    """
    if not ticker or not ticker.strip():
        return {
            "valid": False,
            "reason": "empty_ticker",
            "first_date": None,
            "last_date": None,
            "rows": 0,
        }
    if df is None or df.empty:
        return {
            "valid": False,
            "reason": "no_data",
            "first_date": None,
            "last_date": None,
            "rows": 0,
        }

    required_cols = {"date", "open", "high", "low", "close", "adj_close"}
    if not required_cols.issubset(set(df.columns)):
        return {
            "valid": False,
            "reason": "missing_columns",
            "first_date": None,
            "last_date": None,
            "rows": 0,
        }

    clean = df.dropna(subset=["close", "adj_close"]).copy()
    if clean.empty:
        return {
            "valid": False,
            "reason": "no_data",
            "first_date": None,
            "last_date": None,
            "rows": 0,
        }

    for price_col in ("open", "high", "low", "close", "adj_close"):
        vals = pd.to_numeric(clean[price_col], errors="coerce")
        if vals.isna().any() or (vals <= 0).any():
            return {
                "valid": False,
                "reason": f"invalid_or_non_positive_{price_col}",
                "first_date": str(clean["date"].min())[:10],
                "last_date": str(clean["date"].max())[:10],
                "rows": len(clean),
            }

    first_date = str(clean["date"].min())[:10]
    last_date = str(clean["date"].max())[:10]
    row_count = len(clean)

    if row_count < min_rows:
        return {
            "valid": False,
            "reason": f"insufficient_history ({row_count} < {min_rows} observations)",
            "first_date": first_date,
            "last_date": last_date,
            "rows": row_count,
        }

    return {
        "valid": True,
        "reason": None,
        "first_date": first_date,
        "last_date": last_date,
        "rows": row_count,
    }


def _is_valid_iso_date(val: Any) -> bool:
    if not isinstance(val, str) or len(val.strip()) != 10:
        return False
    try:
        date.fromisoformat(val.strip())
        return True
    except ValueError:
        return False


def _is_valid_url(val: Any) -> bool:
    return isinstance(val, str) and val.strip().startswith(("http://", "https://"))


def _is_entry_populated(entry: dict[str, Any]) -> bool:
    mer = entry.get("merPct") or {}
    if mer.get("value") is not None:
        return True
    for key in ("sectorWeights", "topHoldings", "countryWeights"):
        sec = entry.get(key) or {}
        if sec.get("items"):
            return True
    return False


def validate_etf_entry(ticker: str, entry: dict[str, Any]) -> list[str]:
    """Valide une fiche FNB renseignée (poids proches de 100, dates et URLs présentes)."""
    errors: list[str] = []

    mer = entry.get("merPct")
    if not isinstance(mer, dict):
        errors.append(f"{ticker}: missing merPct object")
    else:
        val = mer.get("value")
        if not isinstance(val, (int, float)) or val < 0 or val > 5.0:
            errors.append(f"{ticker}.merPct: invalid value {val!r} (expected 0 <= value <= 5.0)")
        if not _is_valid_url(mer.get("sourceUrl")):
            errors.append(f"{ticker}.merPct: missing or invalid sourceUrl")
        if not _is_valid_iso_date(mer.get("asOfDate")):
            errors.append(f"{ticker}.merPct: missing or invalid asOfDate (YYYY-MM-DD)")

    for weight_field in ("sectorWeights", "countryWeights"):
        block = entry.get(weight_field)
        if not isinstance(block, dict):
            errors.append(f"{ticker}: missing {weight_field} object")
            continue
        if not _is_valid_url(block.get("sourceUrl")):
            errors.append(f"{ticker}.{weight_field}: missing or invalid sourceUrl")
        if not _is_valid_iso_date(block.get("asOfDate")):
            errors.append(f"{ticker}.{weight_field}: missing or invalid asOfDate")
        items = block.get("items")
        if not isinstance(items, list) or len(items) == 0:
            errors.append(f"{ticker}.{weight_field}: items must be a non-empty list")
            continue
        weights: list[float] = []
        for idx, item in enumerate(items):
            w = item.get("weight") if isinstance(item, dict) else None
            if not isinstance(w, (int, float)) or w < 0 or w > 100:
                errors.append(f"{ticker}.{weight_field}[{idx}]: invalid weight {w!r}")
            else:
                weights.append(float(w))
        total_w = sum(weights)
        if not (95.0 <= total_w <= 105.0):
            errors.append(
                f"{ticker}.{weight_field}: sum of weights is {total_w:.2f}%, expected close to 100% ([95.0, 105.0])"
            )

    th = entry.get("topHoldings")
    if not isinstance(th, dict):
        errors.append(f"{ticker}: missing topHoldings object")
    else:
        if not _is_valid_url(th.get("sourceUrl")):
            errors.append(f"{ticker}.topHoldings: missing or invalid sourceUrl")
        if not _is_valid_iso_date(th.get("asOfDate")):
            errors.append(f"{ticker}.topHoldings: missing or invalid asOfDate")
        items = th.get("items")
        min_holdings = 1 if th.get("allowWrapperSingleHolding") else 5
        if not isinstance(items, list) or not (min_holdings <= len(items) <= 10):
            errors.append(
                f"{ticker}.topHoldings: expected {min_holdings} to 10 holdings, got {len(items) if isinstance(items, list) else 'non-list'}"
            )
        else:
            total_th = 0.0
            for idx, item in enumerate(items):
                w = item.get("weight") if isinstance(item, dict) else None
                if not isinstance(w, (int, float)) or w <= 0 or w > 100:
                    errors.append(f"{ticker}.topHoldings[{idx}]: invalid weight {w!r}")
                else:
                    total_th += float(w)
            if total_th <= 0 or total_th > 105.0:
                errors.append(f"{ticker}.topHoldings: invalid total weight {total_th:.2f}%")

    if ticker == "ESGV":
        excl = entry.get("exclusions")
        if not isinstance(excl, dict):
            errors.append("ESGV.exclusions: required for ESGV")
        else:
            if not _is_valid_url(excl.get("sourceUrl")):
                errors.append("ESGV.exclusions: missing or invalid sourceUrl")
            if not _is_valid_iso_date(excl.get("asOfDate")):
                errors.append("ESGV.exclusions: missing or invalid asOfDate")
            items = excl.get("items")
            if not isinstance(items, list) or len(items) == 0:
                errors.append("ESGV.exclusions: items must be a non-empty list")

    return errors


def validate_etf_enriched(
    source_data: dict[str, Any],
    universe_asset_classes: dict[str, str] | None = None,
    strict: bool = True,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Valide `etf_enriched.source.json` et construit la structure finale `etf_enriched.json`.

    Retourne `(output_dict, errors, warnings)`.
    - Aucun indicateur ESG ou fiche pour les actions (`equity`) n'est accepté.
    - Si `strict=True`, une fiche de `source_data["etfs"]` non remplie est une erreur.
    - Si `strict=False`, une fiche gabarit non encore remplie est signalée en warning
      et marquée `"composition non disponible"` dans la sortie, sans inventer de valeur.
    """
    errors: list[str] = []
    warnings: list[str] = []
    etfs_in = source_data.get("etfs", {})
    if not isinstance(etfs_in, dict):
        return {}, ["root 'etfs' must be a dict"], []

    asset_classes = universe_asset_classes or {}
    out_etfs: dict[str, Any] = {}

    for ticker, entry in etfs_in.items():
        ac = asset_classes.get(ticker, "")
        if ac == "equity":
            errors.append(f"{ticker}: equities are forbidden in etf_enriched (no ESG/composition data for equities)")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{ticker}: entry must be a dict")
            continue

        if not _is_entry_populated(entry):
            msg = f"{ticker}: template entry not yet populated with issuer values"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
            out_etfs[ticker] = {
                "ticker": ticker,
                "name": entry.get("name", ticker),
                "issuer": entry.get("issuer", ""),
                "isKeyEtf": ticker in KEY_ETFS,
                "compositionAvailable": False,
                "status": "composition non disponible",
                "sectorWeights": None,
                "topHoldings": None,
                "countryWeights": None,
                "merPct": None,
                "exclusions": None,
            }
            continue

        entry_errors = validate_etf_entry(ticker, entry)
        if entry_errors:
            errors.extend(entry_errors)
            continue

        out_etfs[ticker] = {
            "ticker": ticker,
            "name": entry.get("name", ticker),
            "issuer": entry.get("issuer", ""),
            "isKeyEtf": ticker in KEY_ETFS,
            "compositionAvailable": True,
            "status": "available",
            "merPct": entry["merPct"],
            "sectorWeights": entry["sectorWeights"],
            "topHoldings": entry["topHoldings"],
            "countryWeights": entry["countryWeights"],
            "exclusions": entry.get("exclusions"),
        }

    # Marquer tous les autres FNB de l'univers comme « composition non disponible »
    for ticker, ac in sorted(asset_classes.items()):
        if ac.startswith("etf_") and ticker not in out_etfs:
            out_etfs[ticker] = {
                "ticker": ticker,
                "isKeyEtf": ticker in KEY_ETFS,
                "compositionAvailable": False,
                "status": "composition non disponible",
                "sectorWeights": None,
                "topHoldings": None,
                "countryWeights": None,
                "merPct": None,
                "exclusions": None,
            }

    output = {
        "schemaVersion": source_data.get("schemaVersion", "1.0"),
        "keyEtfs": list(KEY_ETFS),
        "note": (
            "Detailed composition (sectorWeights, topHoldings, countryWeights, merPct, and exclusions for ESGV) "
            "is tracked for the 15 key ETFs from issuer fact sheets with sourceUrl and asOfDate. "
            "Other ETFs are marked 'composition non disponible'. No ESG indicators exist for equities."
        ),
        "etfs": out_etfs,
    }
    return output, errors, warnings
