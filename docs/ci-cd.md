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
