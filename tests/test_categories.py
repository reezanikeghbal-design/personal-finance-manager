from datetime import date

import pytest

from services import categories as svc
from services import transactions as tx_svc
from utils.validators import ValidationError


def test_default_categories_exist(db):
    names = {c["name"] for c in svc.list_categories()}
    assert {"Salary", "Freelance", "Investment", "Business", "Other Income", "Housing", "Food",
            "Transportation", "Healthcare", "Shopping", "Entertainment", "Education", "Utilities",
            "Travel", "Other Expenses"} <= names
    assert len(svc.list_categories("Income")) == 5 and len(svc.list_categories("Expense")) == 10


def test_create_rename_and_no_duplicates(db):
    cid = svc.create_category("Pet Care", "Expense")
    with pytest.raises(ValidationError):
        svc.create_category("pet care", "Expense")
    with pytest.raises(ValidationError):
        svc.rename_category(cid, "Food")
    svc.rename_category(cid, "Pets")
    assert svc.get_category(cid)["name"] == "Pets"


def test_delete_unused_category(db):
    cid = svc.create_category("Temp", "Expense")
    assert svc.delete_category(cid) == 0
    assert svc.get_category(cid) is None


def test_cannot_delete_used_category_without_reassignment(db):
    cats = {c["name"]: c["id"] for c in svc.list_categories()}
    tx_svc.add_transaction(10, "Expense", cats["Food"], date(2026, 3, 1))
    with pytest.raises(ValidationError):
        svc.delete_category(cats["Food"])
    with pytest.raises(ValidationError):  # wrong type
        svc.delete_category(cats["Food"], reassign_to=cats["Salary"])
    assert svc.delete_category(cats["Food"], reassign_to=cats["Shopping"]) == 1
    assert tx_svc.list_transactions().iloc[0]["category"] == "Shopping"
