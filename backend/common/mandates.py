"""Logique déterministe du mandat, partagée par les deux Lambdas (sans LLM).

- POST /mandates (backend/api) confirme un mandat avec ces fonctions ;
- l'outil propose_mandate (backend/agents) valide un brouillon avec les mêmes,
  pour que le brouillon montré à l'utilisateur et le mandat confirmé aient les
  mêmes riskProfile, effectiveMaxLossPct et warnings.

Il n'existe qu'une copie des seuils par horizon : mandate_defaults.json
(hypothèse d'équipe, R2), surchargeable par RULES_CONFIG_PATH.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.common import config
from backend.common.validation import MANDATE_FIELDS

_DEFAULTS_FILE = Path(__file__).with_name("mandate_defaults.json")

_PROJECT_YEARS_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?|ans?|an)\b", re.IGNORECASE
)

_COMPARED_MANDATE_FIELDS = tuple(
    field for field in MANDATE_FIELDS if field != "fieldSources"
)


@lru_cache(maxsize=1)
def _embedded_defaults() -> dict[str, Any]:
    with _DEFAULTS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_defaults() -> dict[str, Any]:
    custom_path = config.rules_config_path()
    if custom_path:
        path = Path(custom_path)
        if path.is_file():
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict) and "maxAcceptableLossPctByHorizon" in data:
                return data
    return _embedded_defaults()


def default_max_loss_pct(horizon_years: int | float) -> int | float:
    """Retourne le plafond de perte par défaut selon l'horizon (hypothèse d'équipe, R2)."""
    tiers = _load_defaults().get("maxAcceptableLossPctByHorizon") or []
    for tier in tiers:
        if "maxHorizonYearsExclusive" in tier and horizon_years < tier["maxHorizonYearsExclusive"]:
            return tier["maxAcceptableLossPct"]
        if "maxHorizonYearsInclusive" in tier and horizon_years <= tier["maxHorizonYearsInclusive"]:
            return tier["maxAcceptableLossPct"]
        if "defaultMaxAcceptableLossPct" in tier:
            return tier["defaultMaxAcceptableLossPct"]
    if horizon_years < 3:
        return 10
    if horizon_years <= 8:
        return 20
    return 35


def _extract_project_years(detail: str | None) -> float | None:
    if not detail:
        return None
    match = _PROJECT_YEARS_RE.search(detail)
    if not match:
        return None
    return float(match.group(1))


def _warning(code: str, message: str, **params: Any) -> dict[str, Any]:
    """Avertissement stable : `code` sert au front pour traduire, `message` reste en anglais (language_policy)."""
    warning: dict[str, Any] = {"code": code, "message": message}
    if params:
        warning["params"] = params
    return warning


def compute_warnings(
    mandate: dict[str, Any],
    effective_max_loss_pct: int | float,
    default_loss_pct: int | float,
) -> list[dict[str, Any]]:
    """Contrôle de cohérence déterministe du mandat (schema-mandate-warning).

    Codes : HORIZON_EXCEEDS_PROJECT, HORIZON_LONG_FOR_PROJECT, SHORT_HORIZON_GROWTH,
    PRESERVATION_VS_HIGH_RISK, RETIREMENT_SHORT_HORIZON_HIGH_RISK, LOSS_EXCEEDS_DEFAULT.
    """
    warnings: list[dict[str, Any]] = []
    objective = mandate["objective"]
    horizon = float(mandate["horizonYears"])
    risk_tolerance = int(mandate["riskTolerance"])

    if objective == "project":
        project_years = _extract_project_years(mandate.get("objectiveDetail"))
        if project_years is not None and horizon > project_years:
            warnings.append(_warning(
                "HORIZON_EXCEEDS_PROJECT",
                f"Horizon ({mandate['horizonYears']} years) exceeds the project timeline ({project_years:g} years).",
                horizonYears=mandate["horizonYears"], projectYears=project_years,
            ))
        elif horizon > 8:
            warnings.append(_warning(
                "HORIZON_LONG_FOR_PROJECT",
                "Horizon exceeds 8 years, which is unusually long for a specific project objective.",
                horizonYears=mandate["horizonYears"],
            ))

    if objective == "growth" and horizon < 3:
        warnings.append(_warning(
            "SHORT_HORIZON_GROWTH",
            "Short horizon (< 3 years) conflicts with a long-term growth objective.",
            horizonYears=mandate["horizonYears"],
        ))

    if objective == "preservation" and (
        risk_tolerance >= 4 or effective_max_loss_pct > 20
    ):
        warnings.append(_warning(
            "PRESERVATION_VS_HIGH_RISK",
            "Capital preservation objective conflicts with high risk tolerance or maximum acceptable loss.",
            riskTolerance=risk_tolerance, maxAcceptableLossPct=effective_max_loss_pct,
        ))

    if objective == "retirement" and horizon < 3 and risk_tolerance >= 4:
        warnings.append(_warning(
            "RETIREMENT_SHORT_HORIZON_HIGH_RISK",
            "Near-term retirement horizon (< 3 years) conflicts with high risk tolerance.",
            horizonYears=mandate["horizonYears"], riskTolerance=risk_tolerance,
        ))

    if (
        "maxAcceptableLossPct" in mandate
        and mandate["maxAcceptableLossPct"] > default_loss_pct
    ):
        warnings.append(_warning(
            "LOSS_EXCEEDS_DEFAULT",
            f"Maximum acceptable loss ({mandate['maxAcceptableLossPct']}%) exceeds the team assumption default ({default_loss_pct}%) for this horizon.",
            maxAcceptableLossPct=mandate["maxAcceptableLossPct"], defaultLossPct=default_loss_pct,
        ))

    return warnings


def compute_changed_fields(
    current: dict[str, Any], previous: dict[str, Any] | None
) -> list[str]:
    """Liste ordonnée des champs modifiés depuis la version précédente du mandat."""
    if previous is None:
        return []
    prev_mandate = (
        previous.get("mandate")
        if isinstance(previous.get("mandate"), dict)
        else previous
    )
    changed = [
        field
        for field in _COMPARED_MANDATE_FIELDS
        if current.get(field) != prev_mandate.get(field)
    ]
    if not changed and current.get("fieldSources") != prev_mandate.get("fieldSources"):
        changed.append("fieldSources")
    return changed


def evaluate_mandate(mandate: dict[str, Any]) -> dict[str, Any]:
    """Champs dérivés d'un mandat déjà validé : riskProfile (R1), effectiveMaxLossPct, warnings."""
    risk_profile = min(mandate["riskTolerance"], mandate["riskCapacity"])
    default_loss = default_max_loss_pct(mandate["horizonYears"])
    effective = mandate.get("maxAcceptableLossPct", default_loss)
    return {
        "riskProfile": risk_profile,
        "effectiveMaxLossPct": effective,
        "warnings": compute_warnings(mandate, effective, default_loss),
    }
