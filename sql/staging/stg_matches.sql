-- Wir bereinigen die Zeitstempel und extrahieren nützliche Infos
CREATE OR REPLACE VIEW stg_matches AS
SELECT 
    match_id,
    CAST(utc_date AS TIMESTAMP) AS match_timestamp,
    matchday,
    status,
    home_team AS home_team_name,
    away_team AS away_team_name,
    CAST(score_home AS INTEGER) AS goals_home,
    CAST(score_away AS INTEGER) AS goals_away,
    winner
FROM raw_matches;