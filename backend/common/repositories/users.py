"""Accès à la table Users (contrat : db-users, partition : userId).

Un utilisateur est créé au premier appel de GET /me (contrat : api-me-get) ;
aucun mot de passe n'est stocké ici, Cognito s'en charge.
"""

from __future__ import annotations

from typing import Any


def get_user(user_id: str) -> dict[str, Any] | None:
    """Retourne l'utilisateur (schema-user), ou None s'il n'existe pas encore."""
    raise NotImplementedError


def put_user_if_absent(
    user_id: str,
    username: str,
    display_name: str | None = None,
    base_currency: str = "CAD",
) -> dict[str, Any]:
    """Crée l'utilisateur au premier appel, sans écraser un profil existant.

    Écriture conditionnelle (attribute_not_exists), donc idempotent.
    Retourne l'utilisateur créé ou celui déjà présent.
    """
    raise NotImplementedError


def update_investor_profile(user_id: str, investor_profile: dict[str, Any]) -> dict[str, Any]:
    """Remplace le profil investisseur (schema-investor-profile) en mise à jour
    partielle (les autres attributs sont conservés) et retourne l'utilisateur.

    Lève l'erreur si l'utilisateur n'existe pas (créé par put_user_if_absent).
    """
    raise NotImplementedError
