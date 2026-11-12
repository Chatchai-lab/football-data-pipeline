# 0002: Postgres im Cluster nur für Entwicklung und Test, Neon in Produktion

**Status:** angenommen

## Kontext
Die Produktion läuft auf Render mit einer Neon-Datenbank. Im Cluster wird ebenfalls eine Datenbank gebraucht, um das Zusammenspiel von Pipeline, API und Dashboard zu üben und zu testen.

## Entscheidung
Im Cluster läuft PostgreSQL als einzelner Pod (Deployment mit PersistentVolumeClaim und Strategie `Recreate`). Er dient nur Entwicklung und Test. Produktion bleibt bei Neon.

## Alternativen
- **StatefulSet:** der übliche Weg für Datenbanken, hier aber ohne Replikation kein Gewinn.
- **Datenbank-Operator (zum Beispiel CloudNativePG):** bringt Backups und Failover, für ein Lernprojekt unverhältnismäßig.
- **Neon auch aus dem Cluster nutzen:** Tests würden die Produktionsdaten berühren.

## Begründung
Ein einzelner Pod reicht für den Zweck. Die Produktion wird vom Cluster-Experiment getrennt, und der Init-Job (`check_target`) bricht ab, wenn er auf einen anderen Host als `localhost` oder `postgres` zeigt. So kann er Neon nicht versehentlich verändern.

## Folgen
Keine Replikation, keine Backups. Ein Pod-Ausfall bedeutet kurze Downtime. Die Daten bleiben auf dem Volume erhalten. Echte Daten gehören nicht in Repo oder Image, sie werden lokal geladen.
