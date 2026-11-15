"""module-rules : R1 à R10, avec PASS, WARN et FAIL quand c'est applicable, et le scénario vedette."""

from __future__ import annotations

import pytest

from backend.agents.engine.registry import EvidenceRegistry
from backend.agents.engine.scenarios import ScenarioAnalysis, run_engine
from backend.agents.rules import rules
from backend.agents.tests.conftest import robert_holdings, robert_mandate
from backend.common.mandates import evaluate_mandate


def _item(**overrides):
    mandate = robert_mandate(**overrides)
    return {"mandate": mandate, **evaluate_mandate(mandate)}


def _scenario(index=1, **fields):
    defaults = {"positions_cad": {"RY.TO": 1.0}, "weights": {"RY.TO": 100.0}}
    defaults.update(fields)
    return ScenarioAnalysis(index, "s", **defaults)


def _by(verdicts, rule, scenario=None):
    return next(v for v in verdicts if v["rule"] == rule and v.get("scenario") == scenario)


@pytest.mark.parametrize("band,assets,expected", [(1, [], "pass"), (2, [], "warn"), (1, [{"band": 5}], "fail")])
def test_r1(band, assets, expected):
    verdict = rules.r1(_item(), _scenario(portfolio_band=band, idea_assets=assets))
    assert verdict["status"] == expected and verdict["threshold"] == {"value": 1, "nature": "text"}


def test_r1_cite_la_volatilite_du_titre_qui_cause_le_verdict():
    """Le FAIL vient du titre ajouté (bande 5), pas du portefeuille (bande 1) : la preuve citée doit être celle du titre."""
    scenario = _scenario(portfolio_band=1, idea_assets=[{"ticker": "NVDA", "band": 5, "evidence": "EV-40"}], evidence={"volatility": "EV-16"})
    verdict = rules.r1(_item(), scenario)
    assert verdict["status"] == "fail" and verdict["reasonCode"] == "IDEA_EXCEEDS_RISK_PROFILE"
    assert verdict["evidence"] == ["EV-40", "EV-16"]


def test_r1_cite_le_portefeuille_quand_c_est_lui_qui_depasse():
    scenario = _scenario(portfolio_band=3, idea_assets=[{"ticker": "XBB.TO", "band": 1, "evidence": "EV-41"}], evidence={"volatility": "EV-16"})
    verdict = rules.r1(_item(), scenario)
    assert verdict["reasonCode"] == "PORTFOLIO_EXCEEDS_RISK_PROFILE" and verdict["evidence"] == ["EV-16"]


def test_r1_scenario_actuel_plafonne_a_warn():
    assert rules.r1(_item(), _scenario(0, portfolio_band=5))["status"] == "warn"


@pytest.mark.parametrize("drawdown,expected", [(-10.0, "pass"), (-17.0, "warn"), (-25.0, "fail")])
def test_r2_plafond_par_horizon_hypothese_d_equipe(drawdown, expected):
    verdict = rules.r2(_item(), _scenario(metrics={"maxDrawdown": drawdown}))
    assert verdict["status"] == expected
    assert verdict["threshold"] == {"value": 20, "nature": "team_assumption"}


def test_r2_perte_saisie_par_l_utilisateur_n_est_pas_une_hypothese():
    verdict = rules.r2(_item(maxAcceptableLossPct=30), _scenario(metrics={"maxDrawdown": -25.0}))
    assert verdict["status"] == "warn" and verdict["threshold"] == {"value": 30}


def test_r2_sans_mesure_est_non_verifie():
    assert rules.r2(_item(), _scenario())["status"] == "not_verified"


def test_r3():
    assert rules.r3(_scenario())["status"] == "pass"
    assert rules.r3(_scenario(positions_cad={}, weights={}))["status"] == "warn"


@pytest.mark.parametrize("weight,expected", [(8.0, "pass"), (14.0, "warn"), (25.0, "fail")])
def test_r6(weight, expected):
    verdict = rules.r6(_scenario(concentration={"topSingle": {"ticker": "RY.TO", "weight": weight}}))
    assert verdict["status"] == expected and verdict["threshold"]["nature"] == "team_assumption"


@pytest.mark.parametrize("weight,overrides,expected", [
    (0.0, {}, "pass"), (4.0, {}, "warn"), (8.0, {}, "fail"),
    (2.0, {"preferences": {"excludedAssetClasses": ["crypto"]}}, "fail"),
])
def test_r7_plafonds_crypto(weight, overrides, expected):
    verdict = rules.r7(_item(**overrides), _scenario(concentration={"cryptoWeight": weight}))
    assert verdict["status"] == expected


def test_r7_profil_eleve_plafond_10():
    item = _item(riskTolerance=5, riskCapacity=5)
    assert rules.r7(item, _scenario(concentration={"cryptoWeight": 8.0}))["status"] == "warn"


def test_r8_esg(store):
    assert rules.r8(store, _item(), _scenario())["reasonCode"] == "ESG_NOT_REQUESTED"
    esg = _item(preferences={"esg": True})
    assert rules.r8(store, esg, _scenario(weights={"ESGV": 100.0}))["status"] == "pass"
    mixed = rules.r8(store, esg, _scenario(weights={"ESGV": 50.0, "ENB.TO": 50.0}))
    assert mixed["status"] == "warn" and mixed["reasonCode"] == "ESG_NOT_VERIFIED"


def _engine(store, **overrides):
    item = _item(**overrides)
    result = run_engine(store, item, {"holdings": robert_holdings(store), "baseCurrency": "CAD"}, EvidenceRegistry("fr"))
    return item, result


def test_scenario_vedette_robert_nvda(store):
    """SOLUTION.md section 6 : le scénario 1 échoue, l'alternative par catégorie n'échoue pas."""
    item, result = _engine(store)
    verdicts = rules.check_rules(store, item, result)
    by_scenario = rules.scenario_verdicts(verdicts)
    assert by_scenario[1] == "fail"
    assert _by(verdicts, "R1", 1)["reasonCode"] == "IDEA_EXCEEDS_RISK_PROFILE"
    assert _by(verdicts, "R2", 1)["status"] == "fail"
    # Les règles que l'idée fait échouer passent dans l'alternative.
    for rule in ("R1", "R2", "R7"):
        assert _by(verdicts, rule, 2)["status"] == "pass"
    assert by_scenario[2] != "fail"
    assert _by(verdicts, "R4")["reasonCode"] == "ALTERNATIVE_PRESENTED"
    assert _by(verdicts, "R5")["status"] == "pass"
    assert all(v["citations"] == [] for v in verdicts)


def test_r6_herite_du_portefeuille_actuel(store):
    """R6 hérite de l'état actuel (jeu synthétique des tests : un titre y dépasse encore 10 %).

    Sur le jeu réel 2026-11-14, avec RY 8 000 $ et TD 9 000 $, le portefeuille vedette est sous
    10 % (scénario 0 en PASS) : R6 donne PASS / WARN / PASS et le scénario 1 reste en FAIL.
    """
    item, result = _engine(store)
    verdicts = rules.check_rules(store, item, result)
    assert [_by(verdicts, "R6", i)["status"] for i in (0, 1, 2)] == ["warn", "warn", "pass"]


def test_horizon_10_ans_change_le_verdict(store):
    """« Et si » par curseur : l'horizon passe à 10 ans, le plafond de perte passe à 35 %."""
    item, result = _engine(store, horizonYears=10, objectiveDetail="condo purchase in 10 years")
    verdicts = rules.check_rules(store, item, result)
    assert item["effectiveMaxLossPct"] == 35
    assert _by(verdicts, "R2", 1)["status"] in ("pass", "warn")


def test_r4_alternative_manquante(store):
    item, result = _engine(store)
    result.scenarios = result.scenarios[:2]
    verdicts = rules.check_rules(store, item, result)
    assert _by(verdicts, "R4")["status"] == "fail"


def test_r5_titre_nomme_dans_l_alternative(store):
    item, result = _engine(store)
    result.scenarios[2].description = "Buy ZST.TO instead."
    assert _by(rules.check_rules(store, item, result), "R5")["status"] == "fail"


def test_r9_mentions_de_la_province():
    qc = rules.jurisdiction_notices("QC")
    on = rules.jurisdiction_notices("ON")
    assert "AMF" in qc[0] and "FSRA" in on[0] and qc[1] == on[1]
    assert "regulator" in rules.jurisdiction_notices("NU")[0]


def test_r10_macro_avant_publication(store):
    item, result = _engine(store)
    assert _by(rules.check_rules(store, item, result), "R10")["status"] == "pass"
    result.macro_usage[0]["publication"] = result.macro_usage[0]["asOf"] + __import__("pandas").Timedelta(1, "D")
    assert _by(rules.check_rules(store, item, result), "R10")["status"] == "fail"


def test_messages_par_defaut_en_anglais_sans_chiffre(store):
    item, result = _engine(store)
    for verdict in rules.check_rules(store, item, result):
        assert verdict["messageEn"] and not any(ch.isdigit() for ch in verdict["messageEn"])
