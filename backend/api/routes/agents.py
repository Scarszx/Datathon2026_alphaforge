"""Route /agents : registre public des agents et outils (api-agents-registry).

Le contenu est une copie statique de la section agents et tools du contrat
(`registry.json`), sans dépendance YAML. La route reste authentifiée par JWT
comme les autres routes de l'API.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from backend.common.http import json_response


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    with resources.files("backend.api").joinpath("registry.json").open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)


def get_registry(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """GET /v1/agents : { agents: [...], tools: [...] }."""
    return json_response(200, _registry())
