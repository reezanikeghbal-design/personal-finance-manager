"""Monthly budget management."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.db import session_scope
from database.models import Budget, Category
from services import analytics
from services.transactions import list_transactions
from utils.helpers import month_bounds
from utils.validators import ValidationError, validate_budget_amount, validate_month

BUDGET_COLUMNS = ["id", "category_id", "category", "month", "amount"]


def create_budget(category_id: int, month, amount) -> int:
    month, amount = validate_month(month), validate_budget_amount(amount)
    try:
        with session_scope() as s:
            cat = s.get(Category, category_id) if isinstance(category_id, int) else None
            if cat is None:
                raise ValidationError("Selected category does not exist.")
            if cat.type != "Expense":
                raise ValidationError("Budgets can only be set for expense categories.")
            exists = s.execute(select(Budget.id).where(
                Budget.category_id == cat.id, Budget.month == month)).first()
            if exists:
                raise ValidationError(f"A budget for '{cat.name}' in {month} already exists. Edit it instead.")
            b = Budget(category_id=cat.id, month=month, amount=amount)
            s.add(b)
            s.flush()
            return b.id
    except IntegrityError:
        raise ValidationError("A budget for this category and month already exists.") from None


def update_budget(budget_id: int, amount) -> None:
    amount = validate_budget_amount(amount)
    with session_scope() as s:
        b = s.get(Budget, budget_id)
        if b is None:
            raise ValidationError("Budget not found.")
        b.amount = amount


def delete_budget(budget_id: int) -> None:
    with session_scope() as s:
        b = s.get(Budget, budget_id)
        if b is None:
            raise ValidationError("Budget not found.")
        s.delete(b)


def list_budgets(month: str | None = None) -> pd.DataFrame:
    stmt = (select(Budget.id, Budget.category_id, Category.name, Budget.month, Budget.amount)
            .select_from(Budget).join(Category, Category.id == Budget.category_id).order_by(Budget.month.desc(), Category.name))
    if month:
        stmt = stmt.where(Budget.month == validate_month(month))
    with session_scope() as s:
        rows = s.execute(stmt).all()
    return pd.DataFrame([tuple(r) for r in rows], columns=BUDGET_COLUMNS)


def get_budget_status(month: str) -> pd.DataFrame:
    """Budget amount, actual spending, remaining budget and usage % per category."""
    month = validate_month(month)
    first, last = month_bounds(month)
    budgets = list_budgets(month)
    tx = list_transactions(start=first, end=last, tx_type="Expense")
    return analytics.compute_budget_status(budgets, tx, month)
