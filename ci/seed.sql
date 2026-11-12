-- Erfundene Testdaten fuer den Deploy-Test in der CI (keine echten Vereine oder Ergebnisse).
-- Wird nach dem Init-Job in die Rohtabellen geladen. Die Views (dim_teams, fct_standings, ...)
-- bauen darauf auf und zeigen die Daten sofort.

INSERT INTO raw_teams (api_id, name, short_name, tla, crest_url, address) VALUES
  (1001, 'FC Testburg',        'Testburg', 'TST', '', ''),
  (1002, 'SV Beispielstadt',   'Beispiel', 'BSP', '', ''),
  (1003, 'Demo United',        'Demo',     'DMO', '', ''),
  (1004, 'Muster 04',          'Muster',   'MUS', '', '');

INSERT INTO raw_matches
  (match_id, utc_date, season, status, matchday, home_team_id, away_team_id,
   home_team, away_team, score_home, score_away, winner) VALUES
  (9001, '2025-08-23T15:30:00Z', '2025', 'FINISHED', 1, 1001, 1002, 'FC Testburg',      'SV Beispielstadt', 2, 1, 'HOME_TEAM'),
  (9002, '2025-08-23T15:30:00Z', '2025', 'FINISHED', 1, 1003, 1004, 'Demo United',      'Muster 04',        0, 0, 'DRAW'),
  (9003, '2025-08-30T15:30:00Z', '2025', 'FINISHED', 2, 1001, 1003, 'FC Testburg',      'Demo United',      1, 1, 'DRAW'),
  (9004, '2025-08-30T15:30:00Z', '2025', 'FINISHED', 2, 1002, 1004, 'SV Beispielstadt', 'Muster 04',        3, 0, 'HOME_TEAM'),
  (9005, '2025-09-06T15:30:00Z', '2025', 'FINISHED', 3, 1004, 1001, 'Muster 04',        'FC Testburg',      0, 2, 'AWAY_TEAM'),
  (9006, '2025-09-06T15:30:00Z', '2025', 'FINISHED', 3, 1002, 1003, 'SV Beispielstadt', 'Demo United',      1, 2, 'AWAY_TEAM');
