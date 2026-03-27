import os
from sqlalchemy import text
from src.utils.db_client import get_db_engine

def run_sql_file(conn, file_path):
    """Hilfsfunktion, um eine einzelne SQL-Datei über eine bestehende Verbindung auszuführen."""
    with open(file_path, 'r') as f:
        query = f.read()
    conn.execute(text(query))
    print(f"   ↳ ✅ SQL ausgeführt: {os.path.basename(file_path)}")

def transform_data():
    engine = get_db_engine()
    staging_dir = os.path.join('sql', 'staging')
    
    # Sicherstellen, dass der Ordner existiert
    if not os.path.exists(staging_dir):
        print(f"⚠️ Ordner {staging_dir} nicht gefunden.")
        return

    files = sorted([f for f in os.listdir(staging_dir) if f.endswith('.sql')])
    
    print(f"🚀 Starte {len(files)} Daten-Transformationen...")
    
    with engine.connect() as conn:
        for file_name in files:
            file_path = os.path.join(staging_dir, file_name)
            run_sql_file(conn, file_path)
        
        # Wichtig: Erst ganz am Ende commiten, wenn alles ohne Fehler lief
        conn.commit()
    print("🏁 Alle Transformationen erfolgreich abgeschlossen.")

if __name__ == "__main__":
    transform_data()