CREATE OR REPLACE VIEW fct_standings AS
WITH team_stats AS (
    -- Heimspiele auswerten
    SELECT 
        season,
        home_team_id AS team_id,
        CASE 
            WHEN winner = 'HOME_TEAM' THEN 3
            WHEN winner = 'DRAW' THEN 1
            ELSE 0
        END AS points,
        goals_home AS goals_for,
        goals_away AS goals_against,
        1 AS match_count
    FROM fact_matches
    WHERE status = 'FINISHED'
    
    UNION ALL
    
    -- Auswärtsspiele auswerten
    SELECT 
        season,
        away_team_id AS team_id,
        CASE 
            WHEN winner = 'AWAY_TEAM' THEN 3
            WHEN winner = 'DRAW' THEN 1
            ELSE 0
        END AS points,
        goals_away AS goals_for,
        goals_home AS goals_against,
        1 AS match_count
    FROM fact_matches
    WHERE status = 'FINISHED'
)
SELECT 
    s.season,
    t.team_name,
    t.tla, -- Kürzel (z.B. FCB, BVB)
    SUM(s.match_count) AS matches_played,
    SUM(s.points) AS total_points,
    SUM(s.goals_for) AS total_goals_for,
    SUM(s.goals_against) AS total_goals_against,
    (SUM(s.goals_for) - SUM(s.goals_against)) AS goal_diff,
    -- Ein neuer KPI: Punkte pro Spiel (Effizienz)
    ROUND(CAST(SUM(s.points) AS DECIMAL) / SUM(s.match_count), 2) AS points_per_match
FROM team_stats s
JOIN dim_teams t ON s.team_id = t.team_id
GROUP BY s.season, t.team_name, t.tla
ORDER BY s.season DESC,total_points DESC, goal_diff DESC;