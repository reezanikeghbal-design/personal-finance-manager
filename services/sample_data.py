"""Optional, deterministic sample data generator."""
from __future__ import annotations

import random
from datetime import date

from sqlalchemy import select

from database.db import session_scope
from database.models import AppSetting, Budget, Category, Transaction
from utils.helpers import add_months, month_bounds, month_key
from utils.validators import ValidationError

MARKER = "sample_data_loaded"

# (category, min, max, count per month, description choices)
_EXPENSES = [
    ("Housing", 1250, 1250, 1, ["Monthly rent"]),
    ("Utilities", 60, 140, 2, ["Electricity bill", "Internet", "Water bill"]),
    ("Food", 25, 95, 9, ["Grocery store", "Supermarket", "Restaurant dinner", "Lunch", "Bakery"]),
    ("Transportation", 12, 70, 3, ["Fuel", "Public transport pass", "Taxi"]),
    ("Healthcare", 20, 120, 1, ["Pharmacy", "Doctor visit"]),
    ("Shopping", 25, 180, 2, ["Clothing", "Home goods", "Online order"]),
    ("Entertainment", 10, 70, 3, ["Cinema", "Streaming subscription", "Concert"]),
    ("Education", 30, 90, 1, ["Online course", "Books"]),
    ("Travel", 80, 420, 1, ["Weekend trip", "Train tickets"]),
    ("Other Expenses", 10, 60, 1, ["Miscellaneous"]),
]
_BUDGETS = {"Housing": 1300, "Utilities": 220, "Food": 520, "Transportation": 180, "Healthcare": 120,
            "Shopping": 250, "Entertainment": 130, "Education": 100, "Travel": 300}


def is_loaded() -> bool:
    with session_scope() as s:
        return s.get(AppSetting, MARKER) is not None


def _category(session, name: str, tx_type: str) -> Category:
    cat = session.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
    if cat is None:
        cat = Category(name=name, type=tx_type, is_default=False)
        session.add(cat)
        session.flush()
    return cat


def load_sample_data(months: int = 6, today: date | None = None) -> int:
    """Insert ~6 months of realistic data. Returns the number of transactions added.

    Raises ValidationError if sample data was loaded before (no duplicates).
    """
    today = today or date.today()
    rng = random.Random(2024)
    added = 0
    with session_scope() as s:
        if s.get(AppSetting, MARKER) is not None:
            raise ValidationError("Sample data has already been loaded.")
        for offset in range(-(months - 1), 1):
            first = add_months(today.replace(day=1), offset)
            key = month_key(first)
            _, last = month_bounds(key)
            last_day = min(last, today)

            def day(n: int) -> date:
                return min(date(first.year, first.month, min(n, 28)), last_day)

            def put(cat_name, tx_type, amount, d, desc):
                nonlocal added
                if d > today:
                    return
                cat = _category(s, cat_name, tx_type)
                s.add(Transaction(amount=round(amount, 2), type=tx_type, category_id=cat.id,
                                  date=d, description=f"Sample: {desc}"))
                added += 1

            put("Salary", "Income", 4200, day(1), "Monthly salary")
            if offset % 2 == 0:
                put("Freelance", "Income", rng.randint(350, 900), day(14), "Freelance project")
            if offset % 3 == 0:
                put("Investment", "Income", rng.randint(60, 180), day(20), "Dividends")
            for cat_name, lo, hi, count, descs in _EXPENSES:
                for i in range(count):
                    amount = lo if lo == hi else rng.uniform(lo, hi)
                    d = day(1 + (i * 28 // max(count, 1)) + rng.randint(0, 2))
                    put(cat_name, "Expense", amount, d, rng.choice(descs))
            for cat_name, amount in _BUDGETS.items():
                cat = _category(s, cat_name, "Expense")
                has = s.execute(select(Budget.id).where(
                    Budget.category_id == cat.id, Budget.month == key)).first()
                if has is None:
                    s.add(Budget(category_id=cat.id, month=key, amount=float(amount)))
        s.add(AppSetting(key=MARKER, value="1"))
    return added
