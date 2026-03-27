CREATE OR REPLACE VIEW fct_home_away_stats AS
WITH home_stats AS (
    SELECT 
        home_team_id AS team_id,
        COUNT(*) AS home_games,
        SUM(CASE WHEN winner = 'HOME_TEAM' THEN 3 WHEN winner = 'DRAW' THEN 1 ELSE 0 END) AS home_points,
        SUM(goals_home) AS home_goals_scored,
        SUM(goals_away) AS home_goals_conceded
    FROM fact_matches
    WHERE status = 'FINISHED'
    GROUP BY home_team_id
),
away_stats AS (
    SELECT 
        away_team_id AS team_id,
        COUNT(*) AS away_games,
        SUM(CASE WHEN winner = 'AWAY_TEAM' THEN 3 WHEN winner = 'DRAW' THEN 1 ELSE 0 END) AS away_points,
        SUM(goals_away) AS away_goals_scored,
        SUM(goals_home) AS away_goals_conceded
    FROM fact_matches
    WHERE status = 'FINISHED'
    GROUP BY away_team_id
)
SELECT 
    t.team_name,
    h.home_games,
    h.home_points,
    ROUND(CAST(h.home_points AS DECIMAL) / h.home_games, 2) AS home_ppg, -- Points Per Game Home
    a.away_games,
    a.away_points,
    ROUND(CAST(a.away_points AS DECIMAL) / a.away_games, 2) AS away_ppg, -- Points Per Game Away
    (h.home_points + a.away_points) AS total_points
FROM dim_teams t
LEFT JOIN home_stats h ON t.team_id = h.team_id
LEFT JOIN away_stats a ON t.team_id = a.team_id
ORDER BY total_points DESC;