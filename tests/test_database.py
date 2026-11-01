from datetime import date
from pathlib import Path

import pytest

import config
from services import categories, sample_data, settings
from services import transactions as tx_svc
from utils.validators import ValidationError


def test_initialisation_creates_file_and_defaults(db, tmp_path):
    assert (tmp_path / "test.db").exists()
    assert len(categories.list_categories()) == 15


def test_isolation_from_real_database(db, tmp_path):
    assert db.get_db_path() == tmp_path / "test.db"
    assert Path(config.BASE_DIR / "data" / "finance.db") != db.get_db_path()


def test_data_persists_after_reconnect(db, tmp_path):
    cid = categories.list_categories("Expense")[0]["id"]
    tx_svc.add_transaction(42, "Expense", cid, date(2026, 3, 1), "persist me")
    db.reset_for_tests()
    db.configure(tmp_path / "test.db")
    df = tx_svc.list_transactions()
    assert len(df) == 1 and df.iloc[0]["description"] == "persist me"
    assert len(categories.list_categories()) == 15   # defaults not duplicated


def test_deleted_default_category_is_not_recreated(db, tmp_path):
    cid = next(c["id"] for c in categories.list_categories() if c["name"] == "Travel")
    categories.delete_category(cid)
    db.reset_for_tests()
    db.configure(tmp_path / "test.db")
    assert "Travel" not in {c["name"] for c in categories.list_categories()}


def test_settings_roundtrip(db):
    assert settings.get_currency() == "USD" and settings.get_theme() == "light"
    settings.set_currency("EUR")
    settings.set_theme("dark")
    assert settings.get_currency() == "EUR" and settings.get_theme() == "dark"
    with pytest.raises(ValidationError):
        settings.set_currency("JPY")


def test_sample_data_loads_once(db):
    n = sample_data.load_sample_data(today=date(2026, 6, 15))
    assert n > 50 and sample_data.is_loaded()
    df = tx_svc.list_transactions()
    assert len(df) == n and max(df["date"]) <= date(2026, 6, 15)
    with pytest.raises(ValidationError):
        sample_data.load_sample_data(today=date(2026, 6, 15))
    assert len(tx_svc.list_transactions()) == n


def test_backup_and_restore_roundtrip(db):
    cid = categories.list_categories("Expense")[0]["id"]
    tx_svc.add_transaction(10, "Expense", cid, date(2026, 3, 1), "keep")
    backup = db.backup_bytes()
    tx_svc.add_transaction(99, "Expense", cid, date(2026, 3, 2), "added after backup")
    safety = db.restore_from_bytes(backup, "backup.db")
    df = tx_svc.list_transactions()
    assert list(df["description"]) == ["keep"]
    assert safety.exists()


def test_restore_rejects_invalid_files(db):
    with pytest.raises(ValidationError):
        db.restore_from_bytes(b"", "x.db")
    with pytest.raises(ValidationError):
        db.restore_from_bytes(b"not a database at all", "x.db")
    with pytest.raises(ValidationError):
        db.restore_from_bytes(b"whatever", "x.txt")
    import sqlite3, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        other = Path(tmp) / "other.db"
        conn = sqlite3.connect(other)
        conn.execute("create table foo (id integer)")
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError):
            db.restore_from_bytes(other.read_bytes(), "other.db")
    assert len(categories.list_categories()) == 15   # current db untouched
