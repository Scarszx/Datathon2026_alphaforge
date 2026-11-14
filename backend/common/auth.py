"""Identité de l'appelant, extraite du JWT (règle rule-identity-from-jwt).

userId = claim 'sub' du jeton Cognito validé par l'authorizer de l'API Gateway.
Il est toujours lu dans le contexte de la requête, jamais dans le corps ni
dans un paramètre fourni par le modèle.
"""

from __future__ import annotations

from typing import Any

from backend.common.http import ApiError


def get_user_id(event: dict[str, Any]) -> str:
    """Extrait userId du claim 'sub' d'un événement API Gateway HTTP API payload v2.

    Lève ApiError('UNAUTHORIZED') si le JWT validé est absent ou sans 'sub'.
    """
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    jwt = authorizer.get("jwt") or {}
    claims = jwt.get("claims") or {}
    user_id = claims.get("sub")
    if not user_id:
        raise ApiError("UNAUTHORIZED", "Jeton d'accès absent ou invalide.")
    return str(user_id)
