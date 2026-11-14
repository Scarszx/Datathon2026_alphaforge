"""Validation des entrées de la Lambda API (payload v2).

Seuls les types, champs requis, enums et bornes explicitement écrits dans le
contrat sont vérifiés. Aucune règle supplémentaire n'est inventée : les
contraintes non prévues (longueur d'un titre, unicité des tickers, signe du
prix de revient) ne sont pas appliquées.
"""

from __future__ import annotations

import base64
import binascii
import json
import math
import uuid
from typing import Any

from backend.common.http import ApiError

# Même borne que la couche d'accès DynamoDB (backend/common/repositories).
MAX_LIMIT = 100

RISK_LEVELS = ("low", "low_moderate", "moderate", "high")


def _validation_error(message: str) -> ApiError:
    return ApiError("VALIDATION_ERROR", message)


def _reject_constant(value: str) -> None:
    """Refuse NaN et Infinity, que json.loads accepte par défaut."""
    raise ValueError(f"valeur JSON non finie : {value}")


def parse_json_body(
    event: dict[str, Any], *, required: bool = True, allow_empty: bool = False
) -> dict[str, Any]:
    """Retourne le corps JSON sous forme d'objet.

    `allow_empty=True` autorise une requête sans corps (POST /conversations,
    dont le seul champ est facultatif). Un corps requis absent est une erreur.
    """
    body = event.get("body")
    if body is None or (isinstance(body, str) and body == ""):
        if required and not allow_empty:
            raise _validation_error("Corps JSON requis.")
        return {}
    if not isinstance(body, str):
        raise _validation_error("Corps JSON invalide.")

    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeError) as exc:
            raise _validation_error("Corps JSON invalide.") from exc
        if body == "":
            if required and not allow_empty:
                raise _validation_error("Corps JSON requis.")
            return {}

    try:
        parsed = json.loads(body, parse_constant=_reject_constant)
    except (ValueError, TypeError) as exc:
        raise _validation_error("Corps JSON invalide.") from exc
    if not isinstance(parsed, dict):
        raise _validation_error("Le corps JSON doit être un objet.")
    return parsed


def _reject_unknown_fields(body: dict[str, Any], allowed: tuple[str, ...]) -> None:
    unknown = sorted(set(body) - set(allowed))
    if unknown:
        labels = ", ".join(unknown)
        raise _validation_error(f"Champ(s) non prévu(s) : {labels}.")


def _string(body: dict[str, Any], key: str, *, required: bool = True) -> str | None:
    if key not in body:
        if required:
            raise _validation_error(f"Champ requis : {key}.")
        return None
    value = body[key]
    if not isinstance(value, str):
        raise _validation_error(f"{key} doit être une chaîne.")
    return value


def _integer(body: dict[str, Any], key: str, *, required: bool = True) -> int | None:
    if key not in body:
        if required:
            raise _validation_error(f"Champ requis : {key}.")
        return None
    value = body[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise _validation_error(f"{key} doit être un entier.")
    return value


def _number(body: dict[str, Any], key: str) -> int | float:
    if key not in body:
        raise _validation_error(f"Champ requis : {key}.")
    value = body[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _validation_error(f"{key} doit être un nombre.")
    if not math.isfinite(float(value)):
        raise _validation_error(f"{key} doit être un nombre fini.")
    return value


def _array_of_strings(body: dict[str, Any], key: str) -> list[str] | None:
    if key not in body:
        return None
    value = body[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _validation_error(f"{key} doit être un tableau de chaînes.")
    return value


def validate_investor_profile(body: dict[str, Any]) -> dict[str, Any]:
    """Valide schema-investor-profile et retourne les champs autorisés."""
    _reject_unknown_fields(
        body,
        (
            "riskLevel",
            "horizonMinYears",
            "horizonMaxYears",
            "objective",
            "constraints",
            "preferences",
            "excludedAssetClasses",
        ),
    )
    risk_level = _string(body, "riskLevel")
    if risk_level not in RISK_LEVELS:
        values = ", ".join(RISK_LEVELS)
        raise _validation_error(f"riskLevel doit être l'un de : {values}.")
    horizon_min = _integer(body, "horizonMinYears")
    horizon_max = _integer(body, "horizonMaxYears", required=False)
    objective = _string(body, "objective")
    profile: dict[str, Any] = {
        "riskLevel": risk_level,
        "horizonMinYears": horizon_min,
        "objective": objective,
    }
    if horizon_max is not None:
        profile["horizonMaxYears"] = horizon_max
    for key in ("constraints", "preferences", "excludedAssetClasses"):
        value = _array_of_strings(body, key)
        if value is not None:
            profile[key] = value
    return profile


def validate_conversation_create(body: dict[str, Any]) -> str | None:
    """Valide schema-conversation-create-request (title facultatif)."""
    _reject_unknown_fields(body, ("title",))
    return _string(body, "title", required=False)


def validate_conversation_update(body: dict[str, Any]) -> str:
    """Valide schema-conversation-update-request (title requis)."""
    _reject_unknown_fields(body, ("title",))
    return _string(body, "title")  # type: ignore[return-value]


def validate_holdings(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Valide schema-holdings-put-request : une liste complète de positions."""
    _reject_unknown_fields(body, ("holdings",))
    holdings = body.get("holdings")
    if not isinstance(holdings, list):
        raise _validation_error("holdings doit être un tableau.")
    validated: list[dict[str, Any]] = []
    for holding in holdings:
        if not isinstance(holding, dict):
            raise _validation_error("Chaque position doit être un objet.")
        _reject_unknown_fields(holding, ("ticker", "quantity", "avgCost"))
        ticker = _string(holding, "ticker")
        quantity = _number(holding, "quantity")
        if quantity <= 0:
            raise _validation_error("quantity doit être supérieur à 0.")
        avg_cost = _number(holding, "avgCost")
        validated.append(
            {"ticker": ticker, "quantity": quantity, "avgCost": avg_cost}
        )
    return validated


def parse_pagination(
    event: dict[str, Any], default_limit: int
) -> tuple[int, str | None]:
    """Valide `limit` (1..100) et `cursor` (chaîne non vide si présent)."""
    query = event.get("queryStringParameters") or {}
    if not isinstance(query, dict):
        raise _validation_error("Paramètres de requête invalides.")
    limit = default_limit
    if "limit" in query:
        try:
            limit = int(query["limit"])
        except (TypeError, ValueError) as exc:
            raise _validation_error("limit doit être un entier.") from exc
        if limit < 1 or limit > MAX_LIMIT:
            raise _validation_error(f"limit doit être compris entre 1 et {MAX_LIMIT}.")
    cursor = None
    if "cursor" in query:
        cursor = query["cursor"]
        if not isinstance(cursor, str) or cursor == "":
            raise _validation_error("cursor doit être une chaîne non vide.")
    return limit, cursor


def path_parameter(event: dict[str, Any], name: str) -> str:
    """Retourne un paramètre de chemin non vide."""
    parameters = event.get("pathParameters") or {}
    value = parameters.get(name)
    if not isinstance(value, str) or value == "":
        raise _validation_error(f"Paramètre de chemin requis : {name}.")
    return value


def session_id(event: dict[str, Any]) -> str:
    """Valide le sessionId du contrat (UUID v4 généré par le serveur)."""
    value = path_parameter(event, "sessionId")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise _validation_error("sessionId doit être un UUID v4.") from exc
    if parsed.version != 4 or parsed.variant != uuid.RFC_4122:
        raise _validation_error("sessionId doit être un UUID v4.")
    return str(parsed)
