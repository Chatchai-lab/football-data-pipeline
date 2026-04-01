"""
Tests für die Ingestion-Schicht (API-Calls & DB-Writes).
Nutzt Mocking, um weder echte API-Calls noch DB-Zugriffe auszuführen.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


# ═══════════════════════════════════════════════════════════════
#  Tests: ingest_bundesliga_teams()
# ═══════════════════════════════════════════════════════════════

class TestIngestTeams:
    """Testet src/ingestion/ingest_teams.py"""

    MOCK_API_RESPONSE = {
        "teams": [
            {
                "id": 1,
                "name": "FC Bayern München",
                "shortName": "Bayern",
                "tla": "FCB",
                "crest": "https://crests.football-data.org/5.png",
                "address": "Säbener Str. 51 München 81547",
            },
            {
                "id": 2,
                "name": "Borussia Dortmund",
                "shortName": "Dortmund",
                "tla": "BVB",
                "crest": "https://crests.football-data.org/4.png",
                "address": "Rheinlanddamm 207-209 Dortmund 44137",
            },
        ]
    }

    @patch("src.ingestion.ingest_teams.get_db_engine")
    @patch("src.ingestion.ingest_teams.requests.get")
    def test_successful_ingestion(self, mock_get, mock_engine):
        """Bei Status 200 werden Teams transformiert und in DB geschrieben."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_API_RESPONSE
        mock_get.return_value = mock_response

        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value = engine

        from src.ingestion.ingest_teams import ingest_bundesliga_teams

        with patch.object(pd.DataFrame, "to_sql"):
            count = ingest_bundesliga_teams()

        assert count == 2

    @patch("src.ingestion.ingest_teams.get_db_engine")
    @patch("src.ingestion.ingest_teams.requests.get")
    def test_api_error_returns_zero(self, mock_get, mock_engine):
        """Bei API-Fehler (z.B. 500) wird 0 zurückgegeben."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        from src.ingestion.ingest_teams import ingest_bundesliga_teams

        count = ingest_bundesliga_teams()
        assert count == 0

    @patch("src.ingestion.ingest_teams.get_db_engine")
    @patch("src.ingestion.ingest_teams.requests.get")
    def test_empty_teams_list(self, mock_get, mock_engine):
        """Bei leerer Team-Liste wird trotzdem korrekt verarbeitet."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"teams": []}
        mock_get.return_value = mock_response

        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value = engine

        from src.ingestion.ingest_teams import ingest_bundesliga_teams

        with patch.object(pd.DataFrame, "to_sql"):
            count = ingest_bundesliga_teams()

        assert count == 0


# ═══════════════════════════════════════════════════════════════
#  Tests: ingest_bundesliga_matches()
# ═══════════════════════════════════════════════════════════════

class TestIngestMatches:
    """Testet src/ingestion/ingest_matches.py"""

    MOCK_MATCH_RESPONSE = {
        "filters": {"season": "2025"},
        "matches": [
            {
                "id": 101,
                "utcDate": "2025-08-23T13:30:00Z",
                "status": "FINISHED",
                "matchday": 1,
                "homeTeam": {"id": 1, "name": "FC Bayern München"},
                "awayTeam": {"id": 2, "name": "Borussia Dortmund"},
                "score": {
                    "fullTime": {"home": 3, "away": 1},
                    "winner": "HOME_TEAM",
                },
            }
        ],
    }

    @patch("src.ingestion.ingest_matches.get_db_engine")
    @patch("src.ingestion.ingest_matches.requests.get")
    def test_successful_match_ingestion(self, mock_get, mock_engine):
        """Spiele werden korrekt geladen und Anzahl zurückgegeben."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.MOCK_MATCH_RESPONSE
        mock_get.return_value = mock_response

        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value = engine

        from src.ingestion.ingest_matches import ingest_bundesliga_matches

        with patch.object(pd.DataFrame, "to_sql"):
            count = ingest_bundesliga_matches(season=2025)

        assert count == 1

    @patch("src.ingestion.ingest_matches.get_db_engine")
    @patch("src.ingestion.ingest_matches.requests.get")
    def test_api_403_returns_zero(self, mock_get, mock_engine):
        """Bei 403 (Plan-Limit) wird 0 zurückgegeben."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        from src.ingestion.ingest_matches import ingest_bundesliga_matches

        count = ingest_bundesliga_matches(season=1990)
        assert count == 0

    @patch("src.ingestion.ingest_matches.requests.get")
    def test_get_available_seasons_success(self, mock_get):
        """get_available_seasons gibt nur zugängliche Saisons zurück."""
        # Erster Call: Competition-Info mit Saisons
        comp_response = MagicMock()
        comp_response.status_code = 200
        comp_response.json.return_value = {
            "seasons": [
                {"startDate": "2025-08-22"},
                {"startDate": "2024-08-23"},
                {"startDate": "2023-08-18"},
                {"startDate": "2022-08-05"},
            ]
        }

        # Saison-Checks: 2025 OK, 2024 OK, 2023 OK, 2022 Forbidden
        check_200 = MagicMock(status_code=200)
        check_403 = MagicMock(status_code=403)

        mock_get.side_effect = [comp_response, check_200, check_200, check_200, check_403]

        from src.ingestion.ingest_matches import get_available_seasons

        with patch.dict("os.environ", {"FOOTBALL_API_KEY": "test-key"}):
            seasons = get_available_seasons()

        assert seasons == [2025, 2024, 2023]

    @patch("src.ingestion.ingest_matches.requests.get")
    def test_get_available_seasons_api_error(self, mock_get):
        """Bei API-Fehler wird leere Liste zurückgegeben."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        from src.ingestion.ingest_matches import get_available_seasons

        with patch.dict("os.environ", {"FOOTBALL_API_KEY": "test-key"}):
            seasons = get_available_seasons()

        assert seasons == []
