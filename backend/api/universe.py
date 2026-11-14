"""Validation des tickers contre l'univers du jeu de données.

Le contrat permet à la Lambda légère de lire « S3 de ce seul fichier, ou une
copie embarquée ». Ici : lecture directe du seul `universe.parquet` de la
version configurée, mise en cache entre invocations chaudes. pyarrow est
importé paresseusement pour garder ce module léger à l'import (et testable
sans S3 grâce à l'injection d'un autre validateur dans `app.handle_request`).
"""

from __future__ import annotations

import io
from typing import Any

from backend.common import config
from backend.common.http import ApiError

# { (bucket, version du jeu de données) : ensemble des tickers valides }
_CACHE: dict[tuple[str, str], frozenset[str]] = {}


def _s3_client() -> Any:
    """Client S3 créé au premier appel (runtime Lambda : boto3 est fourni)."""
    import boto3

    return boto3.client("s3")


def _read_tickers(parquet_bytes: bytes) -> list[str]:
    """Lit la seule colonne ticker du fichier d'univers."""
    import pyarrow.parquet as pq

    table = pq.read_table(io.BytesIO(parquet_bytes), columns=["ticker"])
    return [str(value) for value in table.column("ticker").to_pylist()]


def _known_tickers() -> frozenset[str]:
    """Ensemble des tickers de la version courante, avec cache."""
    bucket = config.dataset_bucket()
    version = config.dataset_version()
    cache_key = (bucket, version)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    key = f"dataset/{version}/universe.parquet"
    try:
        response = _s3_client().get_object(Bucket=bucket, Key=key)
        tickers = _read_tickers(response["Body"].read())
    except Exception as exc:  # S3 indisponible, variable absente, fichier corrompu
        raise ApiError(
            "INTERNAL",
            "Univers d'actifs indisponible pour valider les tickers.",
        ) from exc
    if not tickers:
        raise ApiError("INTERNAL", "L'univers d'actifs est vide.")
    known = frozenset(tickers)
    _CACHE[cache_key] = known
    return known


def validate_tickers(tickers: list[str]) -> None:
    """Vérifie que chaque ticker existe dans l'univers.

    Lève ApiError('ASSET_NOT_FOUND') en citant le premier ticker inconnu,
    sans jamais renvoyer le contenu du fichier d'univers.
    """
    known = _known_tickers()
    unknown = sorted({ticker for ticker in tickers if ticker not in known})
    if unknown:
        raise ApiError("ASSET_NOT_FOUND", f"Ticker inconnu : {unknown[0]}.")
