"""Tests du validateur embarqué et du script de régénération."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from backend.api import universe
from backend.api.scripts import build_tickers
from backend.common.http import ApiError


def test_le_validateur_reel_accepte_un_ticker_connu():
    universe.validate_tickers(["RY.TO", "AAPL"])


def test_le_validateur_reel_refuse_un_ticker_inconnu():
    with pytest.raises(ApiError) as error:
        universe.validate_tickers(["RY.TO", "TICKER-INCONNU"])
    assert error.value.code == "ASSET_NOT_FOUND"
    assert "TICKER-INCONNU" in error.value.message


def test_tickers_json_est_valide_trie_et_sans_doublon():
    with Path("backend/api/tickers.json").open("r", encoding="utf-8") as file:
        payload = json.load(file)
    assert set(payload) == {"source", "tickers"}
    assert isinstance(payload["source"], str) and payload["source"]
    tickers = payload["tickers"]
    assert tickers
    assert all(isinstance(ticker, str) and ticker for ticker in tickers)
    assert tickers == sorted(tickers)
    assert len(tickers) == len(set(tickers))


def test_le_script_n_importe_pas_pyarrow_a_l_import():
    assert "pyarrow" not in sys.modules
    assert "pyarrow.parquet" not in sys.modules


def test_build_payload_trie_et_refuse_les_doublons():
    payload = build_tickers.build_payload(["BTC-USD", "AAPL"], "test")
    assert payload["source"] == "test"
    assert payload["tickers"] == ["AAPL", "BTC-USD"]

    # Un doublon signale une source corrompue : on refuse plutôt que de
    # dédupliquer silencieusement.
    with pytest.raises(ValueError, match="dupliqué"):
        build_tickers.build_payload(["AAPL", "AAPL"], "test")


def test_build_tickers_lit_un_csv(tmp_path):
    csv_path = tmp_path / "assets_universe.csv"
    csv_path.write_text(
        "asset_id,ticker,name\nA02,AAPL,Apple\nA01,RY.TO,Royal Bank\n",
        encoding="utf-8",
    )
    output = tmp_path / "tickers.json"

    payload = build_tickers.build_payload(
        build_tickers._read_csv(csv_path), "assets_universe.csv@test"
    )
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    assert json.loads(output.read_text(encoding="utf-8")) == {
        "source": "assets_universe.csv@test",
        "tickers": ["AAPL", "RY.TO"],
    }
