"""Catégories d'actifs de la comparaison (scénario 2), lues dans comparison_categories.json.

Un seul fichier pour la Lambda API (validation de compareCategory) et la Lambda agents (moteur).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_FILE = Path(__file__).with_name("comparison_categories.json")


@lru_cache(maxsize=1)
def categories() -> tuple[dict[str, Any], ...]:
    data = json.loads(_FILE.read_text(encoding="utf-8"))
    return tuple(sorted(data["categories"], key=lambda c: (c["level"], c["id"])))


def category_ids() -> tuple[str, ...]:
    return tuple(c["id"] for c in categories())


def get_category(category_id: str | None) -> dict[str, Any] | None:
    return next((c for c in categories() if c["id"] == category_id), None)
