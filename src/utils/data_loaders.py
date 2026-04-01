"""
Zentrale Daten-Lade-Schicht für die Matchlytics-App.
Alle SQL-Queries und Cache-Funktionen an einem Ort.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.utils.db_client import get_db_engine

engine = get_db_engine()


@st.cache_data
def get_team_crests() -> dict:
    """Lädt ein Mapping {team_name: crest_url} aus dim_teams."""
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT team_name, crest_url FROM dim_teams"), conn)
    return dict(zip(df["team_name"], df["crest_url"]))


@st.cache_data
def get_league_highlights(season: str) -> tuple:
    """Lädt KPI-Daten: Tabellenführer, Heimmacht, Offensiv-König, Formstark."""
    with engine.connect() as conn:
        leader = pd.read_sql(
            text(
                "SELECT team_name, total_points FROM fct_standings "
                "WHERE season = :s ORDER BY total_points DESC, goal_diff DESC LIMIT 1"
            ),
            conn,
            params={"s": season},
        )
        home_king = pd.read_sql(
            text(
                "SELECT team_name, home_points FROM fct_home_away_stats "
                "WHERE season = :s ORDER BY home_points DESC LIMIT 1"
            ),
            conn,
            params={"s": season},
        )
        attack_king = pd.read_sql(
            text(
                "SELECT team_name, goals_per_game FROM fct_team_ratings "
                "WHERE season = :s ORDER BY goals_per_game DESC LIMIT 1"
            ),
            conn,
            params={"s": season},
        )
        form_king = pd.read_sql(
            text(
                "SELECT team_name, form_trend FROM fct_team_form "
                "WHERE season = :s "
                "ORDER BY (LENGTH(form_trend) - LENGTH(REPLACE(form_trend, 'W', ''))) DESC "
                "LIMIT 1"
            ),
            conn,
            params={"s": season},
        )
    return leader, home_king, attack_king, form_king


@st.cache_data(ttl=300)
def get_db_status() -> dict:
    """Liefert Live-Infos über den Zustand der Datenbank.

    Returns:
        dict mit keys: last_update, match_count, team_count, season_count, db_online
    """
    status = {
        "last_update": None,
        "match_count": 0,
        "team_count": 0,
        "season_count": 0,
        "db_online": False,
    }
    try:
        with engine.connect() as conn:
            status["db_online"] = True

            # Letztes Match-Update (neuester utc_date-Eintrag)
            row = conn.execute(text(
                "SELECT MAX(match_timestamp) AS last_ts FROM stg_matches"
            )).fetchone()
            if row and row[0]:
                status["last_update"] = row[0].strftime("%d.%m.%Y %H:%M")

            # Zähler
            status["match_count"] = conn.execute(
                text("SELECT COUNT(*) FROM raw_matches")
            ).scalar() or 0
            status["team_count"] = conn.execute(
                text("SELECT COUNT(*) FROM raw_teams")
            ).scalar() or 0
            status["season_count"] = conn.execute(
                text("SELECT COUNT(DISTINCT season) FROM raw_matches")
            ).scalar() or 0
    except Exception:
        status["db_online"] = False
    return status


@st.cache_data
def get_match_schedule(season: str) -> pd.DataFrame:
    """Lädt den kompletten Spielplan einer Saison aus stg_matches."""
    query = text("""
        SELECT 
            matchday,
            match_timestamp,
            DATE(match_timestamp) AS match_date,
            TO_CHAR(match_timestamp, 'HH24:MI') AS match_time,
            home_team_name,
            away_team_name,
            goals_home,
            goals_away,
            status
        FROM stg_matches
        WHERE season = :s
        ORDER BY matchday DESC, match_timestamp ASC
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"s": season})
