import pytest
from sqlalchemy import text
from src.utils.db_client import get_db_engine

@pytest.mark.skipif(reason="Benötigt Live-DB-Verbindung") # Optional: Markierung für lokale DB
def test_check_team_count():
    engine = get_db_engine()
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM raw_teams")).scalar()
        assert count == 18, f"Erwartet 18 Teams, gefunden: {count}"

def test_check_finished_matches_have_scores():
    engine = get_db_engine()
    query = "SELECT COUNT(*) FROM raw_matches WHERE status = 'FINISHED' AND score_home IS NULL"
    with engine.connect() as conn:
        invalid_matches = conn.execute(text(query)).scalar()
        assert invalid_matches == 0, "Beendete Spiele ohne Tore in der DB gefunden!"


def run_quality_checks():
    """Wrapper für Pipeline-Aufruf – führt die Checks manuell aus."""
    print("🧪 Starte Data Quality Checks...")
    engine = get_db_engine()
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM raw_teams")).scalar()
        if count != 18:
            raise ValueError(f"❌ QUALITÄTSFEHLER: Erwartet 18 Teams, aber {count} gefunden!")
        print(f"   ✅ Team-Anzahl korrekt: {count}")

        query = "SELECT COUNT(*) FROM raw_matches WHERE status = 'FINISHED' AND score_home IS NULL"
        invalid = conn.execute(text(query)).scalar()
        if invalid > 0:
            raise ValueError("❌ QUALITÄTSFEHLER: Beendete Spiele ohne Tore gefunden!")
        print("   ✅ Keine unvollständigen Spielergebnisse gefunden.")