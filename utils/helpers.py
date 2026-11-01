"""Formatting and small date helpers. Pure Python."""
from __future__ import annotations

from datetime import date

from config import CURRENCIES, DEFAULT_CURRENCY


def format_currency(value, currency: str = DEFAULT_CURRENCY) -> str:
    """Format a number with the selected currency symbol (display only)."""
    symbol = CURRENCIES.get(currency, CURRENCIES[DEFAULT_CURRENCY])
    if value is None:
        return "N/A"
    value = float(value)
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.2f}"


def format_percent(value) -> str:
    return "N/A" if value is None else f"{float(value):.1f}%"


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_bounds(month: str) -> tuple[date, date]:
    """Return first and last day of a 'YYYY-MM' month."""
    year, mon = int(month[:4]), int(month[5:7])
    first = date(year, mon, 1)
    nxt = date(year + (mon == 12), (mon % 12) + 1, 1)
    last = date.fromordinal(nxt.toordinal() - 1)
    return first, last


def add_months(d: date, n: int) -> date:
    idx = d.year * 12 + (d.month - 1) + n
    return date(idx // 12, idx % 12 + 1, 1)
