"""Tests unitaires hors ligne pour le pipeline d'ingestion WS3 (data/).

Aucun appel réseau ni appel AWS n'est effectué dans ces tests.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from data.ingestion.build_dataset import (
    DEFAULT_ETF_SOURCE_JSON,
    DEFAULT_STARTER_DIR,
    DEFAULT_UNIVERSE_YAML,
    build_dataset,
)
from data.ingestion.metrics import (
    add_macro_publication_date,
    compute_1y_indicators,
    compute_monthly_publication_date,
)
from data.ingestion.quality import (
    isolate_cnq_anomaly_and_check_actions,
    run_quality_checks,
)
from data.ingestion.validators import (
    KEY_ETFS,
    deduce_market_and_currency,
    load_universe_candidates,
    validate_candidate_prices,
    validate_etf_enriched,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# ==========================================================================
# 1. Tests des indicateurs précalculés sur 1 an (return_1y, volatility_1y, max_drawdown_1y)
# ==========================================================================


def test_compute_1y_indicators_exact_math() -> None:
    """Vérifie le calcul exact du rendement total, de la volatilité √252 et du max drawdown sur adj_close."""
    # Série synthétique : 100 -> 110 -> 99 -> 121
    # close est volontairement différent pour vérifier que seul adj_close est utilisé.
    df = pd.DataFrame({
        "date": ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"],
        "close": [100.0, 100.0, 100.0, 100.0],
        "adj_close": [100.0, 110.0, 99.0, 121.0],
    })
    res = compute_1y_indicators(df)

    # Rendement total : 121 / 100 - 1 = 0.21
    assert res["return_1y"] == pytest.approx(0.21, abs=1e-6)

    # Max drawdown : creux à 99 après pic à 110 -> 99 / 110 - 1 = -0.10
    assert res["max_drawdown_1y"] == pytest.approx(-0.10, abs=1e-6)

    # Rendements quotidiens : +0.10, -0.10, +22/99 (+0.222222...)
    expected_r = pd.Series([100.0, 110.0, 99.0, 121.0]).pct_change().dropna()
    expected_vol = float(expected_r.std(ddof=1) * math.sqrt(252.0))
    assert res["volatility_1y"] == pytest.approx(expected_vol, abs=1e-6)


def test_compute_1y_indicators_on_fixtures() -> None:
    """Vérifie le calcul des indicateurs sur les 3 tickers du mini-jeu data/fixtures/."""
    prices = pd.read_csv(FIXTURES_DIR / "prices_daily.csv")
    for ticker in ("RY.TO", "CNQ.TO", "SPY"):
        sub = prices[prices["ticker"] == ticker]
        ind = compute_1y_indicators(sub)
        assert ind["return_1y"] is not None
        assert ind["volatility_1y"] is not None and ind["volatility_1y"] > 0
        assert ind["max_drawdown_1y"] is not None and ind["max_drawdown_1y"] <= 0


def test_compute_1y_indicators_edge_cases() -> None:
    """Vérifie le comportement sur DataFrame vide, ligne unique ou prix négatif."""
    assert compute_1y_indicators(pd.DataFrame()) == {
        "return_1y": None,
        "volatility_1y": None,
        "max_drawdown_1y": None,
    }
    single = pd.DataFrame({"date": ["2026-01-01"], "adj_close": [100.0]})
    assert compute_1y_indicators(single)["return_1y"] is None

    neg = pd.DataFrame({"date": ["2026-01-01", "2026-01-02"], "adj_close": [100.0, -5.0]})
    assert compute_1y_indicators(neg)["return_1y"] is None


# ==========================================================================
# 2. Tests de publication_date sur les séries macro (règle R10 : 28 du mois suivant)
# ==========================================================================


def test_compute_monthly_publication_date_rule_28th_next_month() -> None:
    """Vérifie que les séries mensuelles prennent le 28 du mois suivant (y compris décembre -> janvier)."""
    assert compute_monthly_publication_date("2024-05-01") == "2024-06-28"
    assert compute_monthly_publication_date("2025-10-01") == "2025-11-28"
    assert compute_monthly_publication_date("2025-12-01") == "2026-01-28"
    assert compute_monthly_publication_date("2024-01-01") == "2024-02-28"


def test_add_macro_publication_date_on_fixtures() -> None:
    """Vérifie publication_date sur macro_rates.csv de data/fixtures/."""
    macro = pd.read_csv(FIXTURES_DIR / "macro_rates.csv")
    out = add_macro_publication_date(macro)

    assert "publication_date" in out.columns

    monthly_mask = out["series_id"].isin({"STATIC_TOTALCPICHANGE", "CPIAUCSL", "UNRATE"})
    monthly_rows = out[monthly_mask]
    daily_rows = out[~monthly_mask]

    assert not monthly_rows.empty
    assert not daily_rows.empty

    # Séries journalières : publication_date == date
    assert (daily_rows["publication_date"] == daily_rows["date"]).all()

    # Séries mensuelles : publication_date > date et se termine par "-28"
    assert (monthly_rows["publication_date"] > monthly_rows["date"]).all()
    assert monthly_rows["publication_date"].str.endswith("-28").all()

    # Exemple précis : juillet 2022 (2022-07-01) -> 2022-08-28
    july_cpi = monthly_rows[
        (monthly_rows["series_id"] == "CPIAUCSL") & (monthly_rows["date"] == "2022-07-01")
    ]
    assert not july_cpi.empty
    assert july_cpi["publication_date"].iloc[0] == "2022-08-28"


# ==========================================================================
# 3. Tests de la validation des candidats et de universe.yaml
# ==========================================================================


def test_deduce_market_and_currency() -> None:
    assert deduce_market_and_currency("RY.TO") == ("TSX", "CAD")
    assert deduce_market_and_currency("BIP-UN.TO") == ("TSX", "CAD")
    assert deduce_market_and_currency("BTC-USD") == ("Crypto (24/7)", "USD")
    assert deduce_market_and_currency("SOL-USD") == ("Crypto (24/7)", "USD")
    assert deduce_market_and_currency("AAPL") == ("US", "USD")
    assert deduce_market_and_currency("BRK-B") == ("US", "USD")


def test_validate_candidate_prices_rejects_empty_and_short_and_bad_prices() -> None:
    """Teste le rejet d'un ticker vide, d'un historique trop court et d'un prix <= 0."""
    # 1. DataFrame vide
    res_empty = validate_candidate_prices("FAKE.TO", pd.DataFrame(), min_rows=252)
    assert res_empty["valid"] is False
    assert res_empty["reason"] == "no_data"

    # 2. Historique trop court (60 lignes < 252)
    prices = pd.read_csv(FIXTURES_DIR / "prices_daily.csv")
    ry_short = prices[prices["ticker"] == "RY.TO"].copy()
    assert len(ry_short) < 252
    res_short = validate_candidate_prices("RY.TO", ry_short, min_rows=252)
    assert res_short["valid"] is False
    assert "insufficient_history" in res_short["reason"]

    # 3. Historique suffisant mais plus court que 10 ans (ex. min_rows=50) -> conservé avec first_date
    res_ok = validate_candidate_prices("RY.TO", ry_short, min_rows=50)
    assert res_ok["valid"] is True
    assert res_ok["reason"] is None
    assert res_ok["first_date"] == "2022-07-04"
    assert res_ok["last_date"] == "2022-09-30"

    # 4. Prix nul ou négatif -> écarté
    bad_df = ry_short.copy()
    bad_df.loc[bad_df.index[0], "adj_close"] = 0.0
    res_bad = validate_candidate_prices("RY.TO", bad_df, min_rows=10)
    assert res_bad["valid"] is False
    assert "invalid_or_non_positive_adj_close" in res_bad["reason"]


def test_universe_yaml_coverage() -> None:
    """Vérifie que universe.yaml contient ~250 candidats dont les 31 du starter et tous les titres requis."""
    candidates = load_universe_candidates(DEFAULT_UNIVERSE_YAML)
    tickers = {c["ticker"] for c in candidates}

    assert 220 <= len(candidates) <= 280

    # Les 31 actifs du jeu de départ doivent tous y figurer
    starter_u = pd.read_csv(DEFAULT_STARTER_DIR / "assets_universe.csv")
    starter_tickers = set(starter_u["ticker"])
    assert starter_tickers.issubset(tickers)

    # FNB canadiens, US et cryptos exigés par l'énoncé WS3
    required_Prompt_tickers = {
        # FNB canadiens
        "XIC.TO", "ZCN.TO", "VCN.TO", "XSP.TO", "VFV.TO", "ZSP.TO", "XUS.TO", "XEF.TO", "XEC.TO", "XAW.TO",
        "ZEQT.TO", "XEQT.TO", "VEQT.TO", "XGRO.TO", "VGRO.TO", "XBAL.TO", "VBAL.TO",
        "ZAG.TO", "XSB.TO", "ZFL.TO", "XHY.TO",
        "XEI.TO", "ZDV.TO", "ZWC.TO",
        "XIT.TO", "XFN.TO", "XEG.TO", "XUT.TO", "XRE.TO",
        "XGD.TO", "CGL.TO", "XESG.TO", "CASH.TO", "ZMMK.TO",
        # FNB américains
        "VTI", "VOO", "IVV", "IWM", "VEA", "VWO", "EFA", "EEM",
        "XLK", "XLF", "XLE", "XLV", "XLU", "XLP", "XLI", "XLY", "XLB", "XLRE", "XLC",
        "BND", "IEF", "SHY", "TIP", "LQD", "HYG",
        "IAU", "VNQ", "ESGU", "SUSA", "ICLN", "SOXX", "SMH", "ARKK",
        # Cryptos
        "BTC-USD", "ETH-USD", "SOL-USD",
    }
    missing = required_Prompt_tickers - tickers
    assert not missing, f"Missing required tickers in universe.yaml: {missing}"


# ==========================================================================
# 4. Tests de la validation de etf_enriched
# ==========================================================================


def _make_valid_etf_entry(ticker: str = "SPY", is_esgv: bool = False) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ticker": ticker,
        "name": "Sample ETF",
        "issuer": "Sample Issuer",
        "merPct": {
            "value": 0.09,
            "sourceUrl": "https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy",
            "asOfDate": "2026-10-31",
        },
        "sectorWeights": {
            "sourceUrl": "https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy",
            "asOfDate": "2026-10-31",
            "items": [
                {"sector": "Information Technology", "weight": 31.5},
                {"sector": "Financials", "weight": 13.5},
                {"sector": "Health Care", "weight": 11.5},
                {"sector": "Consumer Discretionary", "weight": 10.5},
                {"sector": "Other", "weight": 33.0},
            ],
        },
        "topHoldings": {
            "sourceUrl": "https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy",
            "asOfDate": "2026-10-31",
            "items": [
                {"ticker": "AAPL", "name": "Apple Inc.", "weight": 7.1},
                {"ticker": "NVDA", "name": "NVIDIA Corp.", "weight": 6.8},
                {"ticker": "MSFT", "name": "Microsoft Corp.", "weight": 6.5},
                {"ticker": "AMZN", "name": "Amazon.com Inc.", "weight": 3.8},
                {"ticker": "META", "name": "Meta Platforms Inc.", "weight": 2.5},
            ],
        },
        "countryWeights": {
            "sourceUrl": "https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy",
            "asOfDate": "2026-10-31",
            "items": [
                {"country": "United States", "weight": 100.0},
            ],
        },
        "exclusions": None,
    }
    if is_esgv:
        entry["exclusions"] = {
            "sourceUrl": "https://investor.vanguard.com/investment-products/etfs/profile/esgv",
            "asOfDate": "2026-10-31",
            "items": [
                "Adult entertainment",
                "Alcohol and tobacco",
                "Controversial and civilian weapons",
                "Fossil fuels",
                "Gambling and nuclear power",
            ],
        }
    return entry


def test_validate_etf_enriched_valid_and_other_etfs_marked_unavailable() -> None:
    """Vérifie qu'une fiche valide passe et que les autres FNB sont marqués 'composition non disponible'."""
    source = {
        "schemaVersion": "1.0",
        "keyEtfs": list(KEY_ETFS),
        "etfs": {
            "SPY": _make_valid_etf_entry("SPY"),
            "ESGV": _make_valid_etf_entry("ESGV", is_esgv=True),
        },
    }
    universe_classes = {
        "SPY": "etf_equity",
        "ESGV": "etf_equity",
        "XLK": "etf_equity",
        "RY.TO": "equity",
    }
    out, errors, warnings = validate_etf_enriched(source, universe_classes, strict=True)
    assert errors == []
    assert warnings == []
    assert out["etfs"]["SPY"]["compositionAvailable"] is True
    assert out["etfs"]["ESGV"]["compositionAvailable"] is True
    # FNB hors des 15 FNB clés -> marqué « composition non disponible »
    assert out["etfs"]["XLK"]["compositionAvailable"] is False
    assert out["etfs"]["XLK"]["status"] == "composition non disponible"
    # Les actions ne figurent pas dans etf_enriched
    assert "RY.TO" not in out["etfs"]


def test_validate_etf_enriched_catches_bad_weights_missing_dates_and_equities() -> None:
    """Vérifie le rejet si la somme des poids != ~100, si asOfDate/sourceUrl manque, ou si une action est présente."""
    bad_spy = _make_valid_etf_entry("SPY")
    # Somme des poids sectoriels = 50 % (loin de 100 %)
    bad_spy["sectorWeights"]["items"] = [{"sector": "Tech", "weight": 50.0}]
    # Date absente sur merPct
    bad_spy["merPct"]["asOfDate"] = ""
    # Seulement 2 holdings au lieu de 5 à 10
    bad_spy["topHoldings"]["items"] = [
        {"ticker": "AAPL", "name": "Apple", "weight": 7.0},
        {"ticker": "MSFT", "name": "Microsoft", "weight": 6.0},
    ]

    bad_esgv = _make_valid_etf_entry("ESGV", is_esgv=False)  # exclusions manquant pour ESGV

    source = {
        "schemaVersion": "1.0",
        "etfs": {
            "SPY": bad_spy,
            "ESGV": bad_esgv,
            "AAPL": _make_valid_etf_entry("AAPL"),
        },
    }
    universe_classes = {"SPY": "etf_equity", "ESGV": "etf_equity", "AAPL": "equity"}
    _, errors, _ = validate_etf_enriched(source, universe_classes, strict=True)

    joined = "\n".join(errors)
    assert "SPY.sectorWeights: sum of weights is 50.00%" in joined
    assert "SPY.merPct: missing or invalid asOfDate" in joined
    assert "SPY.topHoldings: expected 5 to 10 holdings" in joined
    assert "ESGV.exclusions: required for ESGV" in joined
    assert "AAPL: equities are forbidden in etf_enriched" in joined


# ==========================================================================
# 5. Tests du contrôle qualité et de l'anomalie CNQ.TO du 2022-08-22
# ==========================================================================


def test_cnq_2022_08_22_anomaly_isolated() -> None:
    """Vérifie l'isolation du split 1.021 de CNQ.TO le 2022-08-22 le jour du dividende de 0.75 CAD."""
    actions = pd.read_csv(FIXTURES_DIR / "corporate_actions.csv")
    enriched, isolated = isolate_cnq_anomaly_and_check_actions(actions)

    assert len(isolated) == 1
    anom = isolated[0]
    assert anom["ticker"] == "CNQ.TO"
    assert anom["exDate"] == "2022-08-22"
    assert anom["action"] == "split"
    assert anom["value"] == pytest.approx(1.021)
    assert anom["coincidentDividend"] == pytest.approx(0.75)

    flagged = enriched[enriched["anomaly_note"].notna()]
    assert len(flagged) == 1
    assert flagged.iloc[0]["ticker"] == "CNQ.TO"
    assert flagged.iloc[0]["ex_date"] == "2022-08-22"


# ==========================================================================
# 6. Test de bout en bout du mode hors ligne sur data/fixtures/
# ==========================================================================


def test_build_dataset_offline_on_fixtures(tmp_path: Path) -> None:
    """Exécute build_dataset en mode hors ligne sur data/fixtures/ et vérifie tous les fichiers Parquet/JSON."""
    manifest = build_dataset(
        mode="offline",
        starter_dir=FIXTURES_DIR,
        etf_source_json=DEFAULT_ETF_SOURCE_JSON,
        output_root=tmp_path,
        version="2022-09-30-test",
        start_date="2022-07-01",
        end_date="2022-09-30",
        min_history_rows=50,
    )

    out_dir = tmp_path / "2022-09-30-test"
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "universe.parquet").exists()
    assert (out_dir / "fx" / "usdcad.parquet").exists()
    assert (out_dir / "macro" / "macro.parquet").exists()
    assert (out_dir / "corporate_actions.parquet").exists()
    assert (out_dir / "etf_enriched.json").exists()
    assert (out_dir / "prices_all" / "year=2022" / "part-0.parquet").exists()

    for t in ("RY.TO", "CNQ.TO", "SPY"):
        assert (out_dir / "prices" / f"{t}.parquet").exists()

    # Vérifier le nommage snake_case dans universe.parquet
    u_df = pd.read_parquet(out_dir / "universe.parquet")
    expected_u_cols = {
        "asset_id",
        "ticker",
        "name",
        "asset_class",
        "market",
        "currency",
        "sector",
        "sector_source",
        "first_date",
        "last_date",
        "return_1y",
        "volatility_1y",
        "max_drawdown_1y",
    }
    assert set(u_df.columns) == expected_u_cols
    assert len(u_df) == 3

    # Vérifier macro.parquet (snake_case + publication_date)
    m_df = pd.read_parquet(out_dir / "macro" / "macro.parquet")
    assert "publication_date" in m_df.columns

    # Vérifier manifest.json (camelCase)
    assert manifest["counts"]["retainedCount"] == 3
    assert manifest["counts"]["excludedCount"] == 0
    assert "firstDateByTicker" in manifest
    assert "publicationDateRule" in manifest
    assert len(manifest["qualityReport"]["isolatedAnomalies"]) == 1


@pytest.mark.skipif(not DEFAULT_STARTER_DIR.exists(), reason="Starter dataset directory absent")
def test_build_dataset_offline_on_starter_pack(tmp_path: Path) -> None:
    """Vérifie que le mode hors ligne produit un jeu complet à partir du seul jeu fourni (31 actifs)."""
    manifest = build_dataset(
        mode="offline",
        starter_dir=DEFAULT_STARTER_DIR,
        etf_source_json=DEFAULT_ETF_SOURCE_JSON,
        output_root=tmp_path,
        version="2026-11-13-starter",
    )
    assert manifest["counts"]["retainedCount"] == 31
    assert manifest["counts"]["excludedCount"] == 0
    assert manifest["period"]["actualStart"] == "2021-11-12"
    assert manifest["period"]["actualEnd"] == "2026-11-12"

    out_dir = tmp_path / "2026-11-13-starter"
    u_df = pd.read_parquet(out_dir / "universe.parquet")
    assert len(u_df) == 31
    assert u_df["return_1y"].notna().all()
    assert u_df["volatility_1y"].notna().all()
    assert u_df["max_drawdown_1y"].notna().all()
    # Vérifier que ZST.TO (ligne à volume nul le 2022-07-06) et CNQ.TO (2022-08-22) sont signalés
    assert manifest["qualityReport"]["zeroVolumeRowsCount"] >= 1
    assert len(manifest["qualityReport"]["isolatedAnomalies"]) == 1

