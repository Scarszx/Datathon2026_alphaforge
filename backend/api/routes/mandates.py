"""Routes /conversations/{sessionId}/mandates (api-mandates-create, api-mandates-list).

Confirme ou met à jour un mandat (proposé par l'orchestrateur ou modifié via les
curseurs « et si ») sans aucun appel de modèle :
- calcule riskProfile = min(riskTolerance, riskCapacity) (règle R1) ;
- calcule effectiveMaxLossPct à partir de la valeur saisie ou du seuil par
  horizon (hypothèse d'équipe, mandate_defaults.json) ;
- applique le contrôle de cohérence déterministe (warnings) ;
- calcule changedFields par rapport à la version précédente de la session.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from importlib import resources
import json
from pathlib import Path
import re
from typing import Any, Callable

from backend.api.validation import (
    MANDATE_FIELDS,
    parse_json_body,
    session_id,
    validate_mandate_create,
)
from backend.common import config
from backend.common.http import ApiError, json_response
from backend.common.repositories import analyses as analyses_repo
from backend.common.repositories import conversations as conversations_repo

_PROJECT_YEARS_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?|ans?|an)\b", re.IGNORECASE
)

_COMPARED_MANDATE_FIELDS = tuple(
    field for field in MANDATE_FIELDS if field != "fieldSources"
)


def _not_found() -> ApiError:
    """Nouvelle erreur à chaque appel : ne pas partager le requestId."""
    return ApiError("CONVERSATION_NOT_FOUND", "Conversation inconnue.")


def _ensure_owner(user_id: str, session_id_value: str) -> None:
    if conversations_repo.get_conversation(user_id, session_id_value) is None:
        raise _not_found()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@lru_cache(maxsize=1)
def _embedded_defaults() -> dict[str, Any]:
    with resources.files("backend.api").joinpath("mandate_defaults.json").open(
        "r", encoding="utf-8"
    ) as file:
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


def compute_warnings(
    mandate: dict[str, Any],
    effective_max_loss_pct: int | float,
    default_loss_pct: int | float,
) -> list[str]:
    """Contrôle de cohérence déterministe du mandat (messages en anglais, language_policy)."""
    warnings: list[str] = []
    objective = mandate["objective"]
    horizon = float(mandate["horizonYears"])
    risk_tolerance = int(mandate["riskTolerance"])

    if objective == "project":
        project_years = _extract_project_years(mandate.get("objectiveDetail"))
        if project_years is not None and horizon > project_years:
            warnings.append(
                f"Horizon ({mandate['horizonYears']} years) exceeds the project timeline ({project_years:g} years)."
            )
        elif horizon > 8:
            warnings.append(
                "Horizon exceeds 8 years, which is unusually long for a specific project objective."
            )

    if objective == "growth" and horizon < 3:
        warnings.append(
            "Short horizon (< 3 years) conflicts with a long-term growth objective."
        )

    if objective == "preservation" and (
        risk_tolerance >= 4 or effective_max_loss_pct > 20
    ):
        warnings.append(
            "Capital preservation objective conflicts with high risk tolerance or maximum acceptable loss."
        )

    if objective == "retirement" and horizon < 3 and risk_tolerance >= 4:
        warnings.append(
            "Near-term retirement horizon (< 3 years) conflicts with high risk tolerance."
        )

    if (
        "maxAcceptableLossPct" in mandate
        and mandate["maxAcceptableLossPct"] > default_loss_pct
    ):
        warnings.append(
            f"Maximum acceptable loss ({mandate['maxAcceptableLossPct']}%) exceeds the team assumption default ({default_loss_pct}%) for this horizon."
        )

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


def _validate_mandate_tickers(
    mandate: dict[str, Any], ticker_validator: Callable[[list[str]], None]
) -> None:
    tickers: list[str] = [
        op["ticker"] for op in mandate.get("operations", [])
    ]
    if "subjectTicker" in mandate:
        tickers.append(mandate["subjectTicker"])
    if not tickers:
        return
    try:
        ticker_validator(tickers)
    except ApiError as error:
        if error.code == "ASSET_NOT_FOUND":
            raise ApiError("VALIDATION_ERROR", error.message) from error
        raise


def create_mandate(
    event: dict[str, Any],
    user_id: str,
    ticker_validator: Callable[[list[str]], None],
) -> dict[str, Any]:
    """POST /v1/conversations/{sessionId}/mandates : confirme une version de mandat."""
    session_id_value = session_id(event)
    mandate = validate_mandate_create(parse_json_body(event))
    _ensure_owner(user_id, session_id_value)
    _validate_mandate_tickers(mandate, ticker_validator)

    risk_profile = min(mandate["riskTolerance"], mandate["riskCapacity"])
    default_loss = default_max_loss_pct(mandate["horizonYears"])
    effective_max_loss_pct = mandate.get("maxAcceptableLossPct", default_loss)
    warnings = compute_warnings(mandate, effective_max_loss_pct, default_loss)

    previous = analyses_repo.get_latest_mandate(session_id_value, user_id)
    changed_fields = compute_changed_fields(mandate, previous)

    saved = analyses_repo.put_mandate(
        session_id_value,
        user_id,
        {
            "mandate": mandate,
            "riskProfile": risk_profile,
            "effectiveMaxLossPct": effective_max_loss_pct,
            "warnings": warnings,
            "changedFields": changed_fields,
            "confirmedAt": _now_iso(),
        },
    )
    return json_response(201, saved)


def list_mandates(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """GET /v1/conversations/{sessionId}/mandates : versions de la plus récente à la plus ancienne."""
    session_id_value = session_id(event)
    _ensure_owner(user_id, session_id_value)
    items = analyses_repo.list_mandates(session_id_value, user_id)
    return json_response(200, {"items": items})
