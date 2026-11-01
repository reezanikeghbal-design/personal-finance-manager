"""Category management."""
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from database.db import session_scope
from database.models import Budget, Category, Transaction
from utils.validators import ValidationError, validate_name, validate_type


def _to_dict(c: Category, usage: int = 0) -> dict:
    return {"id": c.id, "name": c.name, "type": c.type, "is_default": c.is_default, "usage": usage}


def list_categories(tx_type: str | None = None) -> list[dict]:
    """All categories (optionally one type) with number of linked transactions."""
    with session_scope() as s:
        stmt = (select(Category, func.count(Transaction.id))
                .outerjoin(Transaction, Transaction.category_id == Category.id)
                .group_by(Category.id).order_by(Category.type.desc(), Category.name))
        if tx_type:
            stmt = stmt.where(Category.type == validate_type(tx_type))
        return [_to_dict(c, n) for c, n in s.execute(stmt).all()]


def get_category(category_id: int) -> dict | None:
    with session_scope() as s:
        c = s.get(Category, category_id)
        return _to_dict(c) if c else None


def _name_taken(session, name: str, exclude_id: int | None = None) -> bool:
    stmt = select(Category.id).where(func.lower(Category.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    return session.execute(stmt).first() is not None


def create_category(name: str, tx_type: str) -> int:
    name, tx_type = validate_name(name, "Category name"), validate_type(tx_type)
    try:
        with session_scope() as s:
            if _name_taken(s, name):
                raise ValidationError(f"A category named '{name}' already exists.")
            cat = Category(name=name, type=tx_type, is_default=False)
            s.add(cat)
            s.flush()
            return cat.id
    except IntegrityError:
        raise ValidationError(f"A category named '{name}' already exists.") from None


def rename_category(category_id: int, new_name: str) -> None:
    new_name = validate_name(new_name, "Category name")
    try:
        with session_scope() as s:
            cat = s.get(Category, category_id)
            if cat is None:
                raise ValidationError("Category not found.")
            if _name_taken(s, new_name, exclude_id=category_id):
                raise ValidationError(f"A category named '{new_name}' already exists.")
            cat.name = new_name
    except IntegrityError:
        raise ValidationError(f"A category named '{new_name}' already exists.") from None


def delete_category(category_id: int, reassign_to: int | None = None) -> int:
    """Delete a category. Returns the number of transactions that were reassigned.

    A category that still has transactions can only be deleted when a replacement
    category of the same type is given; its transactions are moved first.
    Budgets of the deleted category are removed with it.
    """
    with session_scope() as s:
        cat = s.get(Category, category_id)
        if cat is None:
            raise ValidationError("Category not found.")
        count = s.execute(select(func.count(Transaction.id))
                          .where(Transaction.category_id == category_id)).scalar_one()
        moved = 0
        if count:
            if reassign_to is None:
                raise ValidationError(
                    f"'{cat.name}' is used by {count} transaction(s). Choose a category to reassign them to.")
            target = s.get(Category, reassign_to)
            if target is None or target.id == category_id:
                raise ValidationError("Choose a different, existing category for reassignment.")
            if target.type != cat.type:
                raise ValidationError("Transactions can only be reassigned to a category of the same type.")
            s.execute(update(Transaction).where(Transaction.category_id == category_id)
                      .values(category_id=target.id))
            moved = count
        for b in s.execute(select(Budget).where(Budget.category_id == category_id)).scalars().all():
            s.delete(b)
        s.flush()
        s.delete(cat)
        return moved
