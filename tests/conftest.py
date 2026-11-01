"""Test configuration: every test uses its own temporary database."""
import os
import sys
import tempfile
from pathlib import Path

# Make the project importable and make sure the real database is never touched.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PFM_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="pfm-tests-")) / "default-unused.db")

import pytest  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    """Fresh, isolated, seeded database for one test."""
    from database import db as database

    database.configure(tmp_path / "test.db")
    yield database
    database.reset_for_tests()


@pytest.fixture()
def cat():
    """Helper returning a category id by name."""
    from services import categories

    def _find(name):
        return next(c["id"] for c in categories.list_categories() if c["name"] == name)
    return _find
