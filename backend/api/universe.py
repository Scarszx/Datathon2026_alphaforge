"""Validation des tickers contre la copie embarquée de l'univers.

Le contrat autorise « lecture S3 de ce seul fichier, ou copie embarquée ».
La Lambda légère utilise la copie embarquée `tickers.json` : aucun accès S3
ni aucune dépendance Parquet à l'exécution. Si WS3 élargit l'univers, la
copie doit être régénérée (voir README.md).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from backend.common.http import ApiError


@lru_cache(maxsize=1)
def _tickers() -> frozenset[str]:
    """Ensemble des tickers embarqués, lu une fois puis mis en cache."""
    with resources.files("backend.api").joinpath("tickers.json").open(
        "r", encoding="utf-8"
    ) as file:
        payload: dict[str, Any] = json.load(file)
    tickers = payload.get("tickers")
    if not isinstance(tickers, list) or not tickers:
        raise RuntimeError("tickers.json ne contient aucun ticker.")
    if any(not isinstance(ticker, str) or not ticker for ticker in tickers):
        raise RuntimeError("tickers.json contient un ticker invalide.")
    return frozenset(tickers)


def validate_tickers(tickers: list[str]) -> None:
    """Vérifie que chaque ticker existe dans la copie embarquée.

    Lève ApiError('ASSET_NOT_FOUND') en citant le premier ticker inconnu.
    """
    known = _tickers()
    unknown = sorted({ticker for ticker in tickers if ticker not in known})
    if unknown:
        raise ApiError("ASSET_NOT_FOUND", f"Ticker inconnu : {unknown[0]}.")
