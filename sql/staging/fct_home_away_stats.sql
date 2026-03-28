CREATE OR REPLACE VIEW fct_home_away_stats AS
WITH home_stats AS (
    SELECT 
        home_team_id AS team_id,
        season,
        COUNT(*) AS home_games,
        SUM(CASE WHEN winner = 'HOME_TEAM' THEN 3 WHEN winner = 'DRAW' THEN 1 ELSE 0 END) AS home_points,
        SUM(goals_home) AS home_goals_scored,
        SUM(goals_away) AS home_goals_conceded,
        COUNT(CASE WHEN winner = 'HOME_TEAM' THEN 1 END) AS home_wins
    FROM fact_matches
    WHERE status = 'FINISHED'
    GROUP BY home_team_id, season
),
away_stats AS (
    SELECT 
        away_team_id AS team_id,
        season,
        COUNT(*) AS away_games,
        SUM(CASE WHEN winner = 'AWAY_TEAM' THEN 3 WHEN winner = 'DRAW' THEN 1 ELSE 0 END) AS away_points,
        SUM(goals_away) AS away_goals_scored,
        SUM(goals_home) AS away_goals_conceded,
        COUNT(CASE WHEN winner = 'AWAY_TEAM' THEN 1 END) AS away_wins
    FROM fact_matches
    WHERE status = 'FINISHED'
    GROUP BY away_team_id, season
)
SELECT 
    t.team_name,
    h.season,
    h.home_games AS home_matches,
    h.home_points,
    h.home_goals_scored AS home_goals_for,
    h.home_goals_conceded AS home_goals_against,
    h.home_wins,
    ROUND(CAST(h.home_points AS DECIMAL) / h.home_games, 2) AS home_ppg,
    a.away_games AS away_matches,
    a.away_points,
    a.away_goals_scored AS away_goals_for,
    a.away_goals_conceded AS away_goals_against,
    a.away_wins,
    ROUND(CAST(a.away_points AS DECIMAL) / a.away_games, 2) AS away_ppg,
    (h.home_points + a.away_points) AS total_points
FROM dim_teams t
JOIN home_stats h ON t.team_id = h.team_id
JOIN away_stats a ON t.team_id = a.team_id AND h.season = a.season
ORDER BY total_points DESC;