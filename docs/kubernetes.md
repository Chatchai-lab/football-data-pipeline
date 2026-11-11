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
