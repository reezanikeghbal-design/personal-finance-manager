"""Database engine, sessions, backup and restore."""
from __future__ import annotations

import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

import config
from database.models import AppSetting, Base, Category
from utils.validators import ValidationError

_engine: Engine | None = None
_session_factory: sessionmaker | None = None
_db_path: Path | None = None

SQLITE_HEADER = b"SQLite format 3\x00"
REQUIRED_SCHEMA = {
    "categories": {"id", "name", "type", "is_default"},
    "transactions": {"id", "amount", "type", "category_id", "date", "description", "created_at"},
    "budgets": {"id", "category_id", "month", "amount"},
    "app_settings": {"key", "value"},
}


def configure(db_path: str | Path | None = None) -> Engine:
    """Point the application at a database file, creating and seeding it if needed."""
    global _engine, _session_factory, _db_path
    path = Path(db_path) if db_path else Path(config.DB_PATH)
    if _engine is not None and _db_path == path:
        return _engine
    if _engine is not None:
        _engine.dispose()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(path)))

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _record):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    _engine, _db_path = engine, path
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    _seed_defaults()
    return engine


def init_db() -> Engine:
    """Initialise the default database (idempotent)."""
    return configure(None) if _engine is None else _engine


def get_db_path() -> Path:
    init_db()
    return _db_path  # type: ignore[return-value]


def get_engine() -> Engine:
    return init_db()


@contextmanager
def session_scope():
    """Transactional scope: commit on success, rollback on any error."""
    init_db()
    session: Session = _session_factory()  # type: ignore[misc]
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_defaults() -> None:
    """Create default categories once. Deleted defaults are not recreated."""
    with session_scope() as s:
        flag = s.get(AppSetting, "defaults_seeded")
        if flag is not None:
            return
        for names, tx_type in ((config.DEFAULT_INCOME_CATEGORIES, "Income"),
                               (config.DEFAULT_EXPENSE_CATEGORIES, "Expense")):
            for name in names:
                exists = s.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
                if exists is None:
                    s.add(Category(name=name, type=tx_type, is_default=True))
        s.add(AppSetting(key="defaults_seeded", value="1"))


# ---------------------------------------------------------------- backup / restore
def backup_bytes() -> bytes:
    """Return a consistent copy of the database file (uses SQLite's backup API)."""
    path = get_db_path()
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "backup.db"
        src = sqlite3.connect(str(path))
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return dest.read_bytes()


def backup_filename() -> str:
    return f"finance-backup-{datetime.now():%Y%m%d-%H%M%S}.db"


def validate_backup_file(path: Path) -> None:
    """Raise ValidationError unless `path` is a healthy database with the expected schema."""
    try:
        with open(path, "rb") as fh:
            header = fh.read(len(SQLITE_HEADER))
    except OSError:
        raise ValidationError("The uploaded file could not be read.") from None
    if header != SQLITE_HEADER:
        raise ValidationError("This is not a valid SQLite database file.")
    try:
        conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValidationError("The database failed its integrity check.")
            for table, columns in REQUIRED_SCHEMA.items():
                found = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                if not columns.issubset(found):
                    raise ValidationError(
                        f"The database is not a Personal Finance Manager backup (table '{table}' is missing or incomplete).")
        finally:
            conn.close()
    except sqlite3.Error:
        raise ValidationError("The file is not a readable database.") from None


def restore_from_bytes(data: bytes, filename: str = "") -> Path:
    """Validate and restore an uploaded backup. Returns the path of the safety copy.

    The current database is copied to data/backups/ before it is replaced.
    """
    if filename and Path(filename).suffix.lower() not in (".db", ".sqlite", ".sqlite3"):
        raise ValidationError("Only .db, .sqlite or .sqlite3 files can be restored.")
    if not data:
        raise ValidationError("The uploaded file is empty.")
    if len(data) > config.MAX_RESTORE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File is larger than {config.MAX_RESTORE_SIZE_MB} MB.")

    current = get_db_path()
    current.parent.mkdir(parents=True, exist_ok=True)
    staged = current.with_name(current.name + ".restore.tmp")
    try:
        staged.write_bytes(data)
        validate_backup_file(staged)

        safety_dir = current.parent / "backups"
        safety_dir.mkdir(exist_ok=True)
        safety_copy = safety_dir / f"pre-restore-{datetime.now():%Y%m%d-%H%M%S}.db"
        safety_copy.write_bytes(backup_bytes())

        global _engine, _session_factory, _db_path
        if _engine is not None:
            _engine.dispose()
        _engine = _session_factory = _db_path = None
        staged.replace(current)
    finally:
        if staged.exists():
            staged.unlink()
    configure(current)
    return safety_copy


def reset_for_tests() -> None:
    """Dispose the active engine (used by the test-suite)."""
    global _engine, _session_factory, _db_path
    if _engine is not None:
        _engine.dispose()
    _engine = _session_factory = _db_path = None
