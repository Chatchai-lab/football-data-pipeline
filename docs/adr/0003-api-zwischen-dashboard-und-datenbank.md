# 0003: API als Zwischenschicht zwischen Dashboard und Datenbank

**Status:** angenommen

## Kontext
Das Dashboard las ursprünglich direkt aus der Datenbank und brauchte dafür Zugangsdaten und SQL-Code im Image.

## Entscheidung
Eine FastAPI-Anwendung liest die Gold-Views und liefert sie als JSON. Das Dashboard spricht nur mit der API. Beide laufen als eigene Deployments. Das Dashboard hat zwei Betriebsarten: Mit `API_URL` nutzt es die API, ohne direkt die Datenbank (so läuft die Produktion weiter).

## Alternativen
- **Direktzugriff beibehalten:** weniger Teile, aber Zugangsdaten und Datenbank-Code in der Dashboard-Oberfläche.
- **GraphQL oder Datenbank-Proxy:** mehr Aufwand ohne klaren Nutzen für zwölf feste Abfragen.

## Begründung
- Das Dashboard-Image enthält keine Datenbank-Zugangsdaten mehr.
- Die API nutzt eine Read-only-Rolle (`api_ro`) mit `SELECT` auf genau die benötigten Views (Least Privilege).
- API und Dashboard lassen sich getrennt skalieren und testen. Die API hat eigene Probes (`/health`, `/ready`).
- Der Dual-Mode-Betrieb hält die Produktion unverändert.

## Folgen
Ein zusätzlicher Dienst und ein Netzwerkhop. Das Dashboard cached Antworten (`st.cache_data`, fünf Minuten). Eine NetworkPolicy, die nur der API den Zugriff auf Postgres erlaubt, ist noch nicht eingerichtet.
