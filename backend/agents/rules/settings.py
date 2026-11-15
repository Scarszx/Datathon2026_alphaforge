"""Seuils d'hypothèse d'équipe (rules_config.json), surchargeables par RULES_CONFIG_PATH.

RULES_CONFIG_PATH est partagé avec la Lambda API (plafonds de perte par horizon,
backend/common/mandate_defaults.json) : chaque module ne lit que ses propres clés,
et une clé absente du fichier surchargé garde sa valeur embarquée.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.common import config

_EMBEDDED = Path(__file__).with_name("rules_config.json")


@lru_cache(maxsize=1)
def _embedded() -> dict[str, Any]:
    return json.loads(_EMBEDDED.read_text(encoding="utf-8"))


def settings() -> dict[str, Any]:
    merged = dict(_embedded())
    custom = config.rules_config_path()
    if custom and Path(custom).is_file():
        try:
            override = json.loads(Path(custom).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            override = {}
        if isinstance(override, dict):
            merged.update({k: v for k, v in override.items() if k in merged})
    return merged


def risk_band(volatility_pct: float) -> int:
    """Profil de risque (1-5) qu'implique une volatilité annualisée (hypothèse d'équipe)."""
    for tier in settings()["riskBandsByVolatility"]:
        limit = tier.get("maxVolatilityPct")
        if limit is None or volatility_pct <= limit:
            return int(tier["band"])
    return 5
