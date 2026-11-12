# Monitoring mit Prometheus

Die Manifeste liegen in `k8s/monitoring/` und werden mit `kubectl apply -k k8s/monitoring` angewendet (nach `kubectl apply -k k8s`). Sie bestehen aus Prometheus (mit ServiceAccount und Leserechten), einem Pushgateway und der Scrape-Konfiguration als ConfigMap. Der Speicher von Prometheus ist ein `emptyDir`: Die Messwerte gehen beim Neustart des Pods verloren, das genügt für Entwicklung.

## Zwei Wege, Messwerte einzusammeln

| | API | Pipeline |
|---|---|---|
| Prinzip | **Pull**: Prometheus holt alle 15 s `/metrics` ab | **Push**: Der Lauf schickt am Ende sein Ergebnis an das Pushgateway |
| Warum | Die API läuft dauerhaft und kann jederzeit gefragt werden | Der Pod ist nach dem Lauf weg, Prometheus könnte ihn nicht mehr abfragen |
| Gefunden über | Service Discovery über die Kubernetes-API (`role: endpoints`) | fester Eintrag auf `pushgateway:9091` |

Die Service Discovery liefert **jeden Pod einzeln** (zwei Ziele für zwei API-Pods) und erkennt neue Pods automatisch. Würde Prometheus den Service `api` direkt abfragen, bekäme er bei jedem Abruf einen zufälligen Pod. Dafür braucht Prometheus eine Rolle, die Endpunkte und Pods im Namespace lesen darf (`prometheus-rbac.yaml`).

## Metriken der API (`/metrics`)

| Metrik | Typ | Zweck |
|---|---|---|
| `http_requests_total{method,path,status}` | Counter | Anfragen und Fehlerrate (`rate()`) |
| `http_request_duration_seconds{method,path}` | Histogram | Antwortzeiten, Perzentile mit `histogram_quantile()` |
| `http_requests_in_progress` | Gauge | Anfragen, die gerade laufen |
| `api_database_errors_total` | Counter | Anfragen, die mit 503 wegen der Datenbank endeten |

- Das Label `path` enthält die **Route** (`/standings`), nicht die konkrete URL. Unbekannte Pfade werden als `unmatched` zusammengefasst, sonst würde jeder Tippfehler und jeder Scanner eine neue Zeitreihe erzeugen (Kardinalität).
- `/metrics` zählt sich selbst nicht mit.

## Metriken der Pipeline (Pushgateway)

`matchlytics_pipeline_duration_seconds`, `_teams_loaded`, `_matches_loaded`, `_errors`, `_last_run_timestamp_seconds` und `_last_success_timestamp_seconds`, alle als **Gauge** mit dem Label `job="matchlytics_pipeline"`.

- **Warum Gauges statt Counter und Histogram?** Das Pushgateway behält immer nur den zuletzt gepushten Wert. Ein Counter würde bei jedem Lauf wieder bei null beginnen, ein Histogram mit einem Messwert pro Lauf sagt nichts aus. Für „Ergebnis des letzten Laufs“ ist ein Gauge der passende Typ. Das weicht bewusst vom ursprünglichen Issue-Text ab.
- **`pushadd` statt `push`:** `pushadd_to_gateway` ersetzt nur die gesendeten Metriken. So bleibt `last_success_timestamp` erhalten, wenn ein späterer Lauf fehlschlägt. Daraus lässt sich ein Alarm „zu lange kein Erfolg“ bauen.
- Der Push läuft nur, wenn `PUSHGATEWAY_URL` gesetzt ist. Ein Fehler beim Pushen bricht die Pipeline nie ab (nur eine Warnung im Log). `prometheus-client` steht nur in `requirements-api.txt` und `requirements-pipeline.txt`, nicht in `requirements.txt` (das baut Render), die Produktion bleibt unverändert.

## Beobachtet

- Beide API-Pods erschienen als Ziele von `matchlytics-api`, dazu das Pushgateway, alle `UP`.
- `sum by (path, status) (rate(http_requests_total[5m]))` zeigte `/ready` mit rund **0,2** und `/health` mit rund **0,09** Anfragen pro Sekunde, ohne dass jemand Last erzeugt hatte. Das sind die Probes von Kubernetes: zwei Pods, Readiness alle 10 s (2 × 0,1) und Liveness alle 20 s (2 × 0,05). Die Zahlen bestätigen die Probe-Konfiguration aus dem Abschnitt „Probes und Ressourcen“.
- Die 95. Perzentile der Antwortzeit lag bei `/ready` bei etwa **9 ms** (fragt die Datenbank) und bei `/health` bei etwa **5 ms**.
- Nach zwei Lastläufen zeigte `increase(http_requests_total{path=~"/standings|unmatched"}[30m])` je etwa **122** Anfragen für `/standings` (200) und `unmatched` (404).
- `matchlytics_pipeline_matches_loaded` lieferte nach einem Test-Push **306**.

**Stolperstein: neue Zeitreihen.** Direkt nach dem ersten Lastlauf zeigten `/standings` und `unmatched` bei `rate()` den Wert 0 und bei `histogram_quantile` `NaN`. Die Zeitreihen waren erst während des Laufs entstanden, vor dem ersten Abruf gab es keinen Messpunkt, aus dem eine Änderung berechnet werden kann. Erst ab dem zweiten Messpunkt rechnet Prometheus. Ebenso liefert `rate(...[1m])` 0, wenn die Last länger als eine Minute her ist.

## Verständnisfragen

**Warum kann Prometheus einen kurzlebigen Pipeline-Step nicht einfach selbst abfragen?** Prometheus holt Werte in festen Abständen (hier alle 15 s) per HTTP ab. Ein Pipeline-Pod läuft vielleicht nur eine Minute und ist danach beendet. Er hat bis dahin womöglich nie einen Abruf erlebt, und danach gibt es niemanden mehr, den man fragen könnte. Das Pushgateway zwischenspeichert das Ergebnis, bis Prometheus es abholt.

**Warum ist ein Histogram für Antwortzeiten besser als ein Gauge mit dem Durchschnitt?** Ein Durchschnitt versteckt Ausreißer: Neunundneunzig Anfragen mit 10 ms und eine mit 5 s ergeben rund 60 ms, und niemand sieht, dass ein Prozent der Nutzer fünf Sekunden wartet. Ein Histogram zählt, wie viele Anfragen in welche Zeitklasse fielen. Daraus berechnet Prometheus beliebige Perzentile (`histogram_quantile`), und das auch über mehrere Pods hinweg. Ein Durchschnitt pro Pod lässt sich dagegen nicht sinnvoll zusammenfassen.
