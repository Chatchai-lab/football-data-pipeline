"""Tests für die Daten-Lade-Schicht (data_loaders.py) in beiden Betriebsarten.

Mit API_URL holt die Schicht ihre Daten vom API-Client, ohne API_URL direkt aus der
Datenbank. Beide Wege werden ohne Netzwerk und ohne Datenbank getestet.
"""

import importlib
from unittest.mock import patch

import pandas as pd
import pytest

from src.utils.api_client import ApiError, ApiNotFound


def _no_cache(*args, **kwargs):
    """Ersatz für st.cache_data: unterstützt @st.cache_data und @st.cache_data(ttl=...)."""
    if args and callable(args[0]):
        return args[0]
    return lambda f: f


class Stopped(Exception):
    """Ersetzt st.stop(), das ausserhalb von Streamlit nichts sinnvolles tut."""


@pytest.fixture
def dl():
    """Das Modul data_loaders ohne Streamlit-Cache, damit Tests unabhängig voneinander sind."""
    with patch("streamlit.cache_data", _no_cache):
        import src.utils.data_loaders as module

        importlib.reload(module)
        yield module
    importlib.reload(module)


@pytest.fixture
def api_mode(monkeypatch):
    monkeypatch.setenv("API_URL", "http://api:8000")


@pytest.fixture
def db_mode(monkeypatch):
    monkeypatch.delenv("API_URL", raising=False)


TEAM_META = [
    {"team_name": "FC Test", "tla": "FCT", "crest_url": "https://example.org/fct.png"},
    {"team_name": "SV Beispiel", "tla": "SVB", "crest_url": "https://example.org/svb.png"},
]


def use_api(monkeypatch, dl, **functions):
    """Ersetzt Funktionen des API-Clients, wie dl sie aufruft."""
    for name, function in functions.items():
        monkeypatch.setattr(dl.api_client, name, function)


# --- Betriebsart Datenbank (ohne API_URL) ----------------------------------

def test_team_crests_ohne_api_aus_der_datenbank(dl, db_mode, monkeypatch):
    """get_team_crests gibt ein Dict {team_name: crest_url} zurück."""
    fake = pd.DataFrame({
        "team_name": ["FC Bayern", "Borussia Dortmund"],
        "crest_url": ["https://bayern.png", "https://bvb.png"],
        "tla": ["FCB", "BVB"],
    })
    monkeypatch.setattr(dl, "_read_sql", lambda query, params=None: fake)

    result = dl.get_team_crests()

    assert isinstance(result, dict)
    assert result["FC Bayern"] == "https://bayern.png"
    assert result["Borussia Dortmund"] == "https://bvb.png"


def test_ohne_api_url_wird_die_api_nie_aufgerufen(dl, db_mode, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Die API darf ohne API_URL nicht benutzt werden")

    use_api(monkeypatch, dl, seasons=forbidden, teams=forbidden)
    seen = {}

    def fake_read_sql(query, params=None):
        seen["query"] = query
        return pd.DataFrame({"season": ["2026", "2025"]})

    monkeypatch.setattr(dl, "_read_sql", fake_read_sql)

    assert dl.get_seasons() == ["2026", "2025"]
    assert "fct_standings" in seen["query"]


def test_ratings_ohne_api_berechnen_performance_score(dl, db_mode, monkeypatch):
    fake = pd.DataFrame({"team_name": ["A"], "goals_per_game": [3.0], "goals_conceded_per_game": [1.0]})
    monkeypatch.setattr(dl, "_read_sql", lambda query, params=None: fake)
    assert dl.get_ratings("2026")["performance_score"].iloc[0] == 2.0


# --- Betriebsart API -------------------------------------------------------

def test_seasons_und_teams_aus_der_api(dl, api_mode, monkeypatch):
    use_api(monkeypatch, dl, seasons=lambda: ["2026"], teams=lambda season: ["A", "B"])
    assert dl.get_seasons() == ["2026"]
    assert dl.get_teams("2026") == ["A", "B"]


def test_team_crests_und_team_info_aus_der_api(dl, api_mode, monkeypatch):
    use_api(monkeypatch, dl, team_meta=lambda: TEAM_META)
    assert dl.get_team_crests() == {
        "FC Test": "https://example.org/fct.png",
        "SV Beispiel": "https://example.org/svb.png",
    }
    info = dl.get_team_info("FC Test")
    assert list(info.columns) == ["team_name", "crest_url", "tla"]
    assert info.iloc[0]["tla"] == "FCT"
    assert dl.get_team_info("FC Phantasie").empty


def test_standings_haben_saison_und_wappen(dl, api_mode, monkeypatch):
    rows = [{
        "team_name": "FC Test", "tla": "FCT", "matches_played": 9, "total_points": 21,
        "total_goals_for": 29, "total_goals_against": 9, "goal_diff": 20,
        "points_per_match": 2.33,
    }]
    use_api(monkeypatch, dl, standings=lambda season: rows, team_meta=lambda: TEAM_META)
    df = dl.get_standings("2026")
    assert df.iloc[0]["season"] == "2026"
    assert df.iloc[0]["crest_url"] == "https://example.org/fct.png"
    assert df.iloc[0]["total_points"] == 21


def test_season_trends_sind_nach_spieltag_sortiert(dl, api_mode, monkeypatch):
    rows = [
        {"team_name": "A", "matchday": 2, "cumulative_points": 4},
        {"team_name": "A", "matchday": 1, "cumulative_points": 3},
        {"team_name": "B", "matchday": 1, "cumulative_points": 0},
    ]
    use_api(monkeypatch, dl, season_trend=lambda season, team=None: rows)
    df = dl.get_season_trends("2026")
    assert list(df.columns) == ["matchday", "team_name", "cumulative_points"]
    assert df["matchday"].tolist() == [1, 1, 2]


def test_home_away_hat_wappen_und_kuerzel(dl, api_mode, monkeypatch):
    rows = [{"team_name": "FC Test", "home_matches": 5, "home_points": 13, "home_goals_for": 10,
             "home_goals_against": 3, "home_wins": 4, "home_ppg": 2.6, "away_matches": 4,
             "away_points": 8, "away_goals_for": 6, "away_goals_against": 4, "away_wins": 2,
             "away_ppg": 2.0, "total_points": 21}]
    use_api(monkeypatch, dl, home_away=lambda season: rows, team_meta=lambda: TEAM_META)
    df = dl.get_home_away("2026")
    assert df.iloc[0]["tla"] == "FCT"
    assert df.iloc[0]["crest_url"] == "https://example.org/fct.png"
    assert df.iloc[0]["season"] == "2026"


def test_ratings_aus_der_api_haben_performance_score(dl, api_mode, monkeypatch):
    rows = [{"team_name": "A", "total_games": 9, "goals_per_game": 3.0,
             "goals_conceded_per_game": 1.0, "clean_sheets": 2}]
    use_api(monkeypatch, dl, ratings=lambda season: rows)
    assert dl.get_ratings("2026")["performance_score"].iloc[0] == 2.0


def test_team_details_filtern_auf_das_team(dl, api_mode, monkeypatch):
    ratings = [
        {"team_name": "A", "total_games": 9, "goals_per_game": 3.0,
         "goals_conceded_per_game": 1.0, "clean_sheets": 2},
        {"team_name": "B", "total_games": 9, "goals_per_game": 1.0,
         "goals_conceded_per_game": 2.0, "clean_sheets": 0},
    ]
    use_api(
        monkeypatch, dl,
        team_form=lambda season, team=None: [{"team_name": "A", "tla": "A", "form_trend": "W-W-D-L-W"}],
        season_trend=lambda season, team=None: [{"team_name": "A", "matchday": 1, "cumulative_points": 3}],
        ratings=lambda season: ratings,
        home_away=lambda season: [],
    )
    form, rat, trends, home_away = dl.get_team_details("A", "2026")
    assert form.iloc[0]["form_trend"] == "W-W-D-L-W"
    assert rat["team_name"].tolist() == ["A"]
    assert trends.iloc[0]["cumulative_points"] == 3
    assert home_away.empty


def test_team_details_ohne_daten_liefern_leere_frames(dl, api_mode, monkeypatch):
    def not_found(season, team=None):
        raise ApiNotFound("Keine Daten fuer diese Teams")

    use_api(monkeypatch, dl, team_form=not_found, season_trend=not_found,
            ratings=lambda season: [], home_away=lambda season: [])
    form, ratings, trends, home_away = dl.get_team_details("FC Phantasie", "2026")
    assert form.empty and ratings.empty and trends.empty and home_away.empty
    assert list(form.columns) == ["form_trend"]


def test_highlights_sind_vier_dataframes(dl, api_mode, monkeypatch):
    use_api(monkeypatch, dl, highlights=lambda season: {
        "leader": {"team_name": "A", "total_points": 21},
        "home_king": {"team_name": "B", "home_points": 15},
        "attack_king": {"team_name": "C", "goals_per_game": 3.22},
        "form_king": None,
    })
    leader, home, attack, form = dl.get_league_highlights("2026")
    assert leader.iloc[0]["total_points"] == 21
    assert home.iloc[0]["team_name"] == "B"
    assert attack.iloc[0]["goals_per_game"] == 3.22
    assert form.empty
    assert list(form.columns) == ["team_name", "form_trend"]


def test_spielplan_hat_datum_und_uhrzeit(dl, api_mode, monkeypatch):
    rows = [{"matchday": 34, "match_timestamp": "2027-05-22T13:30:00",
             "home_team_name": "FC Test", "away_team_name": "SV Beispiel",
             "goals_home": None, "goals_away": None, "status": "TIMED"}]
    use_api(monkeypatch, dl, matches=lambda season: rows)
    df = dl.get_match_schedule("2026")
    assert str(df.iloc[0]["match_date"]) == "2027-05-22"
    assert df.iloc[0]["match_time"] == "13:30"
    assert pd.isna(df.iloc[0]["goals_home"])


def test_leerer_spielplan_hat_die_erwarteten_spalten(dl, api_mode, monkeypatch):
    use_api(monkeypatch, dl, matches=lambda season: [])
    df = dl.get_match_schedule("2026")
    assert df.empty
    assert {"match_date", "match_time", "matchday"} <= set(df.columns)


def test_status_aus_der_api(dl, api_mode, monkeypatch):
    use_api(monkeypatch, dl, status=lambda: {
        "last_update": "2026-11-08T18:30:00", "match_count": 1224,
        "team_count": 18, "season_count": 4,
    })
    assert dl.get_db_status() == {
        "last_update": "08.11.2026 18:30", "match_count": 1224,
        "team_count": 18, "season_count": 4, "db_online": True,
    }


def test_status_meldet_offline_wenn_die_api_fehlt(dl, api_mode, monkeypatch):
    def down():
        raise ApiError("nicht erreichbar")

    use_api(monkeypatch, dl, status=down)
    status = dl.get_db_status()
    assert status["db_online"] is False
    assert status["last_update"] is None


def test_api_fehler_zeigt_meldung_statt_stacktrace(dl, api_mode, monkeypatch):
    def down(season):
        raise ApiError("Die API unter http://api:8000 ist nicht erreichbar.")

    use_api(monkeypatch, dl, standings=down)
    with patch("streamlit.error") as show_error, \
         patch("streamlit.caption"), \
         patch("streamlit.stop", side_effect=Stopped):
        with pytest.raises(Stopped):
            dl.get_standings("2026")
    assert "nicht erreichbar" in show_error.call_args[0][0]
