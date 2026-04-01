# src/main.py
from src.ingestion.ingest_teams import ingest_bundesliga_teams
from src.ingestion.ingest_matches import ingest_bundesliga_matches, get_available_seasons
import datetime
from src.transformation.run_transformations import transform_data
from tests.test_database_integrity import run_quality_checks
from src.utils.logger import get_logger

logger = get_logger("pipeline")

def run_pipeline():
    start_time = datetime.datetime.now()
    count_teams = 0
    count_matches = 0
    logger.info("Starte Football Data Pipeline um %s", start_time.strftime('%H:%M:%S'))
    
    try:
        # SCHRITT 1: Ingestion (Extraktion & Laden)
        logger.info("[1/2] Starte Datenerfassung von API...")
        count_teams = ingest_bundesliga_teams()
        
        # Saisons dynamisch von der API laden (ALLE verfügbaren)
        all_seasons = get_available_seasons()
        saisons = all_seasons  # Alle Saisons laden
        logger.info("Lade %d Saisons: %s%s", len(saisons), saisons[:5], '...' if len(saisons) > 5 else '')
        
        count_matches = 0
        for s in saisons:
            count_matches += ingest_bundesliga_matches(season=s)
        
        run_quality_checks()
        
        # SCHRITT 2: Transformation (Bereinigung & Berechnung)
        logger.info("[2/2] Starte Daten-Transformationen...")
        transform_data()
        
        end_time = datetime.datetime.now()
        duration = end_time - start_time
    
        # Zusammenfassung
        logger.info("=" * 50)
        logger.info("PIPELINE ZUSAMMENFASSUNG")
        logger.info("Datum: %s", end_time.strftime('%Y-%m-%d'))
        logger.info("Dauer: %.2f Sekunden", duration.total_seconds())
        logger.info("Teams geladen:   %d", count_teams)
        logger.info("Matches geladen: %d", count_matches)
        logger.info("Gesamtstatus:    ERFOLGREICH")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error("Fehler bei der Pipeline-Ausführung: %s", str(e), exc_info=True)
        raise
    


if __name__ == "__main__":
    run_pipeline()