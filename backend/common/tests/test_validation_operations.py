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


# --- compareCategory (lot B) ---------------------------------------------------------------------------------------

from backend.common.categories import category_ids, categories  # noqa: E402


def _mandate_body(**extra):
    base = {"portfolioId": "main", "mode": "add_asset", "objective": "project", "horizonYears": 3, "riskTolerance": 3,
            "riskCapacity": 2, "province": "QC", "userLanguage": "fr",
            "operations": [{"action": "add", "ticker": "NVDA", "amount": 100, "currency": "CAD"}]}
    base.update(extra)
    return base


def test_compare_category_facultatif_et_limite_aux_categories_connues():
    from backend.common.validation import validate_mandate_create

    assert "compareCategory" not in validate_mandate_create(_mandate_body())
    for category_id in category_ids():
        assert validate_mandate_create(_mandate_body(compareCategory=category_id))["compareCategory"] == category_id
    for bad in ("XBB.TO", "", True, 2, "unknown"):
        with pytest.raises(ApiError) as error:
            validate_mandate_create(_mandate_body(compareCategory=bad))
        assert error.value.code == "VALIDATION_ERROR"


def test_categories_sans_symbole_dans_les_libelles_et_triees_par_niveau():
    items = categories()
    assert [c["level"] for c in items] == sorted(c["level"] for c in items)
    assert len({c["id"] for c in items}) == len(items)
    for category in items:
        assert not any(proxy in category["label"] for proxy in category["proxies"])
