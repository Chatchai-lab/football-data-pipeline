CREATE OR REPLACE VIEW stg_standings AS
WITH match_points AS (
    -- Punkte für das Heimteam
    SELECT 
        home_team_name AS team_name,
        CASE 
            WHEN winner = 'HOME_TEAM' THEN 3
            WHEN winner = 'DRAW' THEN 1
            ELSE 0
        END AS points,
        goals_home AS goals_for,
        goals_away AS goals_against
    FROM stg_matches
    WHERE status = 'FINISHED'
    
    UNION ALL
    
    -- Punkte für das Auswärtsteam
    SELECT 
        away_team_name AS team_name,
        CASE 
            WHEN winner = 'AWAY_TEAM' THEN 3
            WHEN winner = 'DRAW' THEN 1
            ELSE 0
        END AS points,
        goals_away AS goals_for,
        goals_home AS goals_against
    FROM stg_matches
    WHERE status = 'FINISHED'
)
SELECT 
    team_name,
    COUNT(*) AS matches_played,
    SUM(points) AS total_points,
    SUM(goals_for) AS total_goals_for,
    SUM(goals_against) AS total_goals_against,
    (SUM(goals_for) - SUM(goals_against)) AS goal_diff
FROM match_points
GROUP BY team_name
ORDER BY total_points DESC, goal_diff DESC;