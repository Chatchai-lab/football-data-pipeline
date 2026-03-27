CREATE OR REPLACE VIEW dim_teams AS
SELECT 
    api_id AS team_id,
    name AS team_name,
    short_name,
    tla,
    crest_url,
    address
FROM raw_teams;