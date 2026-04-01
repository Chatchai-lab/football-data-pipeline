import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env
load_dotenv()

def get_db_engine():
    """
    Erstellt und gibt eine SQLAlchemy Engine zur PostgreSQL-Datenbank zurück.
    Nutzt die Umgebungsvariablen DB_USER, DB_PASSWORD, DB_NAME, DB_PORT,
    DB_HOST und optional DB_SSLMODE.
    """
    user = os.getenv('DB_USER')
    password = quote_plus(os.getenv('DB_PASSWORD', ''))
    name = os.getenv('DB_NAME')
    
    # Standardport 5433, falls nicht anders in .env definiert
    port = os.getenv('DB_PORT', '5433')
    host = os.getenv('DB_HOST', 'localhost')
    sslmode = os.getenv('DB_SSLMODE', '')
    
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    # SSL-Parameter anhängen (z.B. für Neon Cloud)
    if sslmode:
        db_url += f"?sslmode={sslmode}"
    
    try:
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der DB-Engine: {e}")
        return None
