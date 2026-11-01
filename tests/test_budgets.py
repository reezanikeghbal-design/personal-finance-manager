from datetime import date

import pytest

from services import budgets as svc
from services import transactions as tx_svc
from utils.validators import ValidationError


def test_create_edit_delete_budget(db, cat):
    bid = svc.create_budget(cat("Food"), "2026-03", 500)
    assert svc.list_budgets("2026-03").iloc[0]["amount"] == 500.0
    svc.update_budget(bid, 650)
    assert svc.list_budgets("2026-03").iloc[0]["amount"] == 650.0
    svc.delete_budget(bid)
    assert svc.list_budgets("2026-03").empty


def test_invalid_budgets_rejected(db, cat):
    with pytest.raises(ValidationError):
        svc.create_budget(cat("Food"), "2026-03", -10)
    with pytest.raises(ValidationError):
        svc.create_budget(cat("Food"), "2026-03", 0)
    with pytest.raises(ValidationError):
        svc.create_budget(cat("Food"), "March", 100)
    with pytest.raises(ValidationError):
        svc.create_budget(cat("Salary"), "2026-03", 100)   # income category
    svc.create_budget(cat("Food"), "2026-03", 100)
    with pytest.raises(ValidationError):
        svc.create_budget(cat("Food"), "2026-03", 200)     # duplicate month/category
    assert len(svc.list_budgets()) == 1


def test_budget_status_from_database(db, cat):
    svc.create_budget(cat("Food"), "2026-03", 300)
    svc.create_budget(cat("Travel"), "2026-03", 1000)
    tx_svc.add_transaction(200, "Expense", cat("Food"), date(2026, 3, 5))
    tx_svc.add_transaction(150, "Expense", cat("Food"), date(2026, 3, 20))
    tx_svc.add_transaction(999, "Expense", cat("Food"), date(2026, 4, 1))   # other month
    tx_svc.add_transaction(100, "Expense", cat("Travel"), date(2026, 3, 9))
    status = svc.get_budget_status("2026-03").set_index("category")
    assert status.loc["Food", "spent"] == 350.0 and status.loc["Food", "remaining"] == -50.0
    assert bool(status.loc["Food", "exceeded"])
    assert round(status.loc["Food", "usage_pct"], 2) == 116.67
    assert status.loc["Travel", "remaining"] == 900.0 and not status.loc["Travel", "exceeded"]


def test_deleting_category_removes_its_budgets(db, cat):
    from services import categories
    cid = categories.create_category("Temp", "Expense")
    svc.create_budget(cid, "2026-03", 50)
    categories.delete_category(cid)
    assert svc.list_budgets().empty
