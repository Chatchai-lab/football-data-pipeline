import requests
import os
import pandas as pd
from src.utils.db_client import get_db_engine
from sqlalchemy import text

def ingest_bundesliga_teams():
    # API Konfiguration
    api_key = os.getenv('FOOTBALL_API_KEY')
    url = "https://api.football-data.org/v4/competitions/BL1/teams"
    headers = {"X-Auth-Token": api_key}
    
    print("📡 Rufe Bundesliga-Teams von API ab...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        teams = data.get('teams', [])
        
        # 2. Daten transformieren
        team_list = []
        for t in teams:
            team_list.append({
                'api_id': t['id'],
                'name': t['name'],
                'short_name': t['shortName'],
                'tla': t['tla'],
                'crest_url': t['crest'],
                'address': t['address'], 
            })
            
        df = pd.DataFrame(team_list)
        
        # 3. In Datenbank schreiben
        engine = get_db_engine()
        
        with engine.connect() as conn:
            try:
                conn.execute(text("TRUNCATE TABLE raw_teams;"))
                conn.commit()
            except Exception:
                conn.rollback()  # Tabelle existiert noch nicht – wird von to_sql erstellt
        
        df.to_sql('raw_teams', engine, if_exists='append', index=False)
        
        print(f"✅ Erfolg! {len(df)} Teams wurden in 'raw_teams' gespeichert.")
        return len(df) # WICHTIG für dein Logging in main.py
    else:
        print(f"❌ Fehler beim Abrufen der Daten: {response.status_code}")
        return 0 # Gibt 0 zurück, falls der API-Call fehlschlägt
        
if __name__ == "__main__":
    ingest_bundesliga_teams()