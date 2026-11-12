#!/usr/bin/env bash
# Startet den Lasttest als Job im Cluster und gibt das Ergebnis aus.
#
# Aufruf:  loadtest/run.sh <Nutzer> [Sekunden]      z. B.  loadtest/run.sh 50 60
#
# Warum im Cluster? "kubectl port-forward" auf einen Service waehlt einen einzigen Pod und bleibt dabei.
# Ein Test ueber den Port-Forward wuerde nie alle Replikas treffen. Der Job spricht den Service "api" an,
# der die Anfragen wie im Betrieb auf alle Pods verteilt.
set -euo pipefail

USERS="${1:?Aufruf: loadtest/run.sh <Nutzer> [Sekunden]}"
SECONDS_TOTAL="${2:-60}"
NS=matchlytics
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "API-Replikas: $(kubectl get deployment api -n "$NS" -o jsonpath='{.status.readyReplicas}')"

# Das Skript kommt als ConfigMap in den Pod
kubectl create configmap locustfile -n "$NS" --from-file="$HERE/locustfile.py" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl delete job loadtest -n "$NS" --ignore-not-found >/dev/null

kubectl apply -n "$NS" -f - <<JOB >/dev/null
apiVersion: batch/v1
kind: Job
metadata:
  name: loadtest
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 900
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: locust
          image: locustio/locust:2.32.5
          env:
            - {name: LOCUST_LOCUSTFILE, value: /mnt/locust/locustfile.py}
            - {name: LOCUST_HOST, value: "http://api"}
            - {name: LOCUST_HEADLESS, value: "true"}
            - {name: LOCUST_ONLY_SUMMARY, value: "true"}
            - {name: LOCUST_USERS, value: "$USERS"}
            - {name: LOCUST_SPAWN_RATE, value: "10"}
            - {name: LOCUST_RUN_TIME, value: "${SECONDS_TOTAL}s"}
          resources:
            requests: {cpu: 200m, memory: 128Mi}
            limits: {cpu: "1", memory: 512Mi}
          volumeMounts:
            - {name: script, mountPath: /mnt/locust}
      volumes:
        - name: script
          configMap:
            name: locustfile
JOB

echo "Test laeuft: $USERS Nutzer, ${SECONDS_TOTAL}s ..."

# Ressourcenverbrauch waehrend des Tests (metrics-server aktualisiert etwa alle 15 s)
( sleep $((SECONDS_TOTAL * 2 / 3)); echo; echo "--- kubectl top pods (waehrend des Tests) ---"; kubectl top pods -n "$NS" ) &

# Locust beendet sich mit einem Fehlercode, wenn Anfragen fehlgeschlagen sind. Der Job gilt dann als
# "failed" statt "complete". Wir warten deshalb auf beides und zeigen das Ergebnis in jedem Fall.
for _ in $(seq 1 $(((SECONDS_TOTAL + 180) / 3))); do
  state="$(kubectl get job loadtest -n "$NS" -o jsonpath='{.status.succeeded}/{.status.failed}')"
  case "$state" in 1/*|*/1) break ;; esac
  sleep 3
done
wait
echo
echo "--- Ergebnis ---"
kubectl logs job/loadtest -n "$NS" | sed -n '/Type  *Name/,$p'
