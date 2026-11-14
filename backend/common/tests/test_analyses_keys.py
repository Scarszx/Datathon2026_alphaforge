"""Tests WS0b du module analyses : clés de tri et signatures posées pour WS2b.

L'implémentation (et ses tests moto) relève de WS2b : test_repo_analyses.py.
"""

import inspect

import pytest

from backend.common.repositories import analyses


def test_cles_de_tri():
    assert analyses.mandate_item_key(1) == "MANDATE#001"
    assert analyses.mandate_item_key(12) == "MANDATE#012"
    assert analyses.run_item_key("01JABCDEF") == "RUN#01JABCDEF"
    # l'ordre lexicographique suit l'ordre des versions
    assert analyses.mandate_item_key(2) < analyses.mandate_item_key(10)


SIGNATURES = {
    "put_mandate": ["session_id", "user_id", "mandate"],
    "get_mandate": ["session_id", "user_id", "version"],
    "get_latest_mandate": ["session_id", "user_id"],
    "list_mandates": ["session_id", "user_id"],
    "put_run": ["session_id", "user_id", "run"],
    "update_run": ["session_id", "user_id", "run_id", "fields"],
    "get_run": ["session_id", "user_id", "run_id"],
    "delete_analyses": ["session_id", "user_id"],
}


@pytest.mark.parametrize("nom,parametres", SIGNATURES.items())
def test_signatures_figees(nom, parametres):
    """Les signatures sont le contrat entre WS0b, WS2b, WS4b et WS5."""
    fonction = getattr(analyses, nom)
    assert list(inspect.signature(fonction).parameters) == parametres
    assert fonction.__doc__
