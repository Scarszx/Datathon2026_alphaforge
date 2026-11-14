"""Accès à la table Analyses (contrat v0.4.0 : db-analyses).

WS0b fixe ici les signatures, les docstrings et le comportement attendu.
WS2b (branche ws/db-v4) implémente ce module sans changer les signatures.

Clé : partition sessionId, tri itemKey.
- Mandat : itemKey = "MANDATE#<version sur 3 chiffres>" (ex. MANDATE#001), type = "mandate".
- Run    : itemKey = "RUN#<runId>" (runId = ULID, voir backend.common.ids.new_run_id), type = "run".

Chaque item porte userId. Toute lecture vérifie que userId correspond :
une ressource d'un autre utilisateur se comporte comme inexistante (None).

Les objets échangés suivent les schémas du contrat (camelCase) :
schema-mandate pour un mandat, schema-run pour un run.
"""

from __future__ import annotations

from typing import Any

MANDATE_PREFIX = "MANDATE#"
RUN_PREFIX = "RUN#"


def mandate_item_key(version: int) -> str:
    """Clé de tri d'un mandat : MANDATE#001, MANDATE#002…"""
    return f"{MANDATE_PREFIX}{version:03d}"


def run_item_key(run_id: str) -> str:
    """Clé de tri d'un run : RUN#<runId>."""
    return f"{RUN_PREFIX}{run_id}"


def put_mandate(session_id: str, user_id: str, mandate: dict[str, Any]) -> dict[str, Any]:
    """Enregistre une nouvelle version de mandat et la retourne (schema-mandate).

    - version = dernière version de la session + 1 (1 pour le premier mandat) ;
    - écriture conditionnelle (attribute_not_exists sur la clé) pour qu'un appel
      concurrent ne crée jamais deux fois la même version ;
    - `mandate` contient les champs calculés par l'appelant (mandate, riskProfile,
      effectiveMaxLossPct, warnings, changedFields, confirmedAt) ; cette fonction
      ajoute sessionId, version, userId, type et itemKey.
    """
    raise NotImplementedError


def get_mandate(session_id: str, user_id: str, version: int) -> dict[str, Any] | None:
    """Retourne la version demandée du mandat (schema-mandate), ou None si absente ou non possédée."""
    raise NotImplementedError


def get_latest_mandate(session_id: str, user_id: str) -> dict[str, Any] | None:
    """Retourne la version la plus récente du mandat, ou None s'il n'y en a pas."""
    raise NotImplementedError


def list_mandates(session_id: str, user_id: str) -> list[dict[str, Any]]:
    """Retourne toutes les versions du mandat de la session, la plus récente d'abord (schema-mandate-list.items)."""
    raise NotImplementedError


def put_run(session_id: str, user_id: str, run: dict[str, Any]) -> dict[str, Any]:
    """Enregistre un nouveau run (schema-run, en général status = partial) et le retourne.

    `run` contient runId (généré par l'appelant avec ids.new_run_id()) ; cette
    fonction ajoute userId, type et itemKey. Échoue si le runId existe déjà.
    """
    raise NotImplementedError


def update_run(session_id: str, user_id: str, run_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Met à jour partiellement un run (UpdateItem) et retourne le run complet.

    Usage typique : passage de partial à done (status, narrative, verifier,
    verdicts enrichis de citations, evidence complétée, completedAt).
    Lève ApiError("RUN_NOT_FOUND") si le run n'existe pas ou n'appartient pas à user_id.
    """
    raise NotImplementedError


def get_run(session_id: str, user_id: str, run_id: str) -> dict[str, Any] | None:
    """Retourne le run (schema-run), ou None s'il est absent ou non possédé."""
    raise NotImplementedError


def delete_analyses(session_id: str, user_id: str) -> None:
    """Supprime tous les mandats et runs de la session (appelé à la suppression d'une conversation).

    Ne supprime rien si les items n'appartiennent pas à user_id.
    """
    raise NotImplementedError
