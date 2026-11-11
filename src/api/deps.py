from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine

from src.utils.db_client import get_db_engine


@lru_cache
def get_engine() -> Engine:
    """Erstellt die Engine einmalig und gibt danach immer dieselbe zurueck."""
    engine = get_db_engine()
    if engine is None:
        raise RuntimeError("Datenbank-Engine konnte nicht erstellt werden")
    return engine


def get_db() -> Iterator[Connection]:
    """Dependency: oeffnet pro Anfrage eine Verbindung und schliesst sie danach."""
    with get_engine().connect() as conn:
        yield conn
