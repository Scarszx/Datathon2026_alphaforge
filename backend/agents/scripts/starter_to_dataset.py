"""Convertit le jeu de départ (CSV, hors git) vers la disposition du contrat, pour le banc local.

Ce n'est PAS le jeu élargi (WS3, data/) : c'est un pont pour exercer la Lambda
agents sur de vraies données en attendant WS3. La sortie ne doit jamais être
commitée (conditions d'utilisation de Yahoo). Pas de publication_date sur la
macro mensuelle (le jeu de départ ne l'a pas) ni de etf_enriched.json : la
concentration lit alors les FNB par catégorie, et c'est signalé.

Usage :
    python -m backend.agents.scripts.starter_to_dataset <dossier_alphaforge_starter> <dossier_sortie>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def convert(starter: Path, out: Path) -> None:
    (out / "prices").mkdir(parents=True, exist_ok=True)
    (out / "fx").mkdir(exist_ok=True)
    (out / "macro").mkdir(exist_ok=True)
    universe = pd.read_csv(starter / "assets_universe.csv").rename(columns={"ticker": "symbol"})
    universe.to_parquet(out / "universe.parquet", index=False)
    prices = pd.read_csv(starter / "prices_daily.csv", parse_dates=["date"]).rename(
        columns={"ticker": "symbol", "adj_close": "adjclose"}
    )
    for ticker, rows in prices.groupby("symbol"):
        rows.drop(columns=["symbol"]).to_parquet(out / "prices" / f"{ticker}.parquet", index=False)
    pd.read_csv(starter / "fx_usdcad_daily.csv", parse_dates=["date"]).to_parquet(out / "fx" / "usdcad.parquet", index=False)
    pd.read_csv(starter / "macro_rates.csv", parse_dates=["date"]).to_parquet(out / "macro" / "macro.parquet", index=False)
    pd.read_csv(starter / "corporate_actions.csv").rename(columns={"ticker": "symbol"}).to_parquet(out / "corporate_actions.parquet", index=False)
    (out / "manifest.json").write_text(json.dumps({
        "version": "starter-2026-11-13", "source": "alphaforge_starter (organizers), converted by WS5 for local tests",
        "periodStart": str(prices["date"].min().date()), "periodEnd": str(prices["date"].max().date()),
        "tickers": sorted(universe["symbol"]),
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    convert(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"Dataset written to {sys.argv[2]}")
