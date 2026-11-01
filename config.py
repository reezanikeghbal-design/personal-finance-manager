"""Application configuration."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# The database location can be overridden with PFM_DB_PATH (used by tests).
DB_PATH = Path(os.environ.get("PFM_DB_PATH", DATA_DIR / "finance.db"))

APP_NAME = "Personal Finance Manager"

# Currency selection only changes display formatting. No conversion is done.
CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£"}
DEFAULT_CURRENCY = "USD"
DEFAULT_THEME = "light"
THEMES = ("light", "dark")

TRANSACTION_TYPES = ("Income", "Expense")

DEFAULT_INCOME_CATEGORIES = [
    "Salary", "Freelance", "Investment", "Business", "Other Income",
]
DEFAULT_EXPENSE_CATEGORIES = [
    "Housing", "Food", "Transportation", "Healthcare", "Shopping",
    "Entertainment", "Education", "Utilities", "Travel", "Other Expenses",
]

MAX_AMOUNT = 1_000_000_000_000.0
MAX_NAME_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500
MAX_RESTORE_SIZE_MB = 100
