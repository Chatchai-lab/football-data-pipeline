import requests
import os
import pandas as pd
from src.utils.db_client import get_db_engine
from sqlalchemy import text

def ingest_bundesliga_matches(season=None):
    #API Konfiguration
    api_key = os.getenv("FOOTBALL_API_KEY")
    url = f"https://api.football-data.org/v4/competitions/BL1/matches"
    if season:
        url += f"?season={season}"
        
    headers = {"X-Auth-Token": api_key}
    
    print(f"📡 Rufe Bundesliga-Spiele ab ({season if season else 'Aktuell'})...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        matches = data.get('matches',[])
        
        # 2. Daten transformieren
        match_list = []
        # Fallback: Versuche season aus filters oder competition zu lesen
        season_year = data.get('filters', {}).get('season') 
        if not season_year:
            # Fallback 2: Falls season Parameter im Call war, nutze diesen
            season_year = str(season) if season else data.get('competition', {}).get('lastUpdated', '').split('-')[0]
        
        print(f"📊 Verarbeitete Saison: {season_year}")
        
        for m in matches:
            match_list.append({
                'match_id': m['id'],
                'utc_date': m['utcDate'],
                'season': season_year,
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
        
        # Wir hängen die Daten an (APPEND), da wir mehrere Saisons sammeln wollen
        # ABER: Wir löschen vorher nur die Daten DIESER Saison, um Dubletten zu vermeiden
        if not df.empty:
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM raw_matches WHERE season = '{season_year}'"))
                conn.commit()
            
            df.to_sql('raw_matches', engine, if_exists='append', index=False)
        
        print(f"✅ Erfolg! {len(df)} Spiele für Saison {season_year} gespeichert.")
        return len(df)
    else:
        print(f"❌ Fehler: {response.status_code}")
        return 0

if __name__ == "__main__":
    ingest_bundesliga_matches()