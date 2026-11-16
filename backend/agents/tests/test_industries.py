"""La liste d'industries du front (recherche bilingue) doit être celle des candidats de l'optimiseur."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from backend.agents.engine import optimizer

ROOT = Path(__file__).resolve().parents[3]
FRONT_FILE = ROOT / "frontend" / "src" / "lib" / "industries.json"
UNIVERSE = Path(os.environ.get("ALPHAFORGE_UNIVERSE", ROOT / "data" / "output" / "2026-11-15" / "universe.parquet"))


def _rows() -> list[dict[str, str]]:
    return json.loads(FRONT_FILE.read_text(encoding="utf-8"))


def test_liste_front_bien_formee():
    rows = _rows()
    names = [r["en"] for r in rows]
    assert len(names) == len(set(names))
    assert all(r["fr"].strip() for r in rows)


@pytest.mark.skipif(not UNIVERSE.exists(), reason="universe.parquet du jeu déployé absent (ignoré par git)")
def test_liste_front_egale_industries_des_candidats_de_l_optimiseur():
    universe = pd.read_parquet(UNIVERSE)
    candidates = optimizer.candidate_universe(universe, optimizer.load_config())
    assert {r["en"] for r in _rows()} == set(candidates["industry"])
    assert len(_rows()) == 101
