"""Bereitet eine leere Datenbank vor: Tabellen, Silver/Gold-Views, Read-only-Rolle.

Das Skript ist idempotent: Es kann beliebig oft laufen und hinterlaesst immer
denselben Zustand. Es laedt keine Daten (siehe docs/kubernetes.md).
"""
import os
import sys

from sqlalchemy import text

from src.transformation.run_transformations import transform_data
from src.utils.db_client import get_db_engine

# Sicherheitsnetz: nur gegen lokale bzw. Cluster-Datenbanken ausfuehren, nie gegen Neon.
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "postgres"}

API_ROLE = "api_ro"

# Spalten und Typen entsprechen dem, was pandas.to_sql beim ersten Schreiben anlegt.
CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS raw_teams (
        api_id     BIGINT,
        name       TEXT,
        short_name TEXT,
        tla        TEXT,
        crest_url  TEXT,
        address    TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_matches (
        match_id     BIGINT,
        utc_date     TEXT,
        season       TEXT,
        status       TEXT,
        matchday     BIGINT,
        home_team_id BIGINT,
        away_team_id BIGINT,
        home_team    TEXT,
        away_team    TEXT,
        score_home   DOUBLE PRECISION,
        score_away   DOUBLE PRECISION,
        winner       TEXT
    )
    """,
]

# Nur diese Objekte darf die API lesen (Least Privilege).
READABLE_OBJECTS = [
    "fct_standings",
    "fct_season_trend",
    "fct_team_form",
    "fct_home_away_stats",
    "fct_team_ratings",
    "dim_teams",
    "stg_matches",
]


def check_target():
    """Bricht ab, wenn DB_HOST nicht in der Erlaubnisliste steht."""
    host = os.getenv("DB_HOST", "localhost")
    if host not in ALLOWED_HOSTS:
        sys.exit(f"Abbruch: DB_HOST={host!r} ist nicht erlaubt (erlaubt: {sorted(ALLOWED_HOSTS)}).")


def create_tables(engine):
    """Legt die Rohtabellen an, falls es sie noch nicht gibt."""
    with engine.begin() as conn:
        for ddl in CREATE_TABLES:
            conn.execute(text(ddl))


def create_api_role(engine):
    """Legt die Read-only-Rolle an (oder setzt ihr Passwort neu) und vergibt SELECT."""
    password = os.getenv("API_RO_PASSWORD")
    if not password:
        sys.exit("Abbruch: API_RO_PASSWORD ist nicht gesetzt.")

    quote = engine.dialect.identifier_preparer.quote
    db_name = quote(os.getenv("DB_NAME"))

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": API_ROLE}
        ).scalar()
        verb = "ALTER" if exists else "CREATE"
        conn.execute(text(f"{verb} ROLE {API_ROLE} LOGIN PASSWORD :pw"), {"pw": password})
        conn.execute(text(f"GRANT CONNECT ON DATABASE {db_name} TO {API_ROLE}"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {API_ROLE}"))
        for obj in READABLE_OBJECTS:
            conn.execute(text(f"GRANT SELECT ON {obj} TO {API_ROLE}"))


def main():
    check_target()
    engine = get_db_engine()
    if engine is None:
        sys.exit("Abbruch: keine Datenbankverbindung.")

    print("1/3 Tabellen anlegen ...")
    create_tables(engine)

    print("2/3 Silver/Gold-Views bauen ...")
    transform_data()

    print(f"3/3 Rolle {API_ROLE} anlegen und Rechte vergeben ...")
    create_api_role(engine)

    print("Fertig.")


if __name__ == "__main__":
    main()
