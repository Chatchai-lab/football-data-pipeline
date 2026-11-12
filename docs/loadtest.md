# Lasttest der API mit Locust

Wie viele gleichzeitige Nutzer verkraftet die API, was ist der Engpass, und was bringen mehr Replikas? Gemessen wurde mit [Locust](https://locust.io) im lokalen k3s-Cluster.

## Aufbau

- `loadtest/locustfile.py`: Ein simulierter Nutzer verhält sich wie das Dashboard. Er holt Saisons und Teams und ruft danach die Gold-Endpunkte auf (`/standings` mit Gewicht 5, `/ratings` und `/matches` 3, `/season-trend`, `/team-form` und `/home-away` 2, `/highlights` 1). Zwischen den Aufrufen wartet er 0,5 bis 2 Sekunden.
- `loadtest/run.sh <Nutzer> [Sekunden]`: Startet Locust als **Job im Cluster** (60 Sekunden, 10 neue Nutzer pro Sekunde), zeigt `kubectl top pods` nach zwei Dritteln der Zeit und danach die Ergebnistabelle.
- **Warum im Cluster?** `kubectl port-forward` auf einen Service wählt einen einzelnen Pod und bleibt dabei. Ein Test mit drei Replikas über einen Port-Forward würde nie alle Pods treffen. Der Job spricht den Service `api` an, der wie im Betrieb auf alle Pods verteilt.
- Gemessen wird nur die **API**. Das Dashboard (Streamlit) arbeitet mit WebSockets, die ein reiner HTTP-Test nicht abbildet. Der Test sagt also nichts darüber, wie viele Nutzer gleichzeitig das Dashboard offen haben können.

## Ergebnisse

Die API hat ein CPU-Limit von 250m und ein Speicher-Limit von 128 Mi pro Pod (siehe [kubernetes.md](kubernetes.md)). Jede Zeile ist ein Lauf über 60 Sekunden.

**Vorher** (Verbindungspool 5 + 10, `/health` als normale Funktion):

| Replikas | Nutzer | Anfragen | req/s | Median | p95 | Fehler | API-CPU je Pod |
|---|---|---|---|---|---|---|---|
| 1 | 10 | 497 | 8,4 | 8 ms | 120 ms | 0 | 47m |
| 1 | 50 | 2079 | 34,9 | 55 ms | 790 ms | 0 | 221m |
| 1 | 100 | 441 | – | – | **30 000 ms** | 35 × `500` | Container wurde neu gestartet |

**Nachher** (Verbindungspool 10 + 10 mit 5 s Wartezeit, `/health` async, Überlast als 503):

| Replikas | Nutzer | Anfragen | req/s | Median | p95 | Fehler | API-CPU je Pod |
|---|---|---|---|---|---|---|---|
| 1 | 50 | 2120 | 35,6 | 57 ms | 780 ms | 0 | 200m |
| 1 | 100 | 1950 | 32,7 | 990 ms | 8 200 ms | 92 × `503` (4,7 %) | – |
| 2 | 50 | 2383 | 40,2 | 11 ms | 96 ms | 0 | 137m, 110m |
| 2 | 100 | 4006 | 67,4 | 82 ms | 910 ms | 0 | 171m, **221m** |
| 3 | 50 | 2391 | 40,1 | 10 ms | 64 ms | 0 | 79m, 32m, 99m |
| 3 | 100 | 4512 | 75,9 | 17 ms | **140 ms** | 0 | 157m, 77m, 101m |

Nach allen Läufen standen die API-Pods auf `RESTARTS 0`. Postgres lag bei 100 Nutzern mit zwei Replikas bei 314m und mit drei bei 178m (Limit 500m).

## Was die Zahlen zeigen

1. **Bis 50 Nutzer passt eine Replika**: p95 unter einer Sekunde, keine Fehler. Der Pod liegt aber schon bei 200 bis 221m von 250m CPU.
2. **Bei 100 Nutzern bricht eine Replika ein.** Median 990 ms, p95 8,2 s, 4,7 % Fehler. Der Engpass ist der einzelne Pod, nicht die Datenbank.
3. **Mehr Replikas lösen das.** Bei 100 Nutzern fällt p95 von 8,2 s (1 Pod) über 910 ms (2 Pods, einer bei 221m von 250m) auf **140 ms** (3 Pods, höchstens 157m). Die Last verteilt sich, kein Pod stößt an sein CPU-Limit.
4. **Postgres ist (noch) nicht der Engpass**: Bei drei Replikas nutzt er 178m von 500m. Bei zwei Pods lag er mit 314m schon näher an der Grenze. Mehr Replikas würden irgendwann ihn überlasten, dann brächten sie nichts mehr (siehe Fragen).
5. **Bei 50 Nutzern bringt die Skalierung keinen höheren Durchsatz**, nur kürzere Wartezeiten. Jeder Nutzer wartet 0,5 bis 2 Sekunden und löst deshalb höchstens etwa 0,8 Anfragen pro Sekunde aus. Mit 50 Nutzern sind das rund 40 Anfragen pro Sekunde, egal wie viele Pods es gibt. Der Test misst die Antwortzeit bei vorgegebener Last, nicht die maximale Kapazität.

## Gefundene Engpässe und Verbesserungen

Der erste Lauf mit 100 Nutzern endete mit `500`-Fehlern und Antworten von genau 30 Sekunden. Im Log des API-Containers standen 46 Fehler `QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00`. Außerdem war der Container neu gestartet worden (`RESTARTS 1`, `Liveness probe failed ... context deadline exceeded`). Zwei getrennte Ursachen:

**1. Verbindungspool erschöpft.** SQLAlchemy erlaubt standardmäßig 5 dauerhafte und 10 zusätzliche Verbindungen, also höchstens 15 gleichzeitig. FastAPI führt die normalen Endpunkte in einem Thread-Pool mit 40 Threads aus. Bei 100 Nutzern wollen mehr als 15 Anfragen gleichzeitig eine Verbindung, der Rest wartet bis zu 30 Sekunden (`pool_timeout`) und scheitert dann mit einem 500.

- Der Pool ist jetzt über `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` und `DB_POOL_TIMEOUT` einstellbar. Die **Standardwerte bleiben die alten**, damit die Produktion (Dashboard direkt auf Neon) unverändert bleibt. Nur das API-Deployment im Cluster setzt 10, 10 und 5 Sekunden. Bei drei Replikas sind das höchstens 60 von den 100 Verbindungen, die Postgres standardmäßig erlaubt.
- Ein erschöpfter Pool führt jetzt zu einem **503 mit `Retry-After: 2`** statt zu einem 500 nach langem Warten. Der Prometheus-Zähler `api_pool_timeouts_total` zählt diese Fälle.

**2. Die Liveness-Probe wurde selbst Opfer der Überlast.** `/health` war eine normale Funktion und lief deshalb im selben Thread-Pool wie die Datenbank-Endpunkte. Waren alle Threads mit dem Warten auf eine Verbindung belegt, bekam `/health` keinen Thread, die Probe lief ins Timeout, und Kubernetes startete den Pod neu. Das passiert genau im Moment der höchsten Last und nimmt der API den einzigen Pod weg.

- `/health` ist jetzt `async def` und läuft in der Event-Loop, unabhängig vom Thread-Pool. `/ready` bleibt blockierend, denn es soll bei Überlast „nicht bereit“ melden.

**Wirkung** (1 Replika, 100 Nutzer):

| | vorher | nachher |
|---|---|---|
| bediente Anfragen in 60 s | 441 | 1950 |
| Fehler | 35 × `500` | 92 × `503` |
| längste Antwort | 30 s | 15 s |
| Neustart durch die Liveness-Probe | ja | nein |

Die Überlast selbst bleibt bei einer einzelnen Replika bestehen, hier hilft nur mehr Kapazität: Mit drei Replikas lag p95 bei 140 ms ohne einen Fehler. Weitere Maßnahmen wären ein höheres CPU-Limit pro Pod oder eine Zwischenspeicherung der Antworten in der API (die Gold-Views ändern sich nur nach einem Pipeline-Lauf). Sie sind nicht umgesetzt oder gemessen.

## Grenzen des Tests

- Locust, die API-Pods, Postgres, Dashboard und Prometheus laufen auf **derselben Maschine** (vier Kerne). Sie konkurrieren um die CPU, die Messung ist keine saubere Laborsituation.
- Jeder Lauf wurde **einmal** gemessen. Die Werte schwanken, besonders die höheren Perzentile.
- `kubectl top` liefert Mittelwerte über ein Zeitfenster, das nicht exakt zum Test passt. Ein Wert (41m bei 100 Nutzern, 1 Replika) passte nicht zum Durchsatz und wurde nicht verwendet.
- Die Datenbank enthält die echten Bundesliga-Daten, aber wenige Zeilen. Bei sehr viel größeren Datenmengen würden die Abfragen langsamer und die Datenbank früher zum Engpass.
- Die ersten Aufrufe jedes Nutzers (`/seasons`, `/teams`) sind langsamer (kalte Verbindungen) und fließen in die Gesamtwerte ein.

## Verständnisfragen

**Warum ist p95 aussagekräftiger als der Durchschnitt?** Der Durchschnitt versteckt Ausreißer. Beim Lauf mit einer Replika und 50 Nutzern lag der Durchschnitt bei 184 ms und der Median bei 57 ms, die 95. Perzentile aber bei 780 ms: Jeder zwanzigste Nutzer wartete fast eine Sekunde. Wer nur den Durchschnitt betrachtet, sieht das nicht. Bei 100 Nutzern und einer Replika waren es 8,2 s bei einem Durchschnitt von 1,6 s.

**Warum bringen mehr API-Replikas nichts, wenn die Datenbank der Engpass ist?** Alle Replikas teilen sich dieselbe Datenbank. Ist sie ausgelastet (CPU, Verbindungen, Festplatte), warten die zusätzlichen Pods genauso auf sie, und jeder neue Pod bringt weitere Verbindungen mit, die sie noch stärker belasten. Hier lag Postgres bei drei Replikas bei 178m von 500m und war nicht der Engpass, deshalb halfen mehr Replikas. Wäre er es gewesen, hätte man die Datenbank verbessern müssen (Index, Antworten zwischenspeichern, Lesereplikate).
