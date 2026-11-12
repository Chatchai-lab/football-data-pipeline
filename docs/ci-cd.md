# CI/CD: Tests und Images mit GitHub Actions

Der Workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) läuft bei jedem Pull Request und bei jedem Push auf `main`. Er ersetzt den früheren Workflow `python-app.yml` (flake8 und Import-Check sind übernommen, dazu kommen `pytest` und die Image-Builds). Der nächtliche Workflow `pipeline.yml` ist unverändert.

## Ablauf

| Job | Wann | Was |
|---|---|---|
| `test` | PR und Push auf `main` | Abhängigkeiten installieren, flake8, Import-Check, `pytest` |
| `build` | nach `test` (`needs: test`) | drei Images bauen: `api`, `dashboard`, `pipeline` |

- Schlägt `test` fehl, startet `build` nicht: Es entsteht kein Image aus ungetestetem Code.
- `build` ist eine **Matrix** über die drei Namen. Ein Job-Template baut je ein Image aus `Dockerfile.<name>`. `fail-fast: false` lässt die anderen Builds weiterlaufen, wenn einer scheitert.
- **Pull Requests** bauen nur, sie pushen nichts und loggen sich nicht bei Docker Hub ein. Bei Fork-PRs gibt es ohnehin keine Secrets. Gepusht wird nur beim Push auf `main` (`push: ${{ github.event_name == 'push' }}`).
- `permissions: contents: read` begrenzt die Rechte des Workflow-Tokens auf Lesen. `concurrency` bricht einen noch laufenden Lauf desselben Branches ab, wenn ein neuer Push kommt.

## Tests in der CI

`requirements.txt` enthält pytest und die Pipeline- und Dashboard-Pakete, aber nicht FastAPI. Die API-Tests brauchen zusätzlich `requirements-api.txt` und `httpx` (FastAPIs `TestClient`).

In der CI gibt es keine Datenbank. Der Integritätstest `test_check_finished_matches_have_scores` fragt eine echte Datenbank ab und wird deshalb **übersprungen**, wenn keine Verbindung möglich ist (Fixture `db_engine`). Mit erreichbarer Datenbank, etwa lokal, läuft er wie bisher. Ergebnis ohne Datenbank: 98 Tests grün, 2 übersprungen.

## Container Registry und Tags

Eine **Registry** ist ein Speicher für Images, vergleichbar mit einem App Store. Bei Docker Hub heißt ein Image `<benutzer>/<repository>:<tag>`. Hier: `<benutzer>/matchlytics-api`, `-dashboard` und `-pipeline`.

Jedes Image bekommt zwei Tags (über `docker/metadata-action`):

- `<commit-sha>`: die volle Commit-ID. Sie ist unveränderlich und verweist auf genau einen Stand des Codes.
- `latest`: der jeweils neueste Stand von `main`. Bequem, aber beweglich: Welche Version dahintersteckt, sieht man dem Tag nicht an.

**Tag oder Digest?** Ein Tag ist ein Name, der auf ein anderes Image zeigen kann (etwa wenn `latest` neu gepusht wird). Der **Digest** (`sha256:…`) ist der Hash des Image-Inhalts und ändert sich nie. Wer exakt dasselbe Image wieder verwenden will (Produktion, Reproduzierbarkeit), referenziert den Digest oder einen Commit-Tag.

**Woher weiß man bei einem Fehler in Produktion, welcher Code im Image steckt?** Aus dem Tag: Er enthält die Commit-ID, und mit `git show <sha>` sieht man den Code. Bei `latest` allein wäre das nicht möglich.

## Secrets

Der Workflow nutzt die Repository-Secrets `DOCKERHUB_USERNAME` und `DOCKERHUB_TOKEN`. Im Repo steht kein Zugangsdatum, im Log erscheinen die Werte maskiert. Das **Access Token** ist besser als das Passwort, weil es nur die nötigen Rechte hat (Read und Write auf Repositories), jederzeit einzeln widerrufen werden kann und nicht für den Login in die Weboberfläche oder Kontoeinstellungen taugt. Bei einem Leck verliert man ein Token, nicht das Konto.

## Cache

`cache-from` und `cache-to` mit `type=gha` legen die Docker-Layer im Cache von GitHub Actions ab, getrennt pro Image (`scope`). Unveränderte Schichten (zum Beispiel `pip install`) werden bei späteren Läufen nicht neu gebaut.

## Pull-Limits

Docker Hub begrenzt anonyme Pulls pro Zeitraum. Die Builds ziehen die Basis-Images (`python:3.12-slim`) und sind davon betroffen, wenn sehr oft gebaut wird. Mit dem Login (nur auf `main`) gelten höhere Limits. Die gebauten Images bleiben beim Cluster-Import lokal, k3s braucht sie nicht aus der Registry zu ziehen, solange `imagePullPolicy: IfNotPresent` und ein lokales Image genutzt werden.

## Deploy-Test in k3d (Continuous Delivery)

Der Job `deploy-test` startet auf dem Runner einen kurzlebigen **k3d-Cluster** (k3s in Docker, dieselbe Distribution wie lokal, feste Version v5.8.3), rollt Matchlytics mit den frisch gebauten Images aus und prüft die Anwendung. Danach wird der Cluster gelöscht. Es entstehen keine Kosten und es ist kein dauerhafter Cluster nötig.

Ablauf:

1. Die drei Images werden mit demselben Dockerfile und Layer-Cache wie im Job `build` gebaut, aber nur lokal geladen (`load: true`), und mit der Commit-ID getaggt. So testet auch ein Pull Request seinen eigenen Code.
2. `k3d image import` bringt sie in den Cluster. `imagePullPolicy: IfNotPresent` sorgt dafür, dass nichts aus einer Registry gezogen wird.
3. Ein **Secret mit Wegwerf-Werten** (`openssl rand`) entsteht nur im Lauf. Es steht nirgends im Repo.
4. **Kustomize** bündelt die Manifeste (`k8s/kustomization.yaml`). Das Overlay `ci/kustomization.yaml` setzt die Image-Tags auf die Commit-ID. Ein Overlay muss außerhalb des Ordners seiner Basis liegen, sonst meldet Kustomize `cycle detected`.
5. Reihenfolge: Postgres → Init-Job (Tabellen, Views, Rolle `api_ro`) → **erfundene Testdaten** (`ci/seed.sql`) → API und Dashboard. Der Init-Job lädt selbst keine Daten, die echten Daten von football-data.org gehören nicht ins Repo.
6. **Smoke Test** per `port-forward`: `/ready` der API, `/standings?season=2025` muss genau vier Teams mit `FC Testburg` an der Spitze liefern (mit `jq` geprüft), `/_stcore/health` des Dashboards. Der Test beweist, dass Daten durch die ganze Kette laufen: Postgres → Views → API → Service.
7. Bei einem Fehler schreibt der Schritt `Diagnostics` Pod-Status, `describe`, Logs und Events ins Actions-Log (`if: failure()`).

**Unterschied zum Issue:** Das Issue sieht vor, die Images aus Docker Hub per Commit-ID zu ziehen. Der Test baut sie stattdessen lokal im Job. Das ist schneller, braucht keine Secrets und funktioniert auch bei Pull Requests, die nichts pushen. Die Images sind aber nicht Bit für Bit die gepushten. Die Variante mit dem Pull aus Docker Hub wäre der nächste Schritt für einen echten Release-Prozess.

### Verständnisfragen

**Was ist der Unterschied zwischen Continuous Delivery und Continuous Deployment?** Bei Continuous Delivery ist jede Änderung jederzeit auslieferbar, getestet und ausgerollt in eine Testumgebung. Der Schritt in Produktion bleibt eine bewusste Entscheidung. Bei Continuous Deployment geht jede grüne Änderung automatisch in Produktion.

**Warum reicht „alle Pods sind Running“ als Test nicht?** `Running` heißt nur, dass der Container läuft. Er kann trotzdem nicht mit der Datenbank sprechen, falsche Daten liefern oder keine Daten haben. Der Smoke Test fragt echte Daten über die API ab.

**Was fehlt noch, um in einen echten Cluster auszurollen?** Ein dauerhafter Cluster mit Zugang aus der CI (zum Beispiel ein `kubeconfig` als Secret), echte Secrets (extern verwaltet, etwa Sealed Secrets oder ein Secret-Manager), Persistenz und Backups für die Datenbank, Images aus der Registry mit Commit-ID oder Digest, ein Rollback-Plan und eine Freigabe vor Produktion.
