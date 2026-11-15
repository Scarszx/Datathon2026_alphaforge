"""module-engine sur le jeu synthétique : conversion, calendriers, stress, concentration, scénarios."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.agents.engine import analytics as an
from backend.agents.engine.concentration import concentration
from backend.agents.engine.registry import EvidenceRegistry, format_number
from backend.agents.engine.scenarios import apply_operations, comparison_operations, resolve_comparison, run_engine
from backend.agents.engine.stress import derive_period
from backend.agents.tests.conftest import ROBERT_AMOUNTS, robert_holdings, robert_mandate
from backend.common.mandates import evaluate_mandate


def _mandate_item(**overrides):
    mandate = robert_mandate(**overrides)
    return {"mandate": mandate, **evaluate_mandate(mandate)}


def test_conversion_en_cad_avec_report_du_dernier_taux(store):
    usd = an.native_series(store, "SPY")
    cad = an.to_cad(store, "SPY", usd)
    fx = store.fx_usdcad()
    # 4 juillet absent du calendrier US, fête du Canada absente du taux : le taux précédent est reporté.
    day = pd.Timestamp("2023-07-03")
    assert cad[day] == pytest.approx(usd[day] * fx[fx.index <= day].iloc[-1])
    assert an.to_cad(store, "RY.TO", an.native_series(store, "RY.TO")).equals(an.native_series(store, "RY.TO"))


def test_annualisation_252_ou_365_selon_la_classe(store):
    assert an.periods_per_year("BTC-USD", "crypto") == 365
    assert an.periods_per_year("SPY", "etf_equity") == 252
    metrics = an.asset_metrics(store, "BTC-USD", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31"))
    assert metrics["periods"] == 365


def test_intersection_des_jours_de_cotation(store):
    aligned = an.aligned_cad_prices(store, ["RY.TO", "SPY", "BTC-USD"], pd.Timestamp("2023-06-25"), pd.Timestamp("2023-07-10"))
    days = set(aligned.frame.index.strftime("%m-%d"))
    assert "07-01" not in days and "07-04" not in days  # ni fête du Canada ni 4 juillet
    assert not aligned.frame.isna().any().any()


def test_periodes_de_stress_derivees_des_donnees(store):
    y2022 = derive_period(store, "y2022")
    assert (y2022.start.year, y2022.end.year) == (2022, 2022)
    covid = derive_period(store, "covid_2020")
    assert covid.start < covid.end and covid.start.year == 2020
    hikes = derive_period(store, "rate_hikes")
    assert hikes.start == pd.Timestamp("2022-03-02") and hikes.end == pd.Timestamp("2023-07-12")
    crash = derive_period(store, "crypto_crash")
    assert crash.available and crash.start < crash.end


def test_periode_non_calculable_n_est_jamais_inventee(store, monkeypatch):
    monkeypatch.setattr(store, "has_ticker", lambda t: t != "SPY")
    covid = derive_period(store, "covid_2020")
    assert covid.available is False and covid.note


def test_concentration_avec_composition_des_fnb(store):
    result = concentration(store, {"XIU.TO": 50, "RY.TO": 50})
    # RY.TO direct 50 % + 7 % de XIU.TO (fiche synthétique) × 50 %.
    assert result["topSingle"] == {"ticker": "RY.TO", "weight": 53.5}
    assert result["lookThroughComplete"] is True
    unknown = concentration(store, {"AGG": 100})
    assert unknown["lookThroughComplete"] is False and "AGG" in unknown["caveats"][0]


def test_fiche_de_fnb_vide_n_est_pas_une_composition(store, monkeypatch):
    """Un gabarit non rempli (listes vides, sans source) ne doit pas faire croire à une transparence."""
    empty = {"ticker": "XIU.TO", "sectorWeights": {}, "countryWeights": {}, "topHoldings": []}
    monkeypatch.setattr(store, "etf_enriched", lambda: {"XIU.TO": empty})
    result = concentration(store, {"XIU.TO": 50, "RY.TO": 50})
    assert result["lookThroughComplete"] is False
    assert "XIU.TO" in result["caveats"][0] and "look-through incomplete" in result["caveats"][0]
    assert result["topSingle"]["ticker"] == "RY.TO" and result["topSingle"]["weight"] == 50.0  # aucune position de fonds ajoutée


def test_concentration_tech_par_transparence(store):
    result = concentration(store, {"SPY": 50, "NVDA": 50})
    assert result["techLookThrough"] == pytest.approx(50 + 50 * 0.32)
    assert result["topSingle"]["ticker"] == "NVDA"


def test_operations_add_remove_set_weight(store):
    as_of = store.last_date()
    base = {"RY.TO": 100.0, "XBB.TO": 100.0}
    added = apply_operations(store, base, [{"action": "add", "ticker": "NVDA", "amount": 50, "currency": "CAD"}], as_of, "CAD")
    assert added["NVDA"] == 50
    removed = apply_operations(store, base, [{"action": "remove", "ticker": "RY.TO"}], as_of, "CAD")
    assert "RY.TO" not in removed
    weighted = apply_operations(store, base, [{"action": "set_weight", "ticker": "SPY", "weight": 50}], as_of, "CAD")
    assert weighted["SPY"] == pytest.approx(100) and sum(weighted.values()) == pytest.approx(200)


def test_categorie_choisie_et_fnb_d_approximation(store):
    start, end = store.last_date() - pd.DateOffset(years=5), store.last_date()
    comparison = resolve_comparison(store, "short-term-bonds", start, end)
    assert (comparison.label, comparison.proxy) == ("Canadian short-term bonds", "ZST.TO") and 1 <= comparison.band <= 5
    assert resolve_comparison(store, "inconnue", start, end) is None and resolve_comparison(store, None, start, end) is None


def test_comparaison_remplace_chaque_titre_ajoute_sans_le_juger(store):
    start, end = store.last_date() - pd.DateOffset(years=5), store.last_date()
    comparison = resolve_comparison(store, "short-term-bonds", start, end)
    mandate = robert_mandate(operations=[
        {"action": "add", "ticker": "RY.TO", "amount": 1000, "currency": "CAD"},  # titre peu volatil : remplacé quand même
        {"action": "add", "ticker": "NVDA", "amount": 2000, "currency": "CAD"},
        {"action": "set_weight", "ticker": "SPY", "weight": 5},
        {"action": "set_weight", "ticker": "AAPL", "weight": 7},
        {"action": "remove", "ticker": "TD.TO"},
    ])
    ops = comparison_operations(mandate, comparison)
    assert [o["ticker"] for o in ops if o["action"] == "add"] == ["ZST.TO", "ZST.TO"]
    assert [o["amount"] for o in ops if o["action"] == "add"] == [1000, 2000]
    weights = [o for o in ops if o["action"] == "set_weight"]
    assert len(weights) == 1 and weights[0]["weight"] == 12 and weights[0]["ticker"] == "ZST.TO"  # cumulés, non écrasés
    assert any(o["action"] == "remove" and o["ticker"] == "TD.TO" for o in ops)
    assert comparison_operations(robert_mandate(operations=[{"action": "remove", "ticker": "RY.TO"}]), comparison) is None


def test_pas_de_scenario_2_sans_demande(store):
    result = run_engine(store, _mandate_item(), {"holdings": robert_holdings(store), "baseCurrency": "CAD"}, EvidenceRegistry("fr"))
    assert [s.index for s in result.scenarios] == [0, 1] and result.compare_requested is False
    assert not any("category" in (item.get("label") or "") for item in result.registry.items)


def test_scenarios_robert_et_registre(store):
    registry = EvidenceRegistry("fr")
    holdings = robert_holdings(store)
    result = run_engine(store, _mandate_item(compareCategory="short-term-bonds"), {"holdings": holdings, "baseCurrency": "CAD"}, registry)
    assert [s.index for s in result.scenarios] == [0, 1, 2] and result.compare_requested is True
    s0, s1, s2 = result.scenarios
    assert sum(s0.positions_cad.values()) == pytest.approx(sum(ROBERT_AMOUNTS.values()), rel=1e-6)
    assert s1.positions_cad["NVDA"] == pytest.approx(15000)
    assert "NVDA" not in s2.positions_cad and s2.positions_cad["ZST.TO"] == pytest.approx(30000)
    assert "ZST.TO" not in s2.proxy_note and "ZST.TO" not in s2.description and "ZST.TO" not in s2.label
    for scenario in result.scenarios:
        for key in ("volatility", "maxDrawdown", "stress2022", "topSingleWeight", "techWeightLookThrough"):
            assert registry.get(scenario.evidence[key])["scenario"] == scenario.index
    ids = [item["id"] for item in registry.items]
    assert len(ids) == len(set(ids)) and all(i.startswith("EV-") for i in ids)
    vol = registry.get(s1.evidence["volatility"])
    assert vol["currency"] == "CAD" and vol["window"] and vol["caveats"] and "sqrt(252)" in vol["method"]
    assert s1.metrics["volatility"] > s0.metrics["volatility"] > s2.metrics["volatility"]


def test_format_selon_la_langue():
    assert format_number(15.24, "%", "fr") == "15,2 %"
    assert format_number(15.24, "%", "en") == "15.2%"
    assert format_number(15000, "CAD", "fr") == "15 000 $"


def test_hausse_isolee_ne_forme_pas_un_cycle(store, monkeypatch):
    """Cas réel du jeu de départ : une hausse isolée en fin de série après un cycle de baisses."""
    days = pd.to_datetime(["2022-01-03", "2022-03-02", "2022-04-13", "2022-06-01", "2024-06-05", "2026-10-29"])
    rates = [0.25, 0.50, 1.00, 1.50, 1.25, 1.50]
    macro = pd.DataFrame({"date": days, "series_id": "V39079", "value": rates})
    monkeypatch.setattr(store, "macro", lambda: macro)
    period = derive_period(store, "rate_hikes")
    assert (period.start, period.end) == (pd.Timestamp("2022-03-02"), pd.Timestamp("2022-06-01"))
