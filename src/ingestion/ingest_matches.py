import requests
import os
import pandas as pd
from src.utils.db_client import get_db_engine

def ingest_bundesliga_matches():
    api_key = os.getenv("FOOTBALL_API_KEY")
    # Endpunkt für alle Spiele der Bundesliga
    url = "https://api.football-data.org/v4/competitions/BL1/matches"
    headers = {"X-Auth-Token": api_key}
    
    print("📡 Rufe Bundesliga-Spiele ab...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        matches = data.get('matches',[])
        
        match_list = []
        for m in matches:
            match_list.append({
                'match_id': m['id'],
                'utc_date': m['utcDate'],
                'status': m['status'],
                'matchday': m['matchday'],
                'home_team': m['homeTeam']['name'],
                'away_team': m['awayTeam']['name'],
                'score_home': m['score']['fullTime']['home'],
                'score_away': m['score']['fullTime']['away'],
                'winner': m['score']['winner']
            })
        
        df = pd.DataFrame(match_list)
        
        # Verbindung zur DB
        engine = get_db_engine()
        
        # Wir speichern es in 'raw_matches'
        df.to_sql('raw_matches', engine, if_exists='replace', index=False)
        
        print(f"✅ Erfolg! {len(df)} Spiele wurden in 'raw_matches' gespeichert.")
    else:
        print(f"❌ Fehler: {response.status_code}")

if __name__ == "__main__":
    ingest_bundesliga_matches()