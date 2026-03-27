import requests
import os
import pandas as pd
from src.utils.db_client import get_db_engine
from sqlalchemy import text

def ingest_bundesliga_matches():
    #API Konfiguration
    api_key = os.getenv("FOOTBALL_API_KEY")
    url = "https://api.football-data.org/v4/competitions/BL1/matches"
    headers = {"X-Auth-Token": api_key}
    
    print("📡 Rufe Bundesliga-Spiele ab...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        matches = data.get('matches',[])
        
        # 2. Daten transformieren
        match_list = []
        for m in matches:
            match_list.append({
                'match_id': m['id'],
                'utc_date': m['utcDate'],
                'status': m['status'],
                'matchday': m['matchday'],
                'home_team_id': m['homeTeam']['id'],
                'away_team_id': m['awayTeam']['id'],
                'home_team': m['homeTeam']['name'],
                'away_team': m['awayTeam']['name'],
                'score_home': m['score']['fullTime']['home'],
                'score_away': m['score']['fullTime']['away'],
                'winner': m['score']['winner']
            })
        
        df = pd.DataFrame(match_list)
        
        # 3. In Datenbank schreiben
        engine = get_db_engine()
        
        # Sicherstellen, dass die Tabelle existiert, bevor TRUNCATE aufgerufen wird
        df.head(0).to_sql('raw_matches', engine, if_exists='append', index=False)
        
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE raw_matches;"))
            conn.commit()
        
        df.to_sql('raw_matches', engine, if_exists='append', index=False)
        
        print(f"✅ Erfolg! {len(df)} Spiele wurden in 'raw_matches' gespeichert.")
        return len(df) # WICHTIG für dein Logging in main.py
    else:
        print(f"❌ Fehler: {response.status_code}")
        return 0 # Gibt 0 zurück, falls der API-Call fehlschlägt

if __name__ == "__main__":
    ingest_bundesliga_matches()