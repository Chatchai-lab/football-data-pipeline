"""
Zentrale Daten-Lade-Schicht für die Matchlytics-App.

Alle Seiten holen ihre Daten ausschließlich über diese Funktionen. Es gibt zwei Betriebsarten:

  - API_URL gesetzt:       Die Daten kommen von der Matchlytics-API (Kubernetes-Cluster).
  - API_URL nicht gesetzt: Die Daten kommen wie bisher direkt aus der Datenbank
                           (Produktion auf Render mit Neon).

Die Funktionen liefern in beiden Betriebsarten dieselben Spalten und Typen, damit sich
die Seiten nicht um die Herkunft der Daten kümmern müssen.
"""

import functools
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from src.utils import api_client
from src.utils.api_client import ApiError, ApiNotFound

# Wie lange Ergebnisse zwischengespeichert werden. Die Pipeline läuft nachts,
# nach höchstens fünf Minuten sind neue Daten auf dem Bildschirm.
CACHE_TTL = 300

TEAM_META_COLUMNS = ["team_name", "crest_url", "tla"]
STANDING_COLUMNS = [
    "season", "team_name", "tla", "matches_played", "total_points", "total_goals_for",
    "total_goals_against", "goal_diff", "points_per_match",
]
HOME_AWAY_COLUMNS = [
    "team_name", "season", "home_matches", "home_points", "home_goals_for",
    "home_goals_against", "home_wins", "home_ppg", "away_matches", "away_points",
    "away_goals_for", "away_goals_against", "away_wins", "away_ppg", "total_points",
]
RATING_COLUMNS = [
    "team_name", "season", "total_games", "goals_per_game", "goals_conceded_per_game",
    "clean_sheets",
]
TREND_COLUMNS = ["matchday", "team_name", "cumulative_points"]
MATCH_COLUMNS = [
    "matchday", "match_timestamp", "home_team_name", "away_team_name", "goals_home",
    "goals_away", "status",
]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def api_guard(func):
    """Zeigt bei einem API-Fehler eine verständliche Meldung statt eines Stacktraces.

    Muss außen um die gecachte Funktion liegen: Ausnahmen werden von st.cache_data nicht
    zwischengespeichert und kommen deshalb hier an.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ApiError as exc:
            st.error(f"Die Daten sind gerade nicht verfügbar. {exc}")
            st.caption("Bitte versuche es in einem Moment erneut.")
            st.stop()

    return wrapper


def _frame(rows: list[dict], columns: list[str], **constants) -> pd.DataFrame:
    """Baut aus API-Zeilen ein DataFrame mit festen Spalten (auch wenn es keine Zeilen gibt)."""
    df = pd.DataFrame(rows)
    for name, value in constants.items():
        df[name] = value
    return df.reindex(columns=columns)


@functools.lru_cache(maxsize=1)
def _engine():
    """Datenbank-Engine für den direkten Zugriff. Wird nur bei Bedarf geladen."""
    from src.utils.db_client import get_db_engine

    return get_db_engine()


def _read_sql(query: str, params: dict | None = None) -> pd.DataFrame:
    """Direkter Datenbankzugriff (nur ohne API_URL)."""
    from sqlalchemy import text

    with _engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def _api_ratings(season: str) -> pd.DataFrame:
    return _frame(api_client.ratings(season), RATING_COLUMNS, season=season)


def _api_home_away(season: str) -> pd.DataFrame:
    return _frame(api_client.home_away(season), HOME_AWAY_COLUMNS, season=season)


# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------

@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_seasons() -> list[str]:
    """Alle verfügbaren Saisons, neueste zuerst."""
    if api_client.is_enabled():
        return api_client.seasons()
    df = _read_sql("SELECT DISTINCT season FROM fct_standings ORDER BY season DESC")
    return df["season"].tolist()


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_teams(season: str) -> list[str]:
    """Alle Teams einer Saison, alphabetisch."""
    if api_client.is_enabled():
        return api_client.teams(season)
    df = _read_sql(
        "SELECT DISTINCT team_name FROM fct_standings WHERE season = :s ORDER BY team_name",
        {"s": season},
    )
    return df["team_name"].tolist()


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_team_meta() -> pd.DataFrame:
    """Kürzel und Wappen aller Teams (Spalten: team_name, crest_url, tla)."""
    if api_client.is_enabled():
        return _frame(api_client.team_meta(), TEAM_META_COLUMNS)
    return _read_sql("SELECT team_name, crest_url, tla FROM dim_teams")


def get_team_crests() -> dict:
    """Ein Mapping {team_name: crest_url}."""
    meta = get_team_meta()
    return dict(zip(meta["team_name"], meta["crest_url"]))


def get_team_info(team_name: str) -> pd.DataFrame:
    """Wappen und Kürzel eines Teams (eine Zeile oder leer)."""
    meta = get_team_meta()
    return meta[meta["team_name"] == team_name].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Auswertungen je Saison
# ---------------------------------------------------------------------------

@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_standings(season: str) -> pd.DataFrame:
    """Tabelle einer Saison inklusive Wappen, bester Platz zuerst."""
    if api_client.is_enabled():
        df = _frame(api_client.standings(season), STANDING_COLUMNS, season=season)
        df["crest_url"] = df["team_name"].map(get_team_crests())
        return df
    return _read_sql(
        "SELECT s.*, t.crest_url FROM fct_standings s "
        "JOIN dim_teams t ON s.team_name = t.team_name "
        "WHERE s.season = :season_param "
        "ORDER BY s.total_points DESC, s.goal_diff DESC",
        {"season_param": season},
    )


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_season_trends(season: str) -> pd.DataFrame:
    """Punkteverlauf aller Teams, nach Spieltag sortiert."""
    if api_client.is_enabled():
        df = _frame(api_client.season_trend(season), TREND_COLUMNS)
        df = df.sort_values("matchday", kind="stable").reset_index(drop=True)
    else:
        df = _read_sql(
            "SELECT matchday, team_name, cumulative_points FROM fct_season_trend "
            "WHERE season = :s ORDER BY matchday ASC",
            {"s": season},
        )
    df["matchday"] = pd.to_numeric(df["matchday"])
    return df


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_home_away(season: str) -> pd.DataFrame:
    """Heim- und Auswärtsbilanz aller Teams inklusive Wappen und Kürzel."""
    if api_client.is_enabled():
        df = _api_home_away(season)
        meta = get_team_meta().set_index("team_name")
        df["crest_url"] = df["team_name"].map(meta["crest_url"])
        df["tla"] = df["team_name"].map(meta["tla"])
        return df
    return _read_sql(
        "SELECT ha.*, t.crest_url, t.tla FROM fct_home_away_stats ha "
        "JOIN dim_teams t ON ha.team_name = t.team_name WHERE ha.season = :s",
        {"s": season},
    )


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_ratings(season: str) -> pd.DataFrame:
    """Offensiv- und Defensivwerte aller Teams plus berechneter performance_score."""
    if api_client.is_enabled():
        df = _api_ratings(season)
    else:
        df = _read_sql("SELECT * FROM fct_team_ratings WHERE season = :s", {"s": season})
    if "goals_per_game" in df.columns and "goals_conceded_per_game" in df.columns:
        df["performance_score"] = df["goals_per_game"] - df["goals_conceded_per_game"]
    else:
        df["performance_score"] = 0
    return df


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_team_details(team_name: str, season: str) -> tuple:
    """Form, Ratings, Punkteverlauf und Heim/Auswärts-Bilanz eines Teams.

    Returns:
        Tupel (form, ratings, trends, home_away) aus je einem DataFrame.
    """
    if api_client.is_enabled():
        try:
            form = _frame(api_client.team_form(season, [team_name]), ["form_trend"])
            trends = _frame(
                api_client.season_trend(season, [team_name]), ["matchday", "cumulative_points"]
            )
        except ApiNotFound:
            form = _frame([], ["form_trend"])
            trends = _frame([], ["matchday", "cumulative_points"])
        ratings = _api_ratings(season)
        ratings = ratings[ratings["team_name"] == team_name].reset_index(drop=True)
        home_away = _api_home_away(season)
        home_away = home_away[home_away["team_name"] == team_name].reset_index(drop=True)
        return form, ratings, trends, home_away

    params = {"team_name": team_name, "season": season}
    form = _read_sql(
        "SELECT form_trend FROM fct_team_form "
        "WHERE team_name = :team_name AND season = :season", params)
    ratings = _read_sql(
        "SELECT * FROM fct_team_ratings WHERE team_name = :team_name AND season = :season",
        params)
    trends = _read_sql(
        "SELECT matchday, cumulative_points FROM fct_season_trend "
        "WHERE team_name = :team_name AND season = :season ORDER BY matchday", params)
    home_away = _read_sql(
        "SELECT * FROM fct_home_away_stats WHERE team_name = :team_name AND season = :season",
        params)
    return form, ratings, trends, home_away


# ---------------------------------------------------------------------------
# Startseite
# ---------------------------------------------------------------------------

def _one_row(row: dict | None, columns: list[str]) -> pd.DataFrame:
    """Ein DataFrame mit höchstens einer Zeile (leer, wenn es keinen Eintrag gibt)."""
    return pd.DataFrame([row] if row else [], columns=columns)


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_league_highlights(season: str) -> tuple:
    """Lädt KPI-Daten: Tabellenführer, Heimmacht, Offensiv-König, Formstark."""
    if api_client.is_enabled():
        data = api_client.highlights(season)
        return (
            _one_row(data["leader"], ["team_name", "total_points"]),
            _one_row(data["home_king"], ["team_name", "home_points"]),
            _one_row(data["attack_king"], ["team_name", "goals_per_game"]),
            _one_row(data["form_king"], ["team_name", "form_trend"]),
        )

    params = {"s": season}
    leader = _read_sql(
        "SELECT team_name, total_points FROM fct_standings "
        "WHERE season = :s ORDER BY total_points DESC, goal_diff DESC LIMIT 1", params)
    home_king = _read_sql(
        "SELECT team_name, home_points FROM fct_home_away_stats "
        "WHERE season = :s ORDER BY home_points DESC LIMIT 1", params)
    attack_king = _read_sql(
        "SELECT team_name, goals_per_game FROM fct_team_ratings "
        "WHERE season = :s ORDER BY goals_per_game DESC LIMIT 1", params)
    form_king = _read_sql(
        "SELECT team_name, form_trend FROM fct_team_form WHERE season = :s "
        "ORDER BY (LENGTH(form_trend) - LENGTH(REPLACE(form_trend, 'W', ''))) DESC LIMIT 1",
        params)
    return leader, home_king, attack_king, form_king


@api_guard
@st.cache_data(ttl=CACHE_TTL)
def get_match_schedule(season: str) -> pd.DataFrame:
    """Kompletter Spielplan einer Saison (jüngster Spieltag zuerst)."""
    if api_client.is_enabled():
        df = _frame(api_client.matches(season), MATCH_COLUMNS)
        timestamps = pd.to_datetime(df["match_timestamp"])
        df["match_timestamp"] = timestamps
        df["match_date"] = timestamps.dt.date
        df["match_time"] = timestamps.dt.strftime("%H:%M")
        return df
    return _read_sql(
        "SELECT matchday, match_timestamp, DATE(match_timestamp) AS match_date, "
        "TO_CHAR(match_timestamp, 'HH24:MI') AS match_time, home_team_name, "
        "away_team_name, goals_home, goals_away, status "
        "FROM stg_matches WHERE season = :s "
        "ORDER BY matchday DESC, match_timestamp ASC",
        {"s": season},
    )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def _empty_status() -> dict:
    return {
        "last_update": None,
        "match_count": 0,
        "team_count": 0,
        "season_count": 0,
        "db_online": False,
    }


def _status_from_database(status: dict) -> None:
    """Füllt den Status mit Zahlen direkt aus der Datenbank (nur ohne API_URL)."""
    from sqlalchemy import text

    with _engine().connect() as conn:
        status["db_online"] = True
        row = conn.execute(text(
            "SELECT MAX(match_timestamp) AS last_ts FROM stg_matches WHERE status = 'FINISHED'"
        )).fetchone()
        if row and row[0]:
            status["last_update"] = row[0].strftime("%d.%m.%Y %H:%M")
        status["match_count"] = conn.execute(
            text("SELECT COUNT(*) FROM raw_matches")).scalar() or 0
        status["team_count"] = conn.execute(
            text("SELECT COUNT(*) FROM raw_teams")).scalar() or 0
        status["season_count"] = conn.execute(
            text("SELECT COUNT(DISTINCT season) FROM raw_matches")).scalar() or 0


@st.cache_data(ttl=CACHE_TTL)
def get_db_status() -> dict:
    """Liefert Live-Infos über den Zustand der Daten.

    Fehler werden hier nicht als Fehlerseite gezeigt: Das Ergebnis wird im Footer jeder
    Seite angezeigt, db_online=False genügt dort.

    Returns:
        dict mit keys: last_update, match_count, team_count, season_count, db_online
    """
    status = _empty_status()

    if api_client.is_enabled():
        try:
            data = api_client.status()
        except ApiError:
            return status
        status["db_online"] = True
        if data.get("last_update"):
            status["last_update"] = datetime.fromisoformat(
                data["last_update"]).strftime("%d.%m.%Y %H:%M")
        status["match_count"] = data.get("match_count", 0)
        status["team_count"] = data.get("team_count", 0)
        status["season_count"] = data.get("season_count", 0)
        return status

    try:
        _status_from_database(status)
    except Exception:
        # Retry einmal – Neon Cloud braucht ggf. einige Sekunden zum Aufwachen
        try:
            time.sleep(3)
            _status_from_database(status)
        except Exception:
            status = _empty_status()
    return status
