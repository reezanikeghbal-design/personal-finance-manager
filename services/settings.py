"""Application settings stored in the database."""
from __future__ import annotations

import config
from database.db import session_scope
from database.models import AppSetting
from utils.validators import ValidationError


def get_setting(key: str, default: str | None = None) -> str | None:
    with session_scope() as s:
        row = s.get(AppSetting, key)
        return row.value if row else default


def set_setting(key: str, value: str) -> None:
    with session_scope() as s:
        row = s.get(AppSetting, key)
        if row:
            row.value = value
        else:
            s.add(AppSetting(key=key, value=value))


def get_currency() -> str:
    value = get_setting("currency", config.DEFAULT_CURRENCY)
    return value if value in config.CURRENCIES else config.DEFAULT_CURRENCY


def set_currency(code: str) -> None:
    if code not in config.CURRENCIES:
        raise ValidationError("Unsupported currency.")
    set_setting("currency", code)


def get_theme() -> str:
    value = get_setting("theme", config.DEFAULT_THEME)
    return value if value in config.THEMES else config.DEFAULT_THEME


def set_theme(theme: str) -> None:
    if theme not in config.THEMES:
        raise ValidationError("Unsupported theme.")
    set_setting("theme", theme)
