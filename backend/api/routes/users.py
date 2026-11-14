"""Routes /me et /me/profile (api-me-get, api-me-profile-put).

Le profil est créé au premier appel. L'utilisateur est identifié par le
claim `sub` du JWT, reçu du contexte ; le nom affiché vient des claims
Cognito et n'est jamais lu dans le corps de la requête.
"""

from __future__ import annotations

from typing import Any

from backend.api.validation import parse_json_body, validate_investor_profile
from backend.common.http import json_response
from backend.common.repositories import users as repo


def _claims(event: dict[str, Any]) -> dict[str, Any]:
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    jwt = authorizer.get("jwt") or {}
    return jwt.get("claims") or {}


def _username(event: dict[str, Any], user_id: str) -> str:
    claims = _claims(event)
    username = claims.get("cognito:username") or claims.get("username")
    return username if isinstance(username, str) and username else user_id


def _display_name(event: dict[str, Any]) -> str | None:
    display_name = _claims(event).get("name")
    return display_name if isinstance(display_name, str) and display_name else None


def get_me(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """GET /v1/me : crée le profil au premier appel, sinon le retourne."""
    user = repo.get_user(user_id)
    if user is None:
        user = repo.put_user_if_absent(
            user_id,
            username=_username(event, user_id),
            display_name=_display_name(event),
        )
    return json_response(200, user)


def put_profile(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """PUT /v1/me/profile : remplace le profil investisseur.

    `put_user_if_absent` est idempotent : un appel direct sans GET /me
    préalable ne laisse pas l'utilisateur dans un état non initialisé.
    """
    profile = validate_investor_profile(parse_json_body(event))
    repo.put_user_if_absent(
        user_id,
        username=_username(event, user_id),
        display_name=_display_name(event),
    )
    user = repo.update_investor_profile(user_id, profile)
    return json_response(200, user)
