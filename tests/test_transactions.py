from datetime import date

import pytest

from services import transactions as svc
from utils.validators import ValidationError


def test_create_transaction(db, cat):
    tx_id = svc.add_transaction(1200, "Income", cat("Salary"), date(2026, 3, 1), "March salary")
    tx = svc.get_transaction(tx_id)
    assert tx["amount"] == 1200.0 and tx["type"] == "Income" and tx["category"] == "Salary"
    assert tx["date"] == date(2026, 3, 1) and tx["description"] == "March salary"
    assert tx["created_at"] is not None


def test_edit_transaction(db, cat):
    tx_id = svc.add_transaction(50, "Expense", cat("Food"), date(2026, 3, 2), "lunch")
    svc.update_transaction(tx_id, 75.5, "Expense", cat("Shopping"), date(2026, 3, 3), "shirt")
    tx = svc.get_transaction(tx_id)
    assert (tx["amount"], tx["category"], tx["date"], tx["description"]) == (
        75.5, "Shopping", date(2026, 3, 3), "shirt")


def test_delete_transaction(db, cat):
    tx_id = svc.add_transaction(10, "Expense", cat("Food"), date(2026, 3, 2))
    svc.delete_transaction(tx_id)
    assert svc.get_transaction(tx_id) is None
    with pytest.raises(ValidationError):
        svc.delete_transaction(tx_id)


@pytest.mark.parametrize("bad", [0, -5, "abc", None, float("nan")])
def test_reject_invalid_amounts(db, cat, bad):
    with pytest.raises(ValidationError):
        svc.add_transaction(bad, "Expense", cat("Food"), date(2026, 3, 2))
    assert svc.list_transactions().empty


def test_reject_invalid_category_type_and_date(db, cat):
    with pytest.raises(ValidationError):
        svc.add_transaction(10, "Expense", 99999, date(2026, 3, 2))
    with pytest.raises(ValidationError):
        svc.add_transaction(10, "Expense", None, date(2026, 3, 2))
    with pytest.raises(ValidationError):  # income category used for an expense
        svc.add_transaction(10, "Expense", cat("Salary"), date(2026, 3, 2))
    with pytest.raises(ValidationError):
        svc.add_transaction(10, "Transfer", cat("Food"), date(2026, 3, 2))
    with pytest.raises(ValidationError):
        svc.add_transaction(10, "Expense", cat("Food"), "2026-13-45")
    assert svc.list_transactions().empty


def test_invalid_update_keeps_original(db, cat):
    tx_id = svc.add_transaction(20, "Expense", cat("Food"), date(2026, 3, 2), "orig")
    with pytest.raises(ValidationError):
        svc.update_transaction(tx_id, -1, "Expense", cat("Food"), date(2026, 3, 2), "changed")
    assert svc.get_transaction(tx_id)["description"] == "orig"


def test_search_filter_and_sort(db, cat):
    svc.add_transaction(10, "Expense", cat("Food"), date(2026, 3, 1), "Coffee 100%")
    svc.add_transaction(300, "Expense", cat("Shopping"), date(2026, 3, 5), "Shoes")
    svc.add_transaction(2000, "Income", cat("Salary"), date(2026, 3, 10), "Pay")
    assert len(svc.list_transactions(search="coffee")) == 1
    assert len(svc.list_transactions(search="100%")) == 1       # % is escaped
    assert len(svc.list_transactions(search="shopping")) == 1   # matches category name
    assert len(svc.list_transactions(tx_type="Expense")) == 2
    assert len(svc.list_transactions(start=date(2026, 3, 4), end=date(2026, 3, 9))) == 1
    assert len(svc.list_transactions(category_ids=[cat("Salary")])) == 1
    by_amount = svc.list_transactions(sort_by="amount", ascending=False)
    assert list(by_amount["amount"]) == [2000.0, 300.0, 10.0]
    assert list(svc.list_transactions(sort_by="date", ascending=True)["description"])[0] == "Coffee 100%"
