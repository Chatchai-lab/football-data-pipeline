import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env
load_dotenv()

def get_db_engine():
    """
    Erstellt und gibt eine SQLAlchemy Engine zur PostgreSQL-Datenbank zurück.
    Nutzt die Umgebungsvariablen DB_USER, DB_PASSWORD, DB_NAME und DB_PORT.
    """
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    name = os.getenv('DB_NAME')
    
    # Standardport 5433, falls nicht anders in .env definiert
    port = os.getenv('DB_PORT', '5433')
    host = os.getenv('DB_HOST', 'localhost')
    
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    try:
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der DB-Engine: {e}")
        return None
