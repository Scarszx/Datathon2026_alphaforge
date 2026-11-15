"""Opérations d'un mandat : add/remove portent un amount, set_weight un weight (schema-operation)."""
import pytest

from backend.common import validation
from backend.common.http import ApiError


def _op(**fields):
    return validation._validate_operation(fields)


def test_operations_valides():
    assert _op(action="add", ticker="NVDA", amount=15000, currency="CAD")["amount"] == 15000
    assert "amount" not in _op(action="remove", ticker="SHOP.TO")  # retirer la position entière
    assert _op(action="remove", ticker="XIC.TO", amount=5000)["amount"] == 5000
    assert _op(action="set_weight", ticker="VFV.TO", weight=25)["weight"] == 25


@pytest.mark.parametrize("fields", [
    {"action": "add", "ticker": "VFV.TO"},                              # add sans montant
    {"action": "add", "ticker": "VFV.TO", "weight": 25},                # weight sur add (cas observé le 2026-11-15)
    {"action": "remove", "ticker": "XIC.TO", "weight": 25},             # weight sur remove (cas observé)
    {"action": "set_weight", "ticker": "VFV.TO"},                       # set_weight sans poids
    {"action": "set_weight", "ticker": "VFV.TO", "weight": 25, "amount": 1000},
])
def test_operations_mal_formees_refusees(fields):
    with pytest.raises(ApiError):
        _op(**fields)
