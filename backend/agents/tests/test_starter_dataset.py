"""Scénario vedette sur le VRAI jeu de départ (optionnel : hors git, conditions Yahoo).

Ignoré sauf si ALPHAFORGE_STARTER_DIR pointe vers mes_docs_perso/Datathon2026/alphaforge_starter.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.agents.data.store import DataStore
from backend.agents.engine.registry import EvidenceRegistry
from backend.agents.engine.scenarios import run_engine
from backend.agents.rules import rules
from backend.agents.scripts.starter_to_dataset import convert
from backend.agents.tests.conftest import robert_holdings, robert_mandate
from backend.common.mandates import evaluate_mandate

STARTER = os.environ.get("ALPHAFORGE_STARTER_DIR")
pytestmark = pytest.mark.skipif(not STARTER, reason="ALPHAFORGE_STARTER_DIR non défini (jeu de départ hors git)")


def test_robert_nvda_sur_le_jeu_de_depart(tmp_path, capsys):
    convert(Path(STARTER), tmp_path)
    store = DataStore(str(tmp_path), "starter")
    mandate = robert_mandate(compareCategory="short-term-bonds")
    item = {"mandate": mandate, **evaluate_mandate(mandate)}
    result = run_engine(store, item, {"holdings": robert_holdings(store), "baseCurrency": "CAD"}, EvidenceRegistry("en"))
    verdicts = rules.check_rules(store, item, result)
    by_scenario = rules.scenario_verdicts(verdicts)
    with capsys.disabled():
        for s in result.scenarios:
            print(f"\nscenario {s.index}: {by_scenario[s.index]}", {k: round(v, 1) for k, v in s.metrics.items()},
                  {k: round(v, 1) for k, v in s.stress.items()}, s.concentration.get("topSingle"), s.notes)
            print("   ", [(v["rule"], v["status"]) for v in verdicts if v.get("scenario") == s.index])
    assert by_scenario[1] == "fail"
    assert by_scenario[2] != "fail"
