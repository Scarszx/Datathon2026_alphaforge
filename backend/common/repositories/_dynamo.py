"""Utilitaires internes partagés par les repositories (non exportés).

- Ressource boto3 DynamoDB créée une fois par conteneur Lambda.
- Curseurs opaques : base64 urlsafe du JSON de LastEvaluatedKey.
- Conversion des nombres : DynamoDB refuse les float (Decimal obligatoire) et
  renvoie des Decimal ; on convertit à l'écriture et à la lecture.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from typing import Any

import boto3

from backend.common.http import ApiError

MAX_LIMIT = 100


@lru_cache(maxsize=1)
def _resource() -> Any:
    """Ressource DynamoDB, créée au premier appel puis réutilisée."""
    return boto3.resource("dynamodb")


def table(name: str) -> Any:
    """Objet Table boto3 pour le nom donné (lu via backend.common.config)."""
    return _resource().Table(name)


def reset_client() -> None:
    """Oublie la ressource en cache (tests : changement de mock ou de région)."""
    _resource.cache_clear()


def is_conditional_failure(error: Exception) -> bool:
    """Vrai si l'erreur boto3 est un échec d'écriture conditionnelle."""
    response = getattr(error, "response", None) or {}
    return response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def now_iso() -> str:
    """Horodatage ISO 8601 UTC du contrat, ex. 2026-11-14T09:30:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clamp_limit(limit: int | None, default: int) -> int:
    """Borne limit entre 1 et MAX_LIMIT (default si None)."""
    if limit is None:
        return default
    return max(1, min(int(limit), MAX_LIMIT))


def encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    """Curseur opaque à partir de LastEvaluatedKey (None s'il n'y a plus de page)."""
    if not last_evaluated_key:
        return None
    raw = json.dumps(from_dynamo(last_evaluated_key), separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None, expected_keys: set[str]) -> dict[str, Any] | None:
    """ExclusiveStartKey à partir du curseur. Curseur illisible : VALIDATION_ERROR."""
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        key = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ApiError("VALIDATION_ERROR", "Curseur de pagination invalide.") from exc
    if not isinstance(key, dict) or set(key) != expected_keys:
        raise ApiError("VALIDATION_ERROR", "Curseur de pagination invalide.")
    if not all(isinstance(v, str) for v in key.values()):
        raise ApiError("VALIDATION_ERROR", "Curseur de pagination invalide.")
    return key


def to_dynamo(value: Any) -> Any:
    """Convertit récursivement les float en Decimal pour l'écriture."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_dynamo(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dynamo(v) for v in value]
    return value


def from_dynamo(value: Any) -> Any:
    """Convertit récursivement les Decimal en int ou float pour la lecture."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: from_dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_dynamo(v) for v in value]
    return value
