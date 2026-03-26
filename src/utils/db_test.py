import os
from sqlalchemy import text
from src.utils.db_client import get_db_engine

def test_connection():
    # Wir nutzen den zentralen DB-Client
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # Ein einfacher SQL-Befehl zum Testen
            result = conn.execute(text("SELECT version();"))
            print("🚀 STATUS: Verbindung erfolgreich!")
            print(f"📦 DB-Version: {result.fetchone()[0]}")
    except Exception as e:
        print("❌ STATUS: Verbindung fehlgeschlagen!")
        print(f"Fehlermeldung: {e}")

if __name__ == "__main__":
    test_connection()