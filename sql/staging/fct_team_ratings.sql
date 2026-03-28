CREATE OR REPLACE VIEW fct_team_ratings AS
SELECT 
    t.team_name,
    f.season,
    COUNT(f.match_id) AS total_games,
    -- Offensive: Tore pro Spiel
    ROUND(AVG(CASE WHEN f.home_team_id = t.team_id THEN f.goals_home ELSE f.goals_away END), 2) AS goals_per_game,
    -- Defensive: Gegentore pro Spiel
    ROUND(AVG(CASE WHEN f.home_team_id = t.team_id THEN f.goals_away ELSE f.goals_home END), 2) AS goals_conceded_per_game,
    -- Clean Sheets: Wie oft zu Null gespielt?
    SUM(CASE 
        WHEN (f.home_team_id = t.team_id AND f.goals_away = 0) OR (f.away_team_id = t.team_id AND f.goals_home = 0) 
        THEN 1 ELSE 0 
    END) AS clean_sheets
FROM dim_teams t
JOIN fact_matches f ON t.team_id = f.home_team_id OR t.team_id = f.away_team_id
WHERE f.status = 'FINISHED'
GROUP BY t.team_name, f.season
ORDER BY f.season DESC, goals_per_game DESC;