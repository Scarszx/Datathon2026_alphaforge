"""Table fixe française : tous les textes connus d'avance sont traduits, sans formulation interdite."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from backend.agents.rules import fr, rules
from backend.agents.rules.settings import settings
from backend.agents.verifier.verifier import PLACEHOLDER_RE, forbidden_phrases


def _default_messages() -> set[str]:
    """Chaque phrase anglaise passée à `_verdict` ou assignée à `message` dans rules.py (hors docstrings et suffixe R6)."""
    tree = ast.parse(Path(rules.__file__).read_text(encoding="utf-8"))
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef)) and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)}
    found = {
        n.value.strip() for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
        and n.value.rstrip().endswith(".") and len(n.value.split()) >= 5
        and n.value.isascii() and not n.value.startswith("Daily")  # RULE_TOPICS et phrases internes sans point final
    }
    found.discard(fr.LOOK_THROUGH_SUFFIX_EN.strip())
    return found


def test_chaque_motif_par_defaut_a_sa_version_francaise():
    missing = sorted(m for m in _default_messages() if fr.fixed_message(m) is None)
    assert missing == []


def test_aucune_entree_orpheline_dans_la_table():
    assert set(fr.MESSAGES_FR) <= _default_messages()


def test_le_suffixe_de_transparence_est_traduit():
    base = "A single security, including through fund holdings, carries a large share of the portfolio."
    assert fr.fixed_message(base + fr.LOOK_THROUGH_SUFFIX_EN) == fr.MESSAGES_FR[base] + fr.LOOK_THROUGH_SUFFIX_FR


def test_chaque_mention_de_la_configuration_a_sa_version_francaise():
    conf = json.loads((Path(rules.__file__).with_name("rules_config.json")).read_text(encoding="utf-8"))
    english = [conf["baseNotice"], *conf["provinceNotices"].values()]
    assert [e for e in english if fr.fixed_notice(e) is None] == []
    assert set(fr.NOTICES_FR) == set(english)
    assert settings()["baseNotice"] in fr.NOTICES_FR


def test_la_table_garde_les_memes_emplacements_et_aucune_approbation():
    for english, french in {**fr.MESSAGES_FR}.items():
        assert PLACEHOLDER_RE.findall(english) == PLACEHOLDER_RE.findall(french)
        assert forbidden_phrases(french) == [], french


def test_les_mentions_de_province_nomment_le_titre_reserve():
    # Légitime dans une mention : ce texte ne passe pas par les contrôles du vérificateur.
    qc = next(v for k, v in fr.NOTICES_FR.items() if k.startswith("In Québec"))
    assert "planificateur financier" in qc and forbidden_phrases(qc)
