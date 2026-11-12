# Kubernetes: Notizen

Diese Datei hält fest, wie Matchlytics lokal auf Kubernetes läuft und was die wichtigsten Begriffe bedeuten.

## Grundbegriffe

| Begriff | Bedeutung |
|---|---|
| **Cluster** | Die Gesamtheit aus Rechnern, auf denen Kubernetes Container ausführt und steuert. |
| **Node** | Ein einzelner Rechner im Cluster. Lokal ist es ein Node (der eigene Rechner), er steuert den Cluster (`control-plane`) und führt gleichzeitig Pods aus. |
| **Pod** | Die kleinste Einheit in Kubernetes: ein oder mehrere Container, die zusammen laufen und sich eine IP teilen. |
| **Namespace** | Ein abgetrennter Bereich im Cluster, wie ein Ordner. Matchlytics liegt im Namespace `matchlytics`, die Systemdienste in `kube-system`. |
| **kubectl** | Das Kommandozeilenprogramm, mit dem man den Cluster steuert. |
| **kubeconfig** | Eine Datei (`~/.kube/config`) mit der Adresse des Clusters und den Zugangsschlüsseln. Wer sie hat, hat Vollzugriff auf den Cluster. Deshalb gehört sie nie ins Git. |

## Deklarativ statt imperativ

Kubernetes arbeitet **deklarativ**: Man beschreibt den Wunschzustand ("es soll ein Namespace `matchlytics` geben"), Kubernetes sorgt dafür, dass er eintritt und bleibt.

| Befehl | Art | Wirkung |
|---|---|---|
| `kubectl apply -f datei.yaml` | deklarativ | Bringt den Cluster in den Zustand, den die Datei beschreibt. Beliebig oft wiederholbar (`created`, dann `unchanged`). |
| `kubectl run test --image=nginx` | imperativ | Startet sofort einen einzelnen Pod. Es gibt keinen Wunschzustand, der danach überwacht wird. |

Ein mit `kubectl run` gestarteter Pod kommt nach dem Löschen **nicht** zurück, weil niemand festgelegt hat, dass er laufen soll. Ein Deployment (kommt später) legt genau das fest und startet gelöschte Pods automatisch neu (Self-Healing).

## Lokaler Cluster: k3s

Installiert wurde k3s mit dem offiziellen Skript von `https://get.k3s.io` (vorher heruntergeladen und gelesen). k3s läuft als Systemdienst (`systemctl status k3s`) und nutzt `containerd` statt Docker.

Die kubeconfig liegt nach der Installation in `/etc/rancher/k3s/k3s.yaml` und ist nur für Root lesbar. Sie wurde nach `~/.kube/config` kopiert (Besitzer angepasst, `chmod 600`). Da k3s ein eigenes `kubectl` unter `/usr/local/bin` mitbringt, das standardmäßig die Root-Datei liest, zeigt die Umgebungsvariable `KUBECONFIG=$HOME/.kube/config` (in `~/.bashrc`) auf die eigene Kopie.

### Nützliche Befehle

| Befehl | Zeigt |
|---|---|
| `kubectl get nodes` | Die Nodes und ihren Status (`Ready`). |
| `kubectl get namespaces` | Alle Namespaces. |
| `kubectl get pods -A` | Alle Pods in allen Namespaces (`-A` = `--all-namespaces`). |
| `kubectl get pods -n kube-system -o wide` | Pods eines Namespace mit IP und Node. |
| `kubectl get storageclass` | Verfügbare Speicherklassen. |
| `kubectl port-forward pod/NAME 8080:80 -n NS` | Leitet einen lokalen Port in einen Pod, um ihn von außen zu testen. |

### Systemdienste in `kube-system`

| Pod | Aufgabe |
|---|---|
| `coredns` | Cluster-interner DNS: löst Dienstnamen zu IPs auf. |
| `traefik` | Ingress: nimmt Web-Anfragen an und leitet sie an Dienste weiter. |
| `svclb-traefik` | Gibt dem Traefik-Service die IP des Rechners (k3s-eigener LoadBalancer). |
| `local-path-provisioner` | Stellt Speicher (Volumes) als Ordner auf dem Node bereit. |
| `metrics-server` | Liefert CPU- und RAM-Werte für `kubectl top`. |
| `helm-install-*` | Einmalige Jobs, die Traefik per Helm installiert haben (Status `Completed`). |

Die Standard-StorageClass heißt `local-path` (`rancher.io/local-path`, Binding `WaitForFirstConsumer`, Reclaim-Policy `Delete`).

### Datenablage und Deinstallation

k3s legt seinen Zustand unter `/var/lib/rancher/k3s` ab: Datenbank, Zertifikate, Images und die Daten der `local-path`-Volumes. Das Skript `/usr/local/bin/k3s-uninstall.sh` entfernt k3s samt aller Daten.

## k3s, k3d und kind

| Werkzeug | Was ist es? | Wo läuft es? | Wofür? |
|---|---|---|---|
| **k3s** | Schlanke, zertifizierte Kubernetes-Distribution | Als Systemdienst direkt auf Linux, Container über `containerd` | Dauerhafter lokaler Cluster |
| **k3d** | Hilfsprogramm, das k3s in Docker-Containern startet | In Docker | Kurzlebige Cluster, die sich schnell starten und wegwerfen lassen |
| **kind** | "Kubernetes in Docker": der Standard-Kubernetes, jeder Node ein Docker-Container | In Docker | Kubernetes selbst und Tools dafür testen |

**Warum k3s lokal und k3d in der CI?** Lokal soll der Cluster dauerhaft laufen und Daten behalten, deshalb k3s als Systemdienst. In der CI braucht jeder Lauf einen frischen, sauberen Cluster, der danach wieder verschwindet. k3d startet dafür dieselbe k3s-Distribution in Docker, das Verhalten bleibt also vergleichbar.

## Konfiguration: ConfigMap und Secret

Matchlytics liest seine Einstellungen aus Umgebungsvariablen. In Kubernetes werden sie nicht ins Image gebaut, sondern beim Start in den Pod eingespielt. Dabei trennt man zwei Arten:

| | ConfigMap | Secret |
|---|---|---|
| Inhalt | Normale Einstellungen (`LOG_LEVEL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_SSLMODE`, `API_URL`) | Geheimnisse (`DB_USER`, `DB_PASSWORD`, `FOOTBALL_API_KEY`) |
| Datei im Repo | `k8s/configmap.yaml` | nur `k8s/secret.example.yaml` mit Platzhaltern |
| Im Git? | ja | **nie** das echte Secret (`k8s/secret.yaml` steht in `.gitignore`) |

Das echte Secret entsteht lokal aus einer Datei außerhalb des Repos, mit eigenen Werten für den Cluster (nicht die der Produktion):

```bash
kubectl create secret generic matchlytics-secrets --from-env-file=$HOME/matchlytics-cluster.env -n matchlytics
```

### Base64 ist kein Schutz

Ein Secret speichert seine Werte nur Base64-kodiert, nicht verschlüsselt. Jeder, der es lesen darf, dekodiert es sofort:

```bash
kubectl get secret matchlytics-secrets -n matchlytics -o jsonpath='{.data.DB_USER}' | base64 -d
```

Der Vorteil eines Secrets liegt woanders: Die Werte stehen nicht im Image und nicht im Git, und der Zugriff lässt sich getrennt von der ConfigMap steuern (RBAC). Wer Secrets lesen darf, bestimmt man über Rollen im Cluster. Zum sicheren Verwalten im Git gibt es Werkzeuge wie Sealed Secrets oder SOPS.

### Werte in den Pod bringen

Mit `envFrom` wird jeder Eintrag einer ConfigMap oder eines Secrets zu einer Umgebungsvariable:

```yaml
envFrom:
  - configMapRef:
      name: matchlytics-config
  - secretRef:
      name: matchlytics-secrets
```

Einzelne Werte lassen sich mit `valueFrom` auswählen. `k8s/debug-pod.yaml` ist ein Wegwerf-Pod, um das zu prüfen (`kubectl exec debug -n matchlytics -- env`). Er bleibt nicht dauerhaft im Cluster.

### Was passiert bei einer Änderung?

Beobachtet mit `kubectl patch configmap ... LOG_LEVEL=DEBUG` und einem laufenden Pod:

| Einbindung | Nach der Änderung |
|---|---|
| Umgebungsvariable (`envFrom`) | Bleibt beim alten Wert (`INFO`). Der Wert wird beim Start des Containers festgelegt, erst ein Neustart des Pods übernimmt den neuen. |
| Als Datei eingebundenes Volume | Wird nach etwa einer Minute im laufenden Pod aktualisiert (`DEBUG`). Die Anwendung muss die Datei aber selbst neu lesen. |

Die Datei `k8s/configmap.yaml` ist der Sollzustand. Eine Änderung per `patch` gilt nur im Cluster und wird mit `kubectl apply -f k8s/configmap.yaml` wieder überschrieben.


## PostgreSQL im Cluster

Für Entwicklung und CI läuft eine eigene PostgreSQL im Cluster, die Produktion bleibt bei Neon. Dateien: `k8s/postgres-pvc.yaml`, `k8s/postgres.yaml`, `k8s/postgres-service.yaml`.

### Bausteine

| Ressource | Aufgabe |
|---|---|
| **PersistentVolumeClaim (PVC)** | Antrag auf Speicher (`1Gi`, `ReadWriteOnce`). Ohne `storageClassName` gilt die Standardklasse `local-path`. |
| **PersistentVolume (PV)** | Der tatsächlich angelegte Speicher. `local-path` erzeugt ihn automatisch als Ordner unter `/var/lib/rancher/k3s/storage/` auf dem Node. |
| **Deployment** | Beschreibt, wie Postgres läuft: `postgres:15`, `replicas: 1`, Volume auf `/var/lib/postgresql/data`. |
| **Service `postgres`** | Stabiler Name und feste IP (`ClusterIP`, Port 5432) für den Pod, der das Label `app: postgres` trägt. |

Das PVC bleibt `Pending`, bis ein Pod es nutzt (`WaitForFirstConsumer`), dann wird es `Bound`.

### Wichtige Einstellungen

- **`strategy: Recreate`**: Bei einer Änderung wird der alte Pod erst beendet, dann startet der neue. Zwei Postgres-Prozesse dürfen nie gleichzeitig dieselben Dateien beschreiben, ein `RollingUpdate` würde das kurz zulassen.
- **`PGDATA` auf einen Unterordner** (`/var/lib/postgresql/data/pgdata`): Ein neu eingebundenes Volume kann ein Verzeichnis `lost+found` enthalten, und `initdb` initialisiert nicht in einem nicht leeren Ordner.
- **Zugangsdaten**: Postgres erwartet `POSTGRES_USER`, `POSTGRES_PASSWORD` und `POSTGRES_DB`. Mit `valueFrom` (`secretKeyRef` bzw. `configMapKeyRef`) werden `DB_USER`, `DB_PASSWORD` und `DB_NAME` einzeln auf diese Namen abgebildet. Das Passwort steht nie im YAML.

### Service und DNS

Pods bekommen bei jedem Neustart eine neue IP. Der Service gibt der Datenbank einen festen Namen. CoreDNS löst ihn auf, der volle Name lautet `postgres.matchlytics.svc.cluster.local`. Im selben Namespace genügt `postgres`, aus einem anderen Namespace `postgres.matchlytics`. Das ist der Wert `DB_HOST=postgres` aus der ConfigMap.

Jeder Pod hat Suchdomänen (`matchlytics.svc.cluster.local`, `svc.cluster.local`, `cluster.local`) und probiert sie der Reihe nach durch. Die `NXDOMAIN`-Zeilen bei `nslookup` sind deshalb normal, entscheidend ist die Zeile mit der gefundenen IP.

```bash
kubectl run dns-test --rm -it --image=busybox:1.36 --restart=Never -n matchlytics -- nslookup postgres
kubectl run pg-test --rm -it --image=postgres:15 --restart=Never -n matchlytics -- pg_isready -h postgres -p 5432
```

### Was passiert mit den Daten?

| Aktion | Daten |
|---|---|
| Pod löschen | bleiben (das Deployment startet einen neuen Pod mit demselben PVC) |
| Deployment löschen | bleiben (das PVC ist eine eigene Ressource) |
| **PVC löschen** | **weg**: Die Reclaim Policy `Delete` entfernt PV und Ordner. Bei `Retain` bliebe der Ordner und müsste von Hand gelöscht werden. |

Die Daten liegen nur auf diesem einen Node. Wird k3s deinstalliert oder `/var/lib/rancher/k3s` gelöscht, sind sie verloren.

Beobachtung: `kubectl rollout status` meldet nach dem Start sofort Erfolg, obwohl Postgres auf einem neuen Volume noch einige Sekunden initialisiert (`psql` scheitert dann mit `No such file or directory`). Kubernetes weiß ohne Readiness-Probe nicht, ob die Datenbank schon Verbindungen annimmt. Das wird mit den Probes in Issue 26 behoben.

### Deployment oder StatefulSet?

Ein Deployment behandelt alle Pods als austauschbar. Für eine Datenbank mit einem Volume und einer Replika reicht das. Bei mehreren Replikas fehlen ihm:

- **Stabile Identität**: Ein StatefulSet gibt Pods feste Namen (`postgres-0`, `postgres-1`) und feste DNS-Namen.
- **Eigenes Volume pro Pod** (`volumeClaimTemplates`): Jeder Pod bekommt seinen eigenen Speicher, statt alle dasselbe PVC zu teilen.
- **Geordneter Start und Stopp**: Pods starten und enden nacheinander.

`replicas: 2` würde mit einem Deployment keine hochverfügbare Datenbank ergeben: Beide Pods würden auf dasselbe Volume zeigen (bei `ReadWriteOnce` startet der zweite nicht einmal sauber), und selbst mit getrennten Volumes wüssten die Datenbanken nichts voneinander. Es gäbe keine Replikation. Dafür braucht man eine Replikationslösung, etwa einen Operator wie CloudNativePG, oder einen Anbieter.

Die Produktionsdatenbank bleibt deshalb bei Neon: Backups, Hochverfügbarkeit, Updates und Wiederherstellung sind dort Aufgabe des Anbieters, der Cluster-Postgres dient nur der Entwicklung und der CI.


## Init-Job: Datenbank vorbereiten

Die Postgres im Cluster ist anfangs leer. Der Job `init-db` (`k8s/init-job.yaml`) bereitet sie vor: Er legt die Rohtabellen `raw_teams` und `raw_matches` an, baut mit `transform_data()` die Silver- und Gold-Views und legt die Read-only-Rolle `api_ro` an. Code: `src/seed/init_db.py`, Image: `Dockerfile.pipeline` mit `requirements-pipeline.txt`.

### Image

Das Image enthält nur Ingestion, Transformation, Hilfsfunktionen und `sql/`, kein Streamlit, und läuft nicht als Root (`USER appuser`, UID 10001). Es ist mit 316 MB deutlich kleiner als das Dashboard-Image (723 MB). Weil k3s `containerd` nutzt und Docker-Images nicht sieht, wird es per Hand importiert:

```bash
docker build -f Dockerfile.pipeline -t matchlytics-pipeline:dev .
docker save matchlytics-pipeline:dev | sudo k3s ctr images import -
```

### Job und Deployment

Ein **Deployment** hält einen Dienst dauerhaft am Leben. Ein **Job** führt eine Aufgabe **zu Ende** und beendet sich. Der Init-Job soll einmal laufen und fertig sein.

| Einstellung | Wirkung |
|---|---|
| `initContainers` | Läuft vor dem Hauptcontainer und muss zuerst fertig sein. Hier wartet `pg_isready`, bis Postgres Verbindungen annimmt ("warte, bis die Abhängigkeit bereit ist"). |
| `restartPolicy: Never` | Ein fehlgeschlagener Container wird nicht im selben Pod neu gestartet, sondern es entsteht bei Bedarf ein neuer Pod. Der alte bleibt für die Logs bestehen. |
| `backoffLimit: 3` | Nach 3 Wiederholungen (insgesamt 4 Pods) gibt Kubernetes auf, der Job ist `Failed`. |
| `ttlSecondsAfterFinished: 3600` | Eine Stunde nach dem Ende wird der Job samt Pods automatisch gelöscht. |
| `envFrom` | Alle Einträge aus ConfigMap und Secret werden zu Umgebungsvariablen. |

Ein fertiger Job läuft nicht erneut und sein Pod-Template ist unveränderlich. Zum Wiederholen löscht man ihn und wendet ihn neu an:

```bash
kubectl delete job init-db -n matchlytics
kubectl apply -f k8s/init-job.yaml
kubectl logs job/init-db -n matchlytics
```

Beobachteter Fehlerfall (falsches `DB_PASSWORD`): Es entstanden vier Pods, jeder endete in `Error` (`FATAL: password authentication failed`), danach war der Job `Failed`.

### Idempotenz

Das Skript darf beliebig oft laufen. `CREATE TABLE IF NOT EXISTS` lässt vorhandene Tabellen samt Daten in Ruhe, die Views werden mit `DROP VIEW ... CASCADE` und `CREATE` neu gebaut, die Rolle wird angelegt oder per `ALTER ROLE` aktualisiert. Ein zweiter Lauf erzeugt keine Dubletten.

Wichtig: `DROP VIEW` entfernt auch die Rechte auf der View. Deshalb vergibt das Skript die Rechte **zuletzt**, und nach jedem Lauf von `transform_data()` müssen sie neu vergeben werden (zum Beispiel durch erneutes Ausführen des Init-Jobs).

### Least Privilege: die Rolle `api_ro`

Die API soll nur lesen. Die Rolle `api_ro` bekommt `CONNECT`, `USAGE` auf das Schema und `SELECT` auf genau diese Objekte: `fct_standings`, `fct_season_trend`, `fct_team_form`, `fct_home_away_stats`, `fct_team_ratings`, `dim_teams` und `stg_matches`. Geprüft als `api_ro`: `SELECT` auf eine View klappt, `INSERT` (`permission denied`), `DROP VIEW` (`must be owner`) und ein Lesen der Rohtabellen (`permission denied`) scheitern. Wird die API gehackt, kann der Angreifer nichts verändern oder löschen, und der Admin-Benutzer bleibt unberührt.

Sicherheitsnetz: `check_target()` bricht ab, wenn `DB_HOST` nicht `localhost`, `127.0.0.1` oder `postgres` ist. So kann der Job nie versehentlich die Produktionsdatenbank (Neon) verändern.

### Daten

Der Job lädt **keine** Daten. Die echten Daten von football-data.org dürfen nicht ins öffentliche Repo oder in ein Image, weil die Weitergabe nicht geklärt ist. Sie werden lokal mit den Ingestion-Skripten geladen (`kubectl port-forward svc/postgres 5434:5432`, dann `python -m src.main` mit `DB_HOST=localhost`, `DB_PORT=5434` und `DB_SSLMODE=` leer). Für die CI folgt später ein kleiner erfundener Datensatz, der ins Repo darf. Der Ordner `/seed/` ist in `.gitignore` und `.dockerignore` eingetragen.

### Job oder SQL-Skript im Postgres-Container?

Skripte in `/docker-entrypoint-initdb.d` laufen nur, wenn das Datenverzeichnis **leer** ist, nur im Postgres-Container und nur als SQL oder Shell. Der Init-Job ist dagegen separat sichtbar (Status, Logs, Wiederholungen), wiederholbar, nutzt denselben Python-Code wie die Pipeline und wartet selbst auf die Datenbank. Das Gegenteil wäre richtig, wenn nur ein festes Schema oder eine Rolle per reinem SQL angelegt werden soll: Dann ist `initdb.d` einfacher, braucht kein eigenes Image und läuft garantiert vor der ersten Verbindung.

## API und Dashboard als Deployments

### Bausteine

| Datei | Was sie macht |
|---|---|
| `api-deployment.yaml` | 2 Pods mit `matchlytics-api:dev`, Port 8000 |
| `api-service.yaml` | Service `api`, Port 80 → 8000 |
| `dashboard-deployment.yaml` | 2 Pods mit `matchlytics-dashboard:dev`, Port 8501 |
| `dashboard-service.yaml` | Service `dashboard`, Port 80 → 8501 |
| `ingress.yaml` | Traefik-Ingress, `matchlytics.localhost` → Service `dashboard` |

Die Images liegen nur lokal und werden in k3s importiert (`docker save … | sudo k3s ctr images import -`). Deshalb steht in den Deployments `imagePullPolicy: IfNotPresent`. Größen: API 180 MB, Dashboard 661 MB, Pipeline 316 MB. Das Dashboard-Image ist nur wenig kleiner als das frühere Einzel-Image, weil Streamlit, pandas, Plotly und pyarrow den größten Teil ausmachen. Der Gewinn liegt woanders: Es enthält keinen Datenbank-Code und keine Zugangsdaten.

### Deployment, ReplicaSet, Pod

Ein **Deployment** beschreibt den Soll-Zustand (Image, Anzahl Kopien). Es erzeugt ein **ReplicaSet**, und das ReplicaSet erzeugt und überwacht die **Pods**. Das ReplicaSet sorgt dafür, dass immer so viele Pods laufen, wie `replicas` sagt. Bei einem Update legt das Deployment ein neues ReplicaSet an und lässt das alte mit 0 Pods stehen, damit ein Rollback möglich ist.

```bash
kubectl get deploy,rs,pods,svc,ingress -n matchlytics
```

### Service, Labels und Selector

Ein Service ist eine feste Adresse (und ein DNS-Name) vor wechselnden Pods. Er findet seine Pods über den **Selector**: Alle Pods, deren Labels zu `app: matchlytics` und `component: api` passen, werden Ziel. Das sieht man mit `kubectl get endpoints api -n matchlytics`. Ein Pod wird erst aufgenommen, wenn er bereit ist. Ohne Probe gilt ein Pod als bereit, sobald der Container läuft (Probes folgen in einem späteren Issue).

Das Dashboard erreicht die API über `http://api` (ConfigMap-Wert `API_URL`). Der Kurzname klappt, weil der Pod die Suchdomäne `matchlytics.svc.cluster.local` bekommt. Geprüft mit `kubectl exec deploy/dashboard -n matchlytics -- python -c "import urllib.request as u; print(u.urlopen('http://api/ready').read())"`. Antwort: `{"status":"ready","database":"ok"}`.

### Ingress

Der Ingress ist die Eingangstür des Clusters. k3s bringt **Traefik** als Controller mit. Die Regel leitet `matchlytics.localhost` an den Service `dashboard` weiter. `*.localhost` zeigt im Browser auf `127.0.0.1`, Traefik lauscht dort auf Port 80. Zum Debuggen eines einzelnen Dienstes ohne Ingress dient `kubectl port-forward svc/api 8000:80 -n matchlytics`.

Streamlit prüft bei WebSocket-Verbindungen die Herkunft der Seite. Das Dashboard bekommt deshalb `STREAMLIT_BROWSER_SERVER_ADDRESS=matchlytics.localhost`.

### Zugangsdaten

Die API bekommt die ConfigMap per `envFrom`, aber **nicht** das Secret per `envFrom`: Es enthält die Zugangsdaten des Admin-Benutzers. Stattdessen setzt das Deployment `DB_USER=api_ro` und holt nur `DB_PASSWORD` aus dem Schlüssel `API_RO_PASSWORD`. Die API arbeitet also mit der Read-only-Rolle. Das Dashboard bekommt nur `API_URL` und keinerlei Datenbank-Zugangsdaten.

### Beobachtet

- **Self-Healing:** Ein gelöschter API-Pod wurde sofort durch einen neuen ersetzt.
- **Skalieren:** `kubectl scale deployment/api --replicas=4` startete zwei weitere Pods, neue Pods tauchten erst als Endpoint auf, als sie bereit waren. `scale` ändert nur den Cluster, nicht die Datei.
- **Rolling Update:** `kubectl rollout restart` erzeugte ein zweites ReplicaSet, das alte blieb mit 0 Pods erhalten (`kubectl rollout history` zeigt zwei Revisionen).
- **Fehlerhaftes Update:** Mit `kubectl set image deployment/api api=matchlytics-api:gibt-es-nicht` hing der neue Pod in `ErrImagePull`, die beiden alten Pods liefen unverändert weiter. `kubectl rollout undo` räumte auf. `undo` ändert nur den Cluster, nicht `last-applied-configuration`. Im Alltag korrigiert man die YAML-Datei und wendet sie neu an.

### Fehlerfall: Cluster-DNS findet neue Services nicht

Symptom: `Name or service not known` aus dem Dashboard-Pod und `NXDOMAIN` für `api.matchlytics.svc.cluster.local`, obwohl der Service existierte und Endpoints hatte. Ältere Services wie `postgres` wurden noch aufgelöst. CoreDNS hatte seine Verbindung zur Kubernetes-API verloren, weil sich die IP-Adresse des Rechners im WLAN geändert hatte (`192.168.2.164` → `100.81.75.109`). Auch `metrics-server` blieb deshalb auf `0/1`.

Behebung: `sudo systemctl restart k3s` (trägt die neue Adresse ein), danach `kubectl rollout restart deployment/coredns -n kube-system`. Ein CoreDNS-Neustart allein half nicht, solange k3s noch die alte Adresse nutzte. Bei einem lokalen Laptop-Cluster kann das nach einem Netzwechsel wieder passieren.

### Verständnisfragen

**Woher weiß der Service, an welche Pods er Anfragen schicken soll?** Über den Selector (`app` und `component`). Kubernetes pflegt die Liste der passenden, bereiten Pods als Endpoints. Pods kommen und gehen, die Liste wird automatisch angepasst.

**Was passiert bei `replicas: 1` in der YAML und erneutem Anwenden, nachdem per `scale` auf 3 erhöht wurde?** Die Datei ist der Soll-Zustand und gewinnt. `apply` setzt `replicas` zurück auf 1, zwei Pods werden beendet. Änderungen mit `kubectl scale` überleben ein erneutes `apply` nicht. Wer dauerhaft skalieren will, ändert die Datei.

**Warum soll die Datenbank nur von der API erreichbar sein?** Das Dashboard ist die größte Angriffsfläche (Browser-Eingaben, viele Bibliotheken). Hätte es direkten Datenbankzugang, könnte ein Fehler dort die Daten offenlegen. Die API ist ein enger, getesteter Zugang mit Read-only-Rolle. Im Cluster lässt sich das mit einer **NetworkPolicy** erzwingen: Sie erlaubt Verkehr zu Postgres (Port 5432) nur von Pods mit `component: api`. k3s bringt mit kube-router eine Umsetzung mit. Das ist hier noch nicht eingerichtet, die Trennung beruht bisher auf den fehlenden Zugangsdaten im Dashboard.

## Probes und Ressourcen

### Probes

| Workload | Readiness | Liveness | Startup |
|---|---|---|---|
| API | `/ready` (prüft die Datenbank) | `/health` (ohne Datenbank) | nicht nötig |
| Dashboard | `/_stcore/health` | `/_stcore/health` | bis 60 s (30 × 2 s) |
| Postgres | `pg_isready` | `pg_isready` | bis 60 s |

- **Readiness** beantwortet: Bekommt der Pod Traffic? Schlägt sie fehl, nimmt der Service den Pod aus der Verteilung, der Pod läuft weiter.
- **Liveness** beantwortet: Muss der Pod neu gestartet werden? Schlägt sie fehl, beendet Kubernetes den Container und startet ihn neu.
- **Startup** gibt langsamen Programmen Zeit. Readiness und Liveness beginnen erst, wenn sie besteht.
- Die Liveness-Probe der API prüft bewusst **nicht** die Datenbank. Sonst würde ein kurzer Ausfall von Postgres alle API-Pods gleichzeitig neu starten, ohne das Problem zu lösen. Diese Trennung ist der Grund für `/health` und `/ready`.

### Requests und Limits

Gemessen im Leerlauf mit `kubectl top pods` (metrics-server):

| Workload | gemessen CPU / RAM | requests | limits |
|---|---|---|---|
| API | 2m / 42–44 Mi | 25m / 64 Mi | 250m / 128 Mi |
| Dashboard | 0m / 45–98 Mi | 50m / 128 Mi | 500m / 384 Mi |
| Postgres | 1m / 26 Mi | 50m / 128 Mi | 500m / 512 Mi |

- **requests** sind die garantierte Menge, der Scheduler plant damit. **limits** sind die Obergrenze: Zu viel CPU wird gebremst, zu viel Speicher beendet den Container (`OOMKilled`).
- Die Werte liegen über den Leerlaufwerten, weil unter Last mehr gebraucht wird. Das Dashboard bekommt mehr Spielraum (Streamlit hält DataFrames im Speicher), Postgres ebenfalls (`shared_buffers` standardmäßig 128 MB, ein `OOMKilled` wäre bei einer Datenbank besonders unschön).
- Ein Limit unter dem Request ist nicht erlaubt (`requests.memory must be less than or equal to memory limit`).

### Experimente

1. **Falscher Readiness-Pfad (API):** Der neue Pod stand auf `0/1 Running` mit `RESTARTS 0`, die Endpoints enthielten nur die alten Pods. Das Rolling Update blieb stehen, die alten Pods liefen weiter, ohne Ausfall. **Falscher Liveness-Pfad:** Nach etwa 70 s (10 s Verzögerung plus 3 × 20 s) startete Kubernetes beide Container neu (`RESTARTS 1`).
2. **Postgres mit `replicas: 0`:** Beide API-Pods wurden `0/1`, die Endpoints leer, `RESTARTS` unverändert. In einem Pod lieferte `/health` `200` und `/ready` `503`. Nach dem Hochfahren von Postgres waren die API-Pods nach etwa 20 s wieder `1/1`, ohne Eingriff. Die Daten waren erhalten, weil sie auf dem PersistentVolume liegen.
3. **Speicher-Limit 20 Mi (Request 16 Mi):** Die API braucht rund 42 Mi. Der neue Pod endete mit `OOMKilled`, `Exit Code: 137`, danach `CrashLoopBackOff` (Kubernetes verlängert die Wartezeit zwischen den Neustarts). Die alten Pods liefen weiter. Mit `kubectl apply -f k8s/api-deployment.yaml` kamen die richtigen Werte zurück.

### Verständnisfragen

**Was ist der Unterschied zwischen „nicht ready“ und „wird neu gestartet“?** Nicht ready: Der Pod bleibt am Leben, bekommt aber keinen Traffic, bis die Readiness-Probe wieder besteht. Neu gestartet: Die Liveness-Probe ist mehrfach fehlgeschlagen, der Container wird beendet und neu erzeugt (`RESTARTS` steigt). Nicht ready ist die mildere Maßnahme.

**Was wäre passiert, wenn die Liveness-Probe der API die DB geprüft hätte und Postgres kurz ausfällt?** Alle API-Pods hätten die Probe gleichzeitig nicht bestanden und wären neu gestartet worden. Die Datenbank ist aber das Problem, nicht die API. Die Neustarts bringen sie nicht zurück und belasten die Datenbank beim Wiederanlauf zusätzlich (alle Pods bauen gleichzeitig Verbindungen auf).

**Wie hängen die Probes mit dem Health Check aus Issue 18 zusammen?** Der `HEALTHCHECK` im Dockerfile gilt nur für Docker (zum Beispiel in `docker compose`), Kubernetes ignoriert ihn. Er nutzt denselben Pfad `/health`. In Kubernetes übernehmen die Probes diese Aufgabe, dort sind sie feiner einstellbar (getrennt nach Readiness und Liveness, mit Startup-Phase).
