"""module-engine sur le jeu synthétique : conversion, calendriers, stress, concentration, scénarios."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.agents.engine import analytics as an
from backend.agents.engine.concentration import concentration
from backend.agents.engine.registry import EvidenceRegistry, format_number
from backend.agents.engine.scenarios import apply_operations, choose_category, run_engine
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


def test_alternative_par_categorie_compatible_avec_le_profil(store):
    start, end = store.last_date() - pd.DateOffset(years=5), store.last_date()
    assert choose_category(store, 1, start, end) == ("Canadian short-term bonds", "ZST.TO")


def test_scenarios_robert_et_registre(store):
    registry = EvidenceRegistry("fr")
    holdings = robert_holdings(store)
    result = run_engine(store, _mandate_item(), {"holdings": holdings, "baseCurrency": "CAD"}, registry)
    assert [s.index for s in result.scenarios] == [0, 1, 2]
    s0, s1, s2 = result.scenarios
    assert sum(s0.positions_cad.values()) == pytest.approx(sum(ROBERT_AMOUNTS.values()), rel=1e-6)
    assert s1.positions_cad["NVDA"] == pytest.approx(15000)
    assert "NVDA" not in s2.positions_cad and s2.positions_cad["ZST.TO"] == pytest.approx(30000)
    assert "approximated by ZST.TO" in s2.proxy_note and "ZST.TO" not in s2.description
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
