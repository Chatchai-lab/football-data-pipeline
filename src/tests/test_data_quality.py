from src.utils.db_client import get_db_engine
from sqlalchemy import text

def run_quality_checks():
    engine = get_db_engine()
    print("🧪 Starte Data Quality Checks...")
    
    with engine.connect() as conn:
        # Check 1: Haben wir alle 18 Bundesliga-Teams?
        result = conn.execute(text("SELECT COUNT(*) FROM raw_teams"))
        count = result.scalar()
        if count != 18:
            raise ValueError(f"❌ QUALITÄTSFEHLER: Erwartet 18 Teams, aber {count} gefunden!")
        print(f"   ✅ Team-Anzahl korrekt: {count}")

        # Check 2: Gibt es Spiele ohne Ergebnis (NULL), die aber als 'FINISHED' markiert sind?
        query = "SELECT COUNT(*) FROM raw_matches WHERE status = 'FINISHED' AND score_home IS NULL"
        result = conn.execute(text(query))
        if result.scalar() > 0:
            raise ValueError("❌ QUALITÄTSFEHLER: Beendete Spiele ohne Tore gefunden!")
        print("   ✅ Keine unvollständigen Spielergebnisse gefunden.")

if __name__ == "__main__":
    run_quality_checks()