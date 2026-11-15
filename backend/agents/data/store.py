"""Lecture du jeu de données de marché (contrat : storage-dataset), en lecture seule.

Disposition attendue (contrat, section storage) sous une racine versionnée :
    manifest.json, universe.parquet, prices/{ticker}.parquet, fx/usdcad.parquet,
    macro/macro.parquet, corporate_actions.parquet, etf_enriched.json

La racine est un dossier local (tests, banc) ou s3://<bucket>/dataset/<version>/
(Lambda). Seules les colonnes utiles sont lues, et chaque fichier est gardé en
mémoire du conteneur (performance_notes du contrat). Aucune ligne brute ne sort
de ce module vers un modèle : les outils renvoient des chiffres.
"""

from __future__ import annotations

import io
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from backend.common import config

PRICE_COLUMNS = ["date", "close", "adjclose", "currency"]
UNIVERSE_COLUMNS = ["symbol", "name", "asset_class", "market", "currency", "sector"]
OPTIONAL_UNIVERSE_COLUMNS = ["industry", "country"]  # absentes des jeux antérieurs à 0.4.8
NON_INVESTABLE_CLASSES = {"index"}  # ex. ^GSPC : référence de comparaison, jamais en portefeuille


class DatasetError(RuntimeError):
    """Fichier du jeu de données absent ou illisible (déploiement incomplet)."""


@dataclass
class DataStore:
    """Accès au jeu de données d'une version, avec cache en mémoire.

    root : dossier local ou URI s3://bucket/prefix (sans / final obligatoire).
    """

    root: str
    version: str
    _cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # --- lecture brute -------------------------------------------------------

    def _read_bytes(self, relative: str) -> bytes:
        if self.root.startswith("s3://"):
            import boto3  # import tardif : les tests locaux n'en ont pas besoin

            bucket, _, prefix = self.root[5:].partition("/")
            key = f"{prefix.rstrip('/')}/{relative}" if prefix else relative
            try:
                obj = _s3_client().get_object(Bucket=bucket, Key=key)
            except Exception as exc:  # ClientError, NoSuchKey
                raise DatasetError(f"Missing dataset object: {key}") from exc
            return obj["Body"].read()
        path = Path(self.root) / relative
        if not path.is_file():
            raise DatasetError(f"Missing dataset file: {relative}")
        return path.read_bytes()

    def _exists(self, relative: str) -> bool:
        try:
            self._read_bytes(relative)
            return True
        except DatasetError:
            return False

    def _cached(self, key: str, loader) -> Any:
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        value = loader()
        with self._lock:
            self._cache[key] = value
        return value

    def _parquet(self, relative: str, columns: list[str] | None = None) -> pd.DataFrame:
        raw = self._read_bytes(relative)
        frame = pd.read_parquet(io.BytesIO(raw))
        if columns is not None:
            present = [c for c in columns if c in frame.columns]
            frame = frame[present]
        return frame

    # --- fichiers du contrat -------------------------------------------------

    def manifest(self) -> dict[str, Any]:
        def load() -> dict[str, Any]:
            try:
                return json.loads(self._read_bytes("manifest.json"))
            except DatasetError:
                return {}

        return self._cached("manifest", load)

    def universe(self) -> pd.DataFrame:
        """Une ligne par actif, indexée par symbole (colonnes UNIVERSE_COLUMNS)."""

        def load() -> pd.DataFrame:
            frame = self._parquet("universe.parquet")
            missing = [c for c in UNIVERSE_COLUMNS if c not in frame.columns]
            if missing:
                raise DatasetError(f"universe.parquet lacks columns: {missing}")
            return frame.set_index("symbol", drop=False)

        return self._cached("universe", load)

    def has_ticker(self, ticker: str) -> bool:
        return ticker in self.universe().index

    def is_investable(self, ticker: str) -> bool:
        """Dans l'univers et pas un indice de référence."""
        if not self.has_ticker(ticker):
            return False
        return str(self.universe().loc[ticker, "asset_class"]).lower() not in NON_INVESTABLE_CLASSES

    def asset(self, ticker: str) -> dict[str, Any]:
        row = self.universe().loc[ticker]
        columns = UNIVERSE_COLUMNS + [c for c in OPTIONAL_UNIVERSE_COLUMNS if c in row.index]
        return {c: (None if pd.isna(row[c]) else row[c]) for c in columns}

    def prices(self, ticker: str) -> pd.DataFrame:
        """Prix journaliers d'un ticker : index date (Timestamp), colonnes close, adjclose, currency."""

        def load() -> pd.DataFrame:
            safe = ticker.replace("/", "_")
            frame = self._parquet(f"prices/{safe}.parquet", PRICE_COLUMNS)
            frame["date"] = pd.to_datetime(frame["date"])
            frame = frame.dropna(subset=["adjclose"]).sort_values("date")
            frame = frame[frame["adjclose"] > 0]
            return frame.drop_duplicates("date", keep="last").set_index("date")

        return self._cached(f"prices:{ticker}", load)

    def fx_usdcad(self) -> pd.Series:
        """Taux USD/CAD (CAD par USD), indexé par date."""

        def load() -> pd.Series:
            frame = self._parquet("fx/usdcad.parquet", ["date", "usdcad"])
            frame["date"] = pd.to_datetime(frame["date"])
            return frame.dropna().sort_values("date").set_index("date")["usdcad"]

        return self._cached("fx", load)

    def macro(self) -> pd.DataFrame:
        """Séries macro (format long). publication_date est présente si WS3 l'a ajoutée."""

        def load() -> pd.DataFrame:
            frame = self._parquet("macro/macro.parquet")
            frame["date"] = pd.to_datetime(frame["date"])
            if "publication_date" in frame.columns:
                frame["publication_date"] = pd.to_datetime(frame["publication_date"])
            return frame.sort_values(["series_id", "date"])

        return self._cached("macro", load)

    def etf_enriched(self) -> dict[str, dict[str, Any]]:
        """Fiches enrichies des FNB, par ticker ({} si le fichier est absent).

        Formes acceptées : { "etfs": { ticker: fiche } }, { ticker: fiche },
        ou { "etfs": [ { "ticker": ..., ... } ] }.
        """

        def load() -> dict[str, dict[str, Any]]:
            try:
                payload = json.loads(self._read_bytes("etf_enriched.json"))
            except DatasetError:
                return {}
            body = payload.get("etfs", payload) if isinstance(payload, dict) else payload
            if isinstance(body, list):
                return {item["ticker"]: item for item in body if isinstance(item, dict) and "ticker" in item}
            if isinstance(body, dict):
                return {k: v for k, v in body.items() if isinstance(v, dict)}
            return {}

        return self._cached("etf_enriched", load)

    def profiles(self) -> dict[str, dict[str, Any]]:
        """Descriptions d'entreprise par ticker ({ ticker: { description, website } }), {} si absent.

        Fichier facultatif `profiles.json` du jeu : sans lui, la fiche d'un actif n'a pas de description.
        """

        def load() -> dict[str, dict[str, Any]]:
            try:
                payload = json.loads(self._read_bytes("profiles.json"))
            except (DatasetError, ValueError):
                return {}
            return {k: v for k, v in payload.items() if isinstance(v, dict)} if isinstance(payload, dict) else {}

        return self._cached("profiles", load)

    def last_date(self) -> pd.Timestamp:
        """Dernière date de cours du jeu (asOf), d'après le manifeste ou SPY / XIU.TO."""
        manifest = self.manifest()
        for key in ("periodEnd", "end", "asOf"):
            if manifest.get(key):
                return pd.Timestamp(manifest[key])
        for ticker in ("SPY", "XIU.TO"):
            if self.has_ticker(ticker):
                return self.prices(ticker).index.max()
        last = None
        for ticker in self.universe().index[:5]:
            candidate = self.prices(ticker).index.max()
            last = candidate if last is None or candidate > last else last
        if last is None:
            raise DatasetError("Empty dataset")
        return last

    def source_label(self, relative: str) -> str:
        """Chemin versionné cité dans explanation.sources (rule-dataset-pinned)."""
        return f"{relative}@{self.version}"


_S3 = None


def _s3_client():
    global _S3
    if _S3 is None:
        import boto3

        _S3 = boto3.client("s3")
    return _S3


_DEFAULT_STORE: DataStore | None = None


def default_store() -> DataStore:
    """Magasin du conteneur : s3://DATASET_BUCKET/dataset/DATASET_VERSION/."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        version = config.dataset_version()
        _DEFAULT_STORE = DataStore(
            root=f"s3://{config.dataset_bucket()}/dataset/{version}", version=version
        )
    return _DEFAULT_STORE


def set_default_store(store: DataStore | None) -> None:
    """Injecte un magasin (tests, banc local)."""
    global _DEFAULT_STORE
    _DEFAULT_STORE = store
