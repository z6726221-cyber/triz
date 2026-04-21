import pytest
import os
from triz.database.init_db import init_database, ensure_data_dir
from triz.database.queries import get_parameter_by_id, query_parameters_by_similarity
from triz.config import DB_PATH


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_triz.db"
    monkeypatch.setattr("triz.config.DB_PATH", db_path)
    monkeypatch.setattr("triz.database.init_db.DB_PATH", db_path)
    monkeypatch.setattr("triz.database.queries.DB_PATH", db_path)
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)


def test_init_database_creates_tables(temp_db):
    assert temp_db.exists()


def test_get_parameter_by_id(temp_db):
    param = get_parameter_by_id(9)
    assert param is not None
    assert "Speed" in param["name"]


def test_get_parameter_by_id_not_found(temp_db):
    param = get_parameter_by_id(999)
    assert param is None


def test_query_parameters_by_similarity(temp_db):
    results = query_parameters_by_similarity("速度")
    assert len(results) > 0
    assert results[0]["id"] == 9
