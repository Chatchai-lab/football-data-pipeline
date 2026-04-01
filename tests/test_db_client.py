"""
Tests für den DB-Client (Engine-Erstellung, URL-Konstruktion).
Nutzt gemockte Umgebungsvariablen, keine echte DB nötig.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetDbEngine:
    """Testet src/utils/db_client.py – URL-Konstruktion und Fehlerbehandlung."""

    def _call_get_db_engine(self):
        """Hilfsmethode: Modul frisch laden und get_db_engine aufrufen."""
        import importlib
        import src.utils.db_client as db_module
        importlib.reload(db_module)
        return db_module.get_db_engine()

    def test_url_contains_credentials(self, mock_db_env):
        """Die DB-URL enthält User, Passwort, DB-Name und Port."""
        engine = self._call_get_db_engine()
        url_str = str(engine.url)
        assert "test_user" in url_str
        assert "test_db" in url_str
        assert "5433" in url_str

    def test_default_port_is_5433(self):
        """Ohne DB_PORT wird der Standardport 5433 verwendet."""
        env = {
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_NAME": "mydb",
            "DB_HOST": "localhost",
        }
        with patch.dict("os.environ", env, clear=False):
            engine = self._call_get_db_engine()
            assert "5433" in str(engine.url)

    def test_engine_returns_not_none(self, mock_db_env):
        """get_db_engine gibt ein Engine-Objekt zurück."""
        engine = self._call_get_db_engine()
        assert engine is not None

    def test_engine_returns_none_on_error(self, mock_db_env):
        """Bei einem Fehler in create_engine wird None zurückgegeben."""
        import importlib
        import src.utils.db_client as db_module

        original_create = db_module.create_engine
        db_module.create_engine = MagicMock(side_effect=Exception("fail"))
        try:
            engine = db_module.get_db_engine()
            assert engine is None
        finally:
            db_module.create_engine = original_create
