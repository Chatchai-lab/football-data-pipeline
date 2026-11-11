"""Tests der REST-API ohne Datenbank.

Die Abhaengigkeit get_db wird durch eine Attrappe ersetzt (dependency_overrides).
Die Attrappe antwortet je nach Stichwort im SQL-Text mit vorbereiteten Zeilen.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.api.deps import get_db
from src.api.main import app


# --- Attrappe fuer die Datenbankverbindung ---------------------------------

class FakeMappings(list):
    def first(self):
        return self[0] if self else None

    def all(self):
        return list(self)


class FakeResult:
    """Ersetzt das Ergebnis von conn.execute(...) mit den Methoden, die die API nutzt."""

    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return SimpleNamespace(**self.rows[0])

    def scalar_one(self):
        return next(iter(self.rows[0].values()))

    def scalars(self):
        return SimpleNamespace(all=lambda: [next(iter(r.values())) for r in self.rows])

    def mappings(self):
        return FakeMappings(self.rows)


class FakeConnection:
    """Antwortet je nach Stichwort im SQL-Text und merkt sich alle Aufrufe."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        for keyword, rows in self.responses.items():
            if keyword in sql:
                return FakeResult(rows)
        return FakeResult([])


def broken_db():
    """Simuliert eine nicht erreichbare Datenbank."""
    raise OperationalError("SELECT 1", {}, Exception("Datenbank tot"))
    yield  # macht die Funktion zu einem Generator, wie get_db


# --- Fixtures --------------------------------------------------------------

@pytest.fixture
def api():
    """Gibt eine Funktion zurueck, die einen TestClient mit festen DB-Antworten baut."""

    def build(responses, season_exists=True):
        data = dict(responses)
        if season_exists:
            data["SELECT 1 FROM fct_standings"] = [{"one": 1}]
        fake = FakeConnection(data)
        app.dependency_overrides[get_db] = lambda: fake
        client = TestClient(app)
        client.fake = fake
        return client

    yield build
    app.dependency_overrides.clear()


@pytest.fixture
def dead_db():
    app.dependency_overrides[get_db] = broken_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Beispielzeilen --------------------------------------------------------

STANDING = {
    "team_name": "FC Test", "tla": "FCT", "matches_played": 9, "total_points": 21,
    "total_goals_for": 29, "total_goals_against": 9, "goal_diff": 20,
    "points_per_match": 2.33,
}
HOME_AWAY = {
    "team_name": "FC Test", "home_matches": 5, "home_points": 13, "home_goals_for": 10,
    "home_goals_against": 3, "home_wins": 4, "home_ppg": 2.6, "away_matches": 4,
    "away_points": 8, "away_goals_for": 6, "away_goals_against": 4, "away_wins": 2,
    "away_ppg": 2.0, "total_points": 21,
}
RATING = {
    "team_name": "FC Test", "total_games": 9, "goals_per_game": 3.22,
    "goals_conceded_per_game": 1.0, "clean_sheets": 2,
}
MATCH = {
    "matchday": 34, "match_timestamp": datetime(2027, 5, 22, 13, 30),
    "home_team_name": "FC Test", "away_team_name": "SV Beispiel",
    "goals_home": None, "goals_away": None, "status": "TIMED",
}


# --- Betrieb ---------------------------------------------------------------

def test_health_antwortet_bei_toter_datenbank(dead_db):
    response = dead_db.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_liefert_503_bei_toter_datenbank(dead_db):
    response = dead_db.get("/ready")
    assert response.status_code == 503


def test_ready_ok(api):
    response = api({}).get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


# --- Stammdaten ------------------------------------------------------------

def test_status(api):
    client = api(
        {
            "COUNT(DISTINCT season)": [
                {"last_update": datetime(2026, 11, 8, 18, 30), "match_count": 1224,
                 "season_count": 4}
            ],
            "SELECT COUNT(*) FROM dim_teams": [{"count": 18}],
        }
    )
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {
        "last_update": "2026-11-08T18:30:00",
        "match_count": 1224,
        "team_count": 18,
        "season_count": 4,
    }


def test_seasons(api):
    client = api({"SELECT DISTINCT season": [{"season": "2026"}, {"season": "2025"}]})
    assert client.get("/seasons").json() == ["2026", "2025"]


def test_teams(api):
    client = api({"SELECT DISTINCT team_name": [{"team_name": "A"}, {"team_name": "B"}]})
    response = client.get("/teams", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json() == ["A", "B"]


def test_team_meta(api):
    rows = [{"team_name": "FC Test", "tla": "FCT", "crest_url": "https://example.org/fct.png"}]
    client = api({"SELECT team_name, tla, crest_url FROM dim_teams": rows})
    response = client.get("/team-meta")
    assert response.status_code == 200
    assert response.json() == rows


# --- Gold-Views ------------------------------------------------------------

def test_standings(api):
    client = api({"total_goals_for": [STANDING]})
    response = client.get("/standings", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json()[0]["team_name"] == "FC Test"
    assert response.json()[0]["total_points"] == 21


def test_season_trend_ohne_filter(api):
    rows = [{"team_name": "FC Test", "matchday": 1, "cumulative_points": 3}]
    client = api({"fct_season_trend": rows})
    response = client.get("/season-trend", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json() == rows
    assert "teams" not in client.fake.calls[-1][1]


def test_season_trend_mit_teamfilter(api):
    rows = [{"team_name": "FC Test", "matchday": 1, "cumulative_points": 3}]
    client = api({"fct_season_trend": rows})
    response = client.get("/season-trend", params={"season": "2026", "team": ["FC Test"]})
    assert response.status_code == 200
    assert client.fake.calls[-1][1]["teams"] == ["FC Test"]


def test_season_trend_unbekanntes_team_liefert_404(api):
    client = api({"fct_season_trend": []})
    response = client.get("/season-trend", params={"season": "2026", "team": ["FC Phantasie"]})
    assert response.status_code == 404


def test_team_form(api):
    rows = [{"team_name": "FC Test", "tla": "FCT", "form_trend": "W-W-D-L-W"}]
    client = api({"tla, form_trend FROM fct_team_form": rows})
    response = client.get("/team-form", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json() == rows


def test_team_form_unbekanntes_team_liefert_404(api):
    client = api({"tla, form_trend FROM fct_team_form": []})
    response = client.get("/team-form", params={"season": "2026", "team": ["FC Phantasie"]})
    assert response.status_code == 404


def test_home_away(api):
    client = api({"home_matches": [HOME_AWAY]})
    response = client.get("/home-away", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json()[0]["home_ppg"] == 2.6


def test_ratings(api):
    client = api({"total_games": [RATING]})
    response = client.get("/ratings", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json()[0]["clean_sheets"] == 2


def test_matches(api):
    client = api({"FROM stg_matches WHERE season": [MATCH]})
    response = client.get("/matches", params={"season": "2026"})
    assert response.status_code == 200
    body = response.json()[0]
    assert body["status"] == "TIMED"
    assert body["goals_home"] is None
    assert body["match_timestamp"] == "2027-05-22T13:30:00"


def test_highlights(api):
    client = api(
        {
            "SELECT team_name, total_points FROM fct_standings": [
                {"team_name": "A", "total_points": 21}],
            "SELECT team_name, home_points FROM fct_home_away_stats": [
                {"team_name": "B", "home_points": 15}],
            "SELECT team_name, goals_per_game FROM fct_team_ratings": [
                {"team_name": "C", "goals_per_game": 3.22}],
            "SELECT team_name, form_trend FROM fct_team_form": [
                {"team_name": "D", "form_trend": "W-W-W-W-W"}],
        }
    )
    response = client.get("/highlights", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json() == {
        "leader": {"team_name": "A", "total_points": 21},
        "home_king": {"team_name": "B", "home_points": 15},
        "attack_king": {"team_name": "C", "goals_per_game": 3.22},
        "form_king": {"team_name": "D", "form_trend": "W-W-W-W-W"},
    }


def test_highlights_ohne_daten_liefert_null_felder(api):
    response = api({}).get("/highlights", params={"season": "2026"})
    assert response.status_code == 200
    assert response.json() == {
        "leader": None, "home_king": None, "attack_king": None, "form_king": None,
    }


# --- Fehlerbehandlung fuer alle Endpoints mit Saison -----------------------

SEASON_ENDPOINTS = [
    "/teams", "/standings", "/season-trend", "/team-form",
    "/home-away", "/ratings", "/matches", "/highlights",
]


@pytest.mark.parametrize("path", SEASON_ENDPOINTS)
def test_unbekannte_saison_liefert_404(api, path):
    client = api({}, season_exists=False)
    assert client.get(path, params={"season": "1999"}).status_code == 404


@pytest.mark.parametrize("path", SEASON_ENDPOINTS)
def test_ungueltige_saison_liefert_422(api, path):
    client = api({})
    assert client.get(path, params={"season": "abc"}).status_code == 422
    assert client.get(path).status_code == 422


def test_sql_injection_erreicht_die_datenbank_nicht(api):
    client = api({})
    response = client.get("/teams", params={"season": "1;DROP TABLE x"})
    assert response.status_code == 422
    assert client.fake.calls == []
