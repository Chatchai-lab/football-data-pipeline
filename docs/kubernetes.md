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
