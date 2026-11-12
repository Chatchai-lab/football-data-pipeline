# 0001: k3s lokal und k3d in der CI statt kind

**Status:** angenommen

## Kontext
Für das Lernen und für Tests wird ein Kubernetes-Cluster ohne Cloud-Kosten gebraucht. Lokal soll er dauerhaft laufen, in der CI nur für einen Lauf.

## Entscheidung
Lokal läuft **k3s** direkt auf dem Rechner, in der CI startet **k3d** (k3s in Docker) einen kurzlebigen Cluster.

## Alternativen
- **kind:** läuft ebenfalls in Docker, bringt aber keinen Ingress-Controller und keine Storage-Klasse mit. Dafür wäre zusätzliche Einrichtung nötig.
- **minikube:** schwerer, braucht eine VM oder einen Treiber.
- **Ein einziger Werkzeugtyp überall:** k3d lokal wäre möglich gewesen, k3s direkt zeigt aber, wie ein Node ohne Docker-Schicht aussieht (containerd, `k3s ctr`).

## Begründung
k3s und k3d sind dieselbe Distribution: Traefik als Ingress und `local-path` als StorageClass sind in beiden schon enthalten, die Manifeste laufen unverändert. k3d startet in der CI in Sekunden und lässt sich wegwerfen, der Runner bleibt sauber.

## Folgen
Die Image-Importwege unterscheiden sich (`k3s ctr images import` lokal, `k3d image import` in der CI). `k3d image import` meldet bei Fehlern trotzdem Erfolg, deshalb prüft die CI selbst, ob die Images im Cluster liegen.
