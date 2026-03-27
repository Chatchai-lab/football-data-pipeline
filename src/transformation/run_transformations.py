import os
from sqlalchemy import text
from src.utils.db_client import get_db_engine

def run_sql_file(conn, file_path):
    with open(file_path, 'r') as f:
        query = f.read()
    conn.execute(text(query))
    print(f"   ↳ ✅ ausgeführt: {os.path.basename(file_path)}")

def transform_data():
    engine = get_db_engine()
    staging_dir = os.path.join('sql', 'staging')
    
    
    layers = {
        # 1. CLEANING: Nur Rohdaten säubern (Datentypen, NULL-Werte)
        "SILVER_STAGING": ["stg_matches.sql", "stg_standings.sql"],
        
        # 2. CORE: Das Star-Schema aufbauen (Stabile Basis)
        "SILVER_CORE": ["dim_teams.sql", "fact_matches.sql"],
        
        # 3. GOLD: Die finalen Produkte für das Dashboard
        "GOLD_MARTS": [
            "fct_standings.sql", 
            "fct_season_trends.sql", 
            "fct_team_form.sql", 
            "fct_home_away_stats.sql", 
            "fct_team_ratings.sql"
        ]
    }

    print("🚀 Starte strukturierte Transformation (dbt-Style)...")
    
    with engine.connect() as conn:
        for layer_name, files in layers.items():
            print(f"\n--- {layer_name} ---")
            for file_name in files:
                file_path = os.path.join(staging_dir, file_name)
                if os.path.exists(file_path):
                    run_sql_file(conn, file_path)
                else:
                    print(f"   ⚠️ Datei übersprungen (nicht gefunden): {file_name}")
        
        conn.commit()
    print("\n🏁 Alle Layer erfolgreich aufgebaut.")