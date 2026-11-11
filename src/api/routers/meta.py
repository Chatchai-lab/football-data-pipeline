from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text

from src.api.deps import get_db
from src.api.params import Season, require_season
from src.api.schemas import StatusResponse, TeamMeta

router = APIRouter(tags=["Stammdaten"])


@router.get("/status", response_model=StatusResponse)
def get_status(conn: Connection = Depends(get_db)) -> StatusResponse:
    """Zaehler und Zeitpunkt des letzten abgeschlossenen Spiels."""
    row = conn.execute(
        text(
            "SELECT MAX(match_timestamp) FILTER (WHERE status = 'FINISHED') AS last_update, "
            "COUNT(*) AS match_count, "
            "COUNT(DISTINCT season) AS season_count "
            "FROM stg_matches"
        )
    ).one()
    team_count = conn.execute(text("SELECT COUNT(*) FROM dim_teams")).scalar_one()
    return StatusResponse(
        last_update=row.last_update,
        match_count=row.match_count,
        team_count=team_count,
        season_count=row.season_count,
    )


@router.get("/seasons", response_model=list[str])
def get_seasons(conn: Connection = Depends(get_db)) -> list[str]:
    """Alle verfuegbaren Saisons, neueste zuerst."""
    rows = conn.execute(
        text("SELECT DISTINCT season FROM fct_standings ORDER BY season DESC")
    ).scalars().all()
    return list(rows)


@router.get("/teams", response_model=list[str])
def get_teams(season: Season, conn: Connection = Depends(get_db)) -> list[str]:
    """Alle Teams einer Saison, alphabetisch."""
    require_season(conn, season)
    rows = conn.execute(
        text(
            "SELECT DISTINCT team_name FROM fct_standings "
            "WHERE season = :s ORDER BY team_name"
        ),
        {"s": season},
    ).scalars().all()
    return list(rows)


@router.get("/team-meta", response_model=list[TeamMeta])
def get_team_meta(conn: Connection = Depends(get_db)) -> list[dict]:
    """Stammdaten aller Teams (Kuerzel und Wappen), unabhaengig von der Saison."""
    rows = conn.execute(
        text("SELECT team_name, tla, crest_url FROM dim_teams ORDER BY team_name")
    ).mappings().all()
    return [dict(row) for row in rows]
