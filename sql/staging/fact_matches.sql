CREATE OR REPLACE VIEW fact_matches AS
SELECT 
    match_id,
    CAST(utc_date AS TIMESTAMP) AS match_timestamp,
    season,
    matchday,
    status,
    home_team_id, 
    away_team_id,
    CAST(score_home AS INTEGER) AS goals_home,
    CAST(score_away AS INTEGER) AS goals_away,
    winner
FROM raw_matches;