from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

from src.api.deps import get_db
from src.api.params import Season, require_season
from src.api.schemas import (
    HighlightsResponse,
    HomeAwayRow,
    MatchRow,
    RatingRow,
    SeasonTrendRow,
    StandingRow,
    TeamFormRow,
)

router = APIRouter(tags=["Gold-Views"])

# Optionaler Teamfilter, mehrfach angebbar: ?team=A&team=B
TeamFilter = Annotated[
    list[str] | None,
    Query(description="Teamname(n), mehrfach angebbar. Ohne Angabe: alle Teams."),
]


def fetch(conn: Connection, sql: str, params: dict) -> list[dict]:
    """Fuehrt eine Abfrage aus und gibt die Zeilen als Dictionaries zurueck."""
    return [dict(row) for row in conn.execute(text(sql), params).mappings()]

def fetch_one(conn: Connection, sql: str, params: dict) -> dict | None:
    """Gibt die erste Zeile als Dictionary zurueck oder None, wenn es keine gibt."""
    row = conn.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


@router.get("/standings", response_model=list[StandingRow])
def get_standings(season: Season, conn: Connection = Depends(get_db)):
    """Tabelle einer Saison, bester Platz zuerst."""
    require_season(conn, season)
    return fetch(
        conn,
        "SELECT team_name, tla, matches_played, total_points, total_goals_for, "
        "total_goals_against, goal_diff, points_per_match "
        "FROM fct_standings WHERE season = :s "
        "ORDER BY total_points DESC, goal_diff DESC, total_goals_for DESC",
        {"s": season},
    )


@router.get("/season-trend", response_model=list[SeasonTrendRow])
def get_season_trend(
    season: Season, team: TeamFilter = None, conn: Connection = Depends(get_db)
):
    """Punkteverlauf ueber die Spieltage, optional nur fuer bestimmte Teams."""
    require_season(conn, season)
    sql = (
        "SELECT team_name, matchday, cumulative_points "
        "FROM fct_season_trend WHERE season = :s"
    )
    params: dict = {"s": season}
    if team:
        sql += " AND team_name = ANY(:teams)"
        params["teams"] = team
    sql += " ORDER BY team_name, matchday"
    rows = fetch(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Keine Daten fuer diese Teams")
    return rows


@router.get("/team-form", response_model=list[TeamFormRow])
def get_team_form(
    season: Season, team: TeamFilter = None, conn: Connection = Depends(get_db)
):
    """Die letzten fuenf Ergebnisse (W/D/L), optional nur fuer bestimmte Teams."""
    require_season(conn, season)
    sql = "SELECT team_name, tla, form_trend FROM fct_team_form WHERE season = :s"
    params: dict = {"s": season}
    if team:
        sql += " AND team_name = ANY(:teams)"
        params["teams"] = team
    sql += " ORDER BY team_name"
    rows = fetch(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Keine Daten fuer diese Teams")
    return rows



@router.get("/home-away", response_model=list[HomeAwayRow])
def get_home_away(season: Season, conn: Connection = Depends(get_db)):
    """Heim- und Auswaertsbilanz je Team, beste Gesamtpunktzahl zuerst."""
    require_season(conn, season)
    return fetch(
        conn,
        "SELECT team_name, home_matches, home_points, home_goals_for, "
        "home_goals_against, home_wins, home_ppg, away_matches, away_points, "
        "away_goals_for, away_goals_against, away_wins, away_ppg, total_points "
        "FROM fct_home_away_stats WHERE season = :s ORDER BY total_points DESC",
        {"s": season},
    )


@router.get("/ratings", response_model=list[RatingRow])
def get_ratings(season: Season, conn: Connection = Depends(get_db)):
    """Offensiv- und Defensivwerte je Team, offensivstes Team zuerst."""
    require_season(conn, season)
    return fetch(
        conn,
        "SELECT team_name, total_games, goals_per_game, goals_conceded_per_game, "
        "clean_sheets FROM fct_team_ratings WHERE season = :s "
        "ORDER BY goals_per_game DESC",
        {"s": season},
    )


@router.get("/matches", response_model=list[MatchRow])
def get_matches(season: Season, conn: Connection = Depends(get_db)):
    """Kompletter Spielplan einer Saison, juengster Spieltag zuerst."""
    require_season(conn, season)
    return fetch(
        conn,
        "SELECT matchday, match_timestamp, home_team_name, away_team_name, "
        "goals_home, goals_away, status FROM stg_matches WHERE season = :s "
        "ORDER BY matchday DESC, match_timestamp ASC",
        {"s": season},
    )


@router.get("/highlights", response_model=HighlightsResponse)
def get_highlights(season: Season, conn: Connection = Depends(get_db)):
    """KPIs der Startseite: Tabellenfuehrer, Heimmacht, Offensiv-Koenig, Formstaerkster."""
    require_season(conn, season)
    params = {"s": season}
    return {
        "leader": fetch_one(
            conn,
            "SELECT team_name, total_points FROM fct_standings WHERE season = :s "
            "ORDER BY total_points DESC, goal_diff DESC LIMIT 1",
            params,
        ),
        "home_king": fetch_one(
            conn,
            "SELECT team_name, home_points FROM fct_home_away_stats WHERE season = :s "
            "ORDER BY home_points DESC LIMIT 1",
            params,
        ),
        "attack_king": fetch_one(
            conn,
            "SELECT team_name, goals_per_game FROM fct_team_ratings WHERE season = :s "
            "ORDER BY goals_per_game DESC LIMIT 1",
            params,
        ),
        "form_king": fetch_one(
            conn,
            "SELECT team_name, form_trend FROM fct_team_form WHERE season = :s "
            "ORDER BY (LENGTH(form_trend) - LENGTH(REPLACE(form_trend, 'W', ''))) DESC "
            "LIMIT 1",
            params,
        ),
    }
