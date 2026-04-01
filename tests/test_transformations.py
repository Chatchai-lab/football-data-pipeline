"""
Tests für die Transformations-Schicht (SQL-Layer-Ausführung).
Prüft, dass SQL-Dateien korrekt gelesen und ausgeführt werden.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, mock_open, call
from sqlalchemy import text


class TestRunSqlFile:
    """Testet run_sql_file() – einzelne SQL-Datei ausführen."""

    def test_executes_simple_query(self, tmp_path):
        """Einfache SQL-Datei wird gelesen und auf der Connection ausgeführt."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE test (id INT);")

        conn = MagicMock()

        from src.transformation.run_transformations import run_sql_file
        run_sql_file(conn, str(sql_file))

        conn.execute.assert_called_once()

    def test_drops_view_before_recreating(self, tmp_path):
        """Bei CREATE OR REPLACE VIEW wird zuerst DROP VIEW ausgeführt."""
        sql_content = "CREATE OR REPLACE VIEW my_view AS SELECT 1;"
        sql_file = tmp_path / "view.sql"
        sql_file.write_text(sql_content)

        conn = MagicMock()

        from src.transformation.run_transformations import run_sql_file
        run_sql_file(conn, str(sql_file))

        # Zwei Calls: DROP + CREATE
        assert conn.execute.call_count == 2
        # Prüfe den SQL-Text des ersten Calls (DROP VIEW)
        first_call_arg = conn.execute.call_args_list[0][0][0]
        assert "DROP VIEW IF EXISTS" in str(first_call_arg.text)

    def test_no_drop_for_non_view(self, tmp_path):
        """Normale Queries (kein VIEW) lösen kein DROP aus."""
        sql_file = tmp_path / "table.sql"
        sql_file.write_text("INSERT INTO teams VALUES (1, 'Bayern');")

        conn = MagicMock()

        from src.transformation.run_transformations import run_sql_file
        run_sql_file(conn, str(sql_file))

        assert conn.execute.call_count == 1


class TestTransformData:
    """Testet transform_data() – kompletter Layer-Durchlauf."""

    @patch("src.transformation.run_transformations.get_db_engine")
    @patch("src.transformation.run_transformations.run_sql_file")
    @patch("os.path.exists", return_value=True)
    def test_all_layers_executed(self, mock_exists, mock_run_sql, mock_engine):
        """Alle 9 SQL-Dateien werden in der richtigen Reihenfolge ausgeführt."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value = engine

        from src.transformation.run_transformations import transform_data
        transform_data()

        # 2 Staging + 2 Core + 5 Gold = 9 SQL-Dateien
        assert mock_run_sql.call_count == 9
        conn.commit.assert_called_once()

    @patch("src.transformation.run_transformations.get_db_engine")
    @patch("src.transformation.run_transformations.run_sql_file")
    @patch("os.path.exists", return_value=True)
    def test_layer_order_is_correct(self, mock_exists, mock_run_sql, mock_engine):
        """Staging wird vor Core ausgeführt, Core vor Gold."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value = engine

        from src.transformation.run_transformations import transform_data
        transform_data()

        called_files = [
            os.path.basename(call.args[1]) for call in mock_run_sql.call_args_list
        ]
        # Staging-Dateien vor Core-Dateien
        assert called_files.index("stg_matches.sql") < called_files.index("dim_teams.sql")
        # Core-Dateien vor Gold-Dateien
        assert called_files.index("fact_matches.sql") < called_files.index("fct_standings.sql")

    @patch("src.transformation.run_transformations.get_db_engine")
    @patch("src.transformation.run_transformations.run_sql_file")
    @patch("os.path.exists", return_value=False)
    def test_missing_files_are_skipped(self, mock_exists, mock_run_sql, mock_engine):
        """Fehlende SQL-Dateien werden übersprungen (kein Crash)."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value = engine

        from src.transformation.run_transformations import transform_data
        transform_data()

        mock_run_sql.assert_not_called()
