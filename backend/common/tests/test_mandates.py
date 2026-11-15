"""Logique partagée du mandat (backend/common/mandates.py)."""

from backend.common import mandates


def _mandate(**overrides):
    base = {
        "portfolioId": "main",
        "mode": "add_asset",
        "objective": "project",
        "objectiveDetail": "condo purchase in 3 years",
        "horizonYears": 3,
        "riskTolerance": 3,
        "riskCapacity": 1,
        "province": "QC",
        "userLanguage": "fr",
    }
    base.update(overrides)
    return base


def test_evaluate_mandate_profil_retenu_et_plafond_par_horizon():
    derived = mandates.evaluate_mandate(_mandate())
    assert derived == {"riskProfile": 1, "effectiveMaxLossPct": 20, "warnings": []}


def test_evaluate_mandate_garde_la_perte_saisie_et_avertit_si_au_dessus_du_defaut():
    derived = mandates.evaluate_mandate(_mandate(horizonYears=2, maxAcceptableLossPct=15))
    assert derived["effectiveMaxLossPct"] == 15
    assert any(w["code"] == "LOSS_EXCEEDS_DEFAULT" and "team assumption default (10%)" in w["message"] for w in derived["warnings"])
    loss = next(w for w in derived["warnings"] if w["code"] == "LOSS_EXCEEDS_DEFAULT")
    assert loss["params"] == {"maxAcceptableLossPct": 15, "defaultLossPct": 10}


def test_defaults_lus_depuis_le_fichier_partage(monkeypatch):
    monkeypatch.delenv("RULES_CONFIG_PATH", raising=False)
    assert [mandates.default_max_loss_pct(h) for h in (1, 3, 8, 9)] == [10, 20, 20, 35]
