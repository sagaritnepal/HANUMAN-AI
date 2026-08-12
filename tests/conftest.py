import pytest

from app import config


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Point every module's sqlite connection at a fresh per-test file."""
    db_path = tmp_path / "test_leads.db"
    monkeypatch.setattr(config, "LEADS_DB_PATH", str(db_path))
    monkeypatch.setattr(config, "ADMIN_API_KEY", "test-admin-key")
    yield db_path
