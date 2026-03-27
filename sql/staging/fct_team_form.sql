CREATE OR REPLACE VIEW fct_team_form AS
WITH match_results AS (
    -- Wir holen alle beendeten Spiele und bestimmen Sieg, Niederlage oder Unentschieden
    SELECT 
        utc_date,
        home_team_id AS team_id,
        CASE 
            WHEN winner = 'HOME_TEAM' THEN 'W' 
            WHEN winner = 'DRAW' THEN 'D' 
            ELSE 'L' 
        END AS result
    FROM raw_matches WHERE status = 'FINISHED'
    UNION ALL
    SELECT 
        utc_date,
        away_team_id AS team_id,
        CASE 
            WHEN winner = 'AWAY_TEAM' THEN 'W' 
            WHEN winner = 'DRAW' THEN 'D' 
            ELSE 'L' 
        END AS result
    FROM raw_matches WHERE status = 'FINISHED'
),
ranked_matches AS (
    -- Wir nummerieren die Spiele pro Team nach Datum (das aktuellste ist 1)
    SELECT 
        team_id,
        result,
        ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY utc_date DESC) as recency_rank
    FROM match_results
)
-- Wir fassen die letzten 5 Ergebnisse zu einem String zusammen
SELECT 
    t.team_name,
    t.tla,
    STRING_AGG(r.result, '-' ORDER BY r.recency_rank DESC) AS form_trend
FROM ranked_matches r
JOIN dim_teams t ON r.team_id = t.team_id
WHERE r.recency_rank <= 5
GROUP BY t.team_name, t.tla;