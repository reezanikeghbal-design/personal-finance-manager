"""Transaction management."""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import select

from database.db import session_scope
from database.models import Category, Transaction
from services.analytics import TX_COLUMNS, empty_transactions
from utils.validators import (ValidationError, validate_amount, validate_date,
                              validate_description, validate_type)

SORT_COLUMNS = {
    "date": Transaction.date, "amount": Transaction.amount, "type": Transaction.type,
    "category": Category.name, "description": Transaction.description,
    "created_at": Transaction.created_at, "id": Transaction.id,
}


def _validated(amount, tx_type, category_id, tx_date, description, session) -> dict:
    amount = validate_amount(amount)
    tx_type = validate_type(tx_type)
    tx_date = validate_date(tx_date)
    description = validate_description(description)
    cat = session.get(Category, category_id) if isinstance(category_id, int) else None
    if cat is None:
        raise ValidationError("Selected category does not exist.")
    if cat.type != tx_type:
        raise ValidationError(f"'{cat.name}' is an {cat.type.lower()} category and cannot be used for {tx_type.lower()} transactions.")
    return {"amount": amount, "type": tx_type, "category_id": cat.id,
            "date": tx_date, "description": description}


def add_transaction(amount, tx_type, category_id, tx_date, description: str = "") -> int:
    with session_scope() as s:
        tx = Transaction(**_validated(amount, tx_type, category_id, tx_date, description, s))
        s.add(tx)
        s.flush()
        return tx.id


def update_transaction(tx_id: int, amount, tx_type, category_id, tx_date, description: str = "") -> None:
    with session_scope() as s:
        tx = s.get(Transaction, tx_id)
        if tx is None:
            raise ValidationError("Transaction not found.")
        for key, value in _validated(amount, tx_type, category_id, tx_date, description, s).items():
            setattr(tx, key, value)


def delete_transaction(tx_id: int) -> None:
    with session_scope() as s:
        tx = s.get(Transaction, tx_id)
        if tx is None:
            raise ValidationError("Transaction not found.")
        s.delete(tx)


def get_transaction(tx_id: int) -> dict | None:
    with session_scope() as s:
        row = s.execute(select(Transaction, Category.name).select_from(Transaction)
                        .join(Category, Category.id == Transaction.category_id)
                        .where(Transaction.id == tx_id)).first()
        if row is None:
            return None
        tx, cat_name = row
        return {"id": tx.id, "amount": tx.amount, "type": tx.type, "category_id": tx.category_id,
                "category": cat_name, "date": tx.date, "description": tx.description,
                "created_at": tx.created_at}


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_transactions(start: date | None = None, end: date | None = None,
                      tx_type: str | None = None, category_ids: list[int] | None = None,
                      search: str | None = None, sort_by: str = "date",
                      ascending: bool = False) -> pd.DataFrame:
    """Return transactions as a DataFrame (columns: see analytics.TX_COLUMNS)."""
    stmt = select(Transaction.id, Transaction.date, Transaction.type, Category.name,
                  Transaction.amount, Transaction.description, Transaction.created_at
                  ).select_from(Transaction).join(Category, Category.id == Transaction.category_id)
    if start:
        stmt = stmt.where(Transaction.date >= start)
    if end:
        stmt = stmt.where(Transaction.date <= end)
    if tx_type:
        stmt = stmt.where(Transaction.type == validate_type(tx_type))
    if category_ids:
        stmt = stmt.where(Transaction.category_id.in_(category_ids))
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        stmt = stmt.where(Transaction.description.ilike(pattern, escape="\\")
                          | Category.name.ilike(pattern, escape="\\"))
    column = SORT_COLUMNS.get(sort_by, Transaction.date)
    order = column.asc() if ascending else column.desc()
    stmt = stmt.order_by(order, Transaction.id.desc())
    with session_scope() as s:
        rows = s.execute(stmt).all()
    if not rows:
        return empty_transactions()
    return pd.DataFrame([tuple(r) for r in rows], columns=TX_COLUMNS)
