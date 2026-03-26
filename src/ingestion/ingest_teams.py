import requests
import os
import pandas as pd
from src.utils.db_client import get_db_engine

def ingest_bundesliga_teams():
    # API Konfiguration
    api_key = os.getenv('FOOTBALL_API_KEY')
    url = "https://api.football-data.org/v4/competitions/BL1/teams"
    headers = {"X-Auth-Token": api_key}
    
    
    print(" Rufe Bundesliga-Teams von API ab..")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        teams = data.get('teams',[])
        
        # 2. Daten transformieren
        team_list = []
        for t in teams:
            team_list.append({
                'api_id': t['id'],
                'name': t['name'],
                'short_name': t['shortName'],
                'tla': t['tla'],
                'crest_url': t['crest'],
                'adress': t['address'],
            })
            
        df = pd.DataFrame(team_list)
        
        # 3. In Datenbank schreiben
        engine = get_db_engine()
        
        df.to_sql('raw_teams', engine, if_exists='replace', index=False)
        
        print(f"✅ Erfolg! {len(df)} Teams wurden in 'raw_teams' gespeichert.")
    else:
        print(f"❌ Fehler beim Abrufen der Daten: {response.status_code}")
        print(response.text)
        
if __name__ == "__main__":
    ingest_bundesliga_teams()