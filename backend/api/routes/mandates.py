"""Routes /conversations/{sessionId}/mandates (api-mandates-create, api-mandates-list).

Confirme ou met à jour un mandat (proposé par l'orchestrateur ou modifié via les
curseurs « et si ») sans aucun appel de modèle :
- calcule riskProfile = min(riskTolerance, riskCapacity) (règle R1) ;
- calcule effectiveMaxLossPct à partir de la valeur saisie ou du seuil par
  horizon (hypothèse d'équipe, backend/common/mandate_defaults.json) ;
- applique le contrôle de cohérence déterministe (warnings) ;
- calcule changedFields par rapport à la version précédente de la session.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from backend.api.validation import (
    parse_json_body,
    session_id,
    validate_mandate_create,
)
from backend.common.http import ApiError, json_response
from backend.common.mandates import (  # noqa: F401  (réexportés pour les tests existants)
    compute_changed_fields,
    compute_warnings,
    default_max_loss_pct,
    evaluate_mandate,
)
from backend.common.repositories import analyses as analyses_repo
from backend.common.repositories import conversations as conversations_repo


def _not_found() -> ApiError:
    """Nouvelle erreur à chaque appel : ne pas partager le requestId."""
    return ApiError("CONVERSATION_NOT_FOUND", "Conversation inconnue.")


def _ensure_owner(user_id: str, session_id_value: str) -> None:
    if conversations_repo.get_conversation(user_id, session_id_value) is None:
        raise _not_found()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

    derived = evaluate_mandate(mandate)

    previous = analyses_repo.get_latest_mandate(session_id_value, user_id)
    changed_fields = compute_changed_fields(mandate, previous)

    saved = analyses_repo.put_mandate(
        session_id_value,
        user_id,
        {
            "mandate": mandate,
            "riskProfile": derived["riskProfile"],
            "effectiveMaxLossPct": derived["effectiveMaxLossPct"],
            "warnings": derived["warnings"],
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
