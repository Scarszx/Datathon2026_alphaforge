"""Génère `backend/api/tickers.json` à partir d'un univers d'actifs.

Usage :

    python -m backend.api.scripts.build_tickers \
        --input data/output/<version>/universe.parquet \
        --output backend/api/tickers.json \
        --source "universe.parquet@2026-11-13"

Le format d'entrée est déduit de l'extension : CSV (module standard) ou
Parquet (pyarrow). `pyarrow` n'est donc jamais importé par la Lambda : ce
script n'est utilisé que pour régénérer la copie embarquée hors runtime.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


def _symbol_column(columns: Iterable[str], path: Path) -> str:
    """`symbol` (jeu 0.4.8) ou `ticker` (jeu de départ, jeux antérieurs)."""
    names = list(columns)
    for candidate in ("symbol", "ticker"):
        if candidate in names:
            return candidate
    raise ValueError(f"Colonne 'symbol' (ou 'ticker') absente : {path}")


def _read_csv(path: Path) -> list[str]:
    """Lit la colonne symbole d'un CSV (assets_universe ou univers WS3)."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        column = _symbol_column(reader.fieldnames or [], path)
        return [str(row[column]) for row in reader if str(row.get("asset_class", "")).lower() != "index"]


def _read_parquet(path: Path) -> list[str]:
    """Lit la colonne symbole d'un Parquet (indices exclus). pyarrow est hors runtime."""
    import pyarrow.parquet as pq

    names = pq.read_schema(path).names
    column = _symbol_column(names, path)
    wanted = [column] + (["asset_class"] if "asset_class" in names else [])
    table = pq.read_table(path, columns=wanted).to_pydict()
    classes = table.get("asset_class") or [""] * len(table[column])
    return [str(s) for s, c in zip(table[column], classes) if str(c).lower() != "index"]


def _read_tickers(path: Path) -> list[str]:
    if path.suffix.lower() == ".parquet":
        return _read_parquet(path)
    return _read_csv(path)


def build_payload(tickers: Iterable[str], source: str) -> dict[str, Any]:
    """Retourne un JSON trié, sans doublon ni ticker vide."""
    values = [ticker.strip() for ticker in tickers]
    if any(not ticker for ticker in values):
        raise ValueError("Ticker vide dans l'univers d'entrée.")
    known = list(dict.fromkeys(values))
    if len(known) != len(values):
        raise ValueError("Ticker dupliqué dans l'univers d'entrée.")
    if not known:
        raise ValueError("L'univers d'entrée est vide.")
    return {"source": source, "tickers": sorted(known)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="CSV ou Parquet contenant la colonne symbol (ou ticker).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Chemin de tickers.json à régénérer.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Origine et version, ex. universe.parquet@2026-11-13.",
    )
    arguments = parser.parse_args()
    tickers = _read_tickers(arguments.input)
    payload = build_payload(tickers, arguments.source)
    arguments.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
