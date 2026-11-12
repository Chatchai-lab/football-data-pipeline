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
    
    # Standardport 5432, falls nicht oder leer in .env definiert
    port = os.getenv('DB_PORT') or '5432'
    host = os.getenv('DB_HOST', 'localhost')
    sslmode = os.getenv('DB_SSLMODE', '')
    
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    # SSL-Parameter anhängen (z.B. für Neon Cloud)
    if sslmode:
        db_url += f"?sslmode={sslmode}"
    
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,           # Prüft Verbindung vor Nutzung (hilft bei Neon Cold-Start)
            pool_recycle=300,              # Recycled Connections alle 5 Min.
            connect_args={"connect_timeout": 10},  # 10 Sek. Timeout für Neon Wakeup
            # Größe des Verbindungspools, per Umgebungsvariable einstellbar. Die Standardwerte sind die
            # von SQLAlchemy, die Produktion ändert sich also nicht. Die API im Cluster setzt eigene Werte.
            pool_size=int(os.getenv('DB_POOL_SIZE') or 5),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW') or 10),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT') or 30),
        )
        return engine
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der DB-Engine: {e}")
        return None
