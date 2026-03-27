CREATE OR REPLACE VIEW fct_season_trend AS
WITH match_points AS (
    SELECT 
        matchday,
        home_team_id AS team_id,
        CASE WHEN winner = 'HOME_TEAM' THEN 3 WHEN winner = 'DRAW' THEN 1 ELSE 0 END AS points
    FROM fact_matches
    UNION ALL
    SELECT 
        matchday,
        away_team_id AS team_id,
        CASE WHEN winner = 'AWAY_TEAM' THEN 3 WHEN winner = 'DRAW' THEN 1 ELSE 0 END AS points
    FROM fact_matches
)
SELECT 
    t.team_name,
    m.matchday,
    -- Hier passiert die Magie: Laufende Summe über die Spieltage
    SUM(m.points) OVER (PARTITION BY t.team_name ORDER BY m.matchday) AS cumulative_points
FROM match_points m
JOIN dim_teams t ON m.team_id = t.team_id
ORDER BY t.team_name, m.matchday;