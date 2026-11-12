"""Meldet die Kennzahlen eines Pipeline-Laufs an ein Prometheus-Pushgateway.

Warum Push? Die Pipeline laeuft nur kurz und ist danach beendet. Prometheus holt Werte per Pull ab und
koennte den Pod gar nicht mehr abfragen. Deshalb schiebt der Lauf sein Ergebnis am Ende selbst an das
Pushgateway, das es zwischenspeichert, bis Prometheus es abholt.

Warum Gauges? Das Pushgateway behaelt immer nur den zuletzt gepushten Wert. Ein Counter wuerde bei jedem Lauf
wieder bei null beginnen, ein Histogram mit einem einzigen Messwert pro Lauf sagt nichts aus. Fuer
"Ergebnis des letzten Laufs" ist ein Gauge der passende Typ.

Der Push ist nur aktiv, wenn PUSHGATEWAY_URL gesetzt ist. Ein Fehler beim Pushen bricht die Pipeline nie ab.
"""
import os
import time

from src.utils.logger import get_logger

logger = get_logger("metrics")

JOB_NAME = "matchlytics_pipeline"


def push_pipeline_metrics(duration_seconds: float, teams: int, matches: int, success: bool) -> bool:
    """Schickt die Werte des Laufs an das Pushgateway. Gibt zurueck, ob gepusht wurde."""
    url = os.getenv("PUSHGATEWAY_URL")
    if not url:
        return False

    try:
        from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway

        registry = CollectorRegistry()
        now = time.time()
        Gauge("matchlytics_pipeline_duration_seconds", "Laufzeit des letzten Pipeline-Laufs", registry=registry).set(
            duration_seconds
        )
        Gauge("matchlytics_pipeline_teams_loaded", "Teams im letzten Lauf geladen", registry=registry).set(teams)
        Gauge("matchlytics_pipeline_matches_loaded", "Spiele im letzten Lauf geladen", registry=registry).set(matches)
        Gauge("matchlytics_pipeline_errors", "Fehler im letzten Lauf (0 oder 1)", registry=registry).set(
            0 if success else 1
        )
        Gauge("matchlytics_pipeline_last_run_timestamp_seconds", "Ende des letzten Laufs", registry=registry).set(now)
        if success:
            Gauge(
                "matchlytics_pipeline_last_success_timestamp_seconds",
                "Ende des letzten erfolgreichen Laufs",
                registry=registry,
            ).set(now)

        # pushadd (POST) ersetzt nur die hier gesendeten Metriken. So bleibt der Zeitpunkt des letzten
        # Erfolgs erhalten, wenn ein spaeterer Lauf fehlschlaegt.
        pushadd_to_gateway(url, job=JOB_NAME, registry=registry)
        logger.info("Pipeline-Metriken an %s gesendet", url)
        return True
    except Exception as exc:  # Monitoring darf die Pipeline nie zum Absturz bringen
        logger.warning("Pipeline-Metriken konnten nicht gesendet werden: %s", exc)
        return False
