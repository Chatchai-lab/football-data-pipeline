from typing import Annotated

from fastapi import HTTPException, Query
from sqlalchemy import Connection, text

# Saison als Startjahr, z. B. "2025". Alles andere wird mit 422 abgelehnt.
Season = Annotated[
    str,
    Query(pattern=r"^\d{4}$", description="Startjahr der Saison, z. B. 2025"),
]


def require_season(conn: Connection, season: str) -> None:
    """Wirft 404, wenn es zu der Saison keine Daten gibt."""
    exists = conn.execute(
        text("SELECT 1 FROM fct_standings WHERE season = :s LIMIT 1"),
        {"s": season},
    ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"Saison {season} nicht gefunden")
