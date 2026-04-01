# src/main.py
from src.ingestion.ingest_teams import ingest_bundesliga_teams
from src.ingestion.ingest_matches import ingest_bundesliga_matches, get_available_seasons
import datetime
from src.transformation.run_transformations import transform_data
from tests.test_database_integrity import run_quality_checks

def run_pipeline():
    start_time = datetime.datetime.now()
    count_teams = 0
    count_matches = 0
    print(f"--- 🚀 Starte Football Data Pipeline um {start_time.strftime('%H:%M:%S')} ---")
    
    try:
        # SCHRITT 1: Ingestion (Extraktion & Laden)
        print("\n[1/2] Starte Datenerfassung von API.." )
        count_teams = ingest_bundesliga_teams()
        
        # Saisons dynamisch von der API laden (ALLE verfügbaren)
        all_seasons = get_available_seasons()
        saisons = all_seasons  # Alle Saisons laden
        print(f"📅 Lade {len(saisons)} Saisons: {saisons[:5]}{'...' if len(saisons) > 5 else ''}")
        
        count_matches = 0
        for s in saisons:
            count_matches += ingest_bundesliga_matches(season=s)
        
        run_quality_checks()
        
        # SCHRITT 2: Transformation (Bereinigung & Berechnung)
        print("\n[2/2] Starte Daten-Transformationen...")
        transform_data()
        
        end_time = datetime.datetime.now()
        duration = end_time - start_time
    
        # Zusammenfassung (Logging)
        print("\n" + "="*30)
        print("📊 PIPELINE ZUSAMMENFASSUNG")
        print(f"📅 Datum: {end_time.strftime('%Y-%m-%d')}")
        print(f"🕒 Dauer: {duration.total_seconds():.2f} Sekunden")
        print(f"⚽ Teams geladen:   {count_teams}")
        print(f"🏟️ Matches geladen: {count_matches}")
        print(f"✅ Gesamtstatus:   ERFOLGREICH")
        print("="*30)
        
    except Exception as e:
        print(f"\n❌ Fehler bei der Pipeline-Ausführung: {str(e)}")
    


if __name__ == "__main__":
    run_pipeline()