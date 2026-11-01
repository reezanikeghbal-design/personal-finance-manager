"""Input validation helpers. Pure Python, no database access."""
from __future__ import annotations

import math
import re
from datetime import date, datetime

from config import MAX_AMOUNT, MAX_DESCRIPTION_LENGTH, MAX_NAME_LENGTH, TRANSACTION_TYPES


class ValidationError(ValueError):
    """Raised when user input is invalid. The message is safe to show to users."""


def validate_amount(value, field: str = "Amount") -> float:
    """Return a positive amount rounded to 2 decimals or raise ValidationError."""
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"{field} must be a number.")
    try:
        amount = float(str(value).replace(",", "").strip()) if isinstance(value, str) else float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.") from None
    if math.isnan(amount) or math.isinf(amount):
        raise ValidationError(f"{field} must be a finite number.")
    if amount <= 0:
        raise ValidationError(f"{field} must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValidationError(f"{field} is too large.")
    amount = round(amount, 2)
    if amount <= 0:
        raise ValidationError(f"{field} must be at least 0.01.")
    return amount


def validate_type(value) -> str:
    """Normalise a transaction type to 'Income' or 'Expense'."""
    if not isinstance(value, str):
        raise ValidationError("Transaction type must be Income or Expense.")
    for t in TRANSACTION_TYPES:
        if value.strip().lower() == t.lower():
            return t
    raise ValidationError("Transaction type must be Income or Expense.")


def validate_date(value, field: str = "Date") -> date:
    """Accept date, datetime or ISO string (YYYY-MM-DD)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass
    raise ValidationError(f"{field} must be a valid date (YYYY-MM-DD).")


def validate_month(value) -> str:
    """Return a month key like '2026-03' or raise ValidationError."""
    if isinstance(value, (date, datetime)):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value.strip()):
        return value.strip()
    raise ValidationError("Month must be in YYYY-MM format.")


def validate_name(value, field: str = "Name") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} cannot be empty.")
    name = " ".join(value.split())
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"{field} must be at most {MAX_NAME_LENGTH} characters.")
    return name


def validate_description(value) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("Description must be text.")
    text = value.strip()
    if len(text) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"Description must be at most {MAX_DESCRIPTION_LENGTH} characters.")
    return text


def validate_budget_amount(value) -> float:
    return validate_amount(value, "Budget amount")
