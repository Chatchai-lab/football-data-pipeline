"""
Shared pytest fixtures für alle Tests.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_engine():
    """Erstellt eine gemockte SQLAlchemy Engine mit Connection-Context."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    return engine, conn


@pytest.fixture
def mock_api_key():
    """Setzt einen Dummy-API-Key als Umgebungsvariable."""
    with patch.dict("os.environ", {"FOOTBALL_API_KEY": "test-key-12345"}):
        yield


@pytest.fixture
def mock_db_env():
    """Setzt alle DB-Umgebungsvariablen für Tests."""
    env = {
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "DB_NAME": "test_db",
        "DB_HOST": "localhost",
        "DB_PORT": "5433",
    }
    with patch.dict("os.environ", env):
        yield env
