import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.validators import (ValidationError, validate_amount, validate_date, validate_month,  # noqa: E402
                              validate_name, validate_type)


def fails(fn, *args):
    try:
        fn(*args)
    except ValidationError:
        return True
    return False


def test_amount_accepts_valid_values():
    assert validate_amount(12.345) == 12.35 or validate_amount(12.345) == 12.34
    assert validate_amount("1,250.50") == 1250.5
    assert validate_amount(5) == 5.0


def test_amount_rejects_invalid_values():
    for bad in (0, -1, "abc", None, True, float("nan"), float("inf"), 0.001, 10 ** 15):
        assert fails(validate_amount, bad), bad


def test_type_and_date():
    assert validate_type("income") == "Income"
    assert fails(validate_type, "transfer")
    assert validate_date("2026-02-28") == date(2026, 2, 28)
    assert fails(validate_date, "2026-02-30")
    assert fails(validate_date, "not a date")


def test_month_and_name():
    assert validate_month("2026-03") == "2026-03"
    assert fails(validate_month, "2026-13")
    assert validate_name("  Pet   Care ") == "Pet Care"
    assert fails(validate_name, "   ")
    assert fails(validate_name, "x" * 51)
