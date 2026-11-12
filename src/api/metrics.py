"""Prometheus-Metriken der API.

Prometheus holt die Werte per Pull von /metrics ab. Drei Metrik-Typen:

- Counter:   zaehlt nur aufwaerts (Anfragen, Datenbankfehler). Prometheus bildet daraus mit rate() Anfragen pro Sekunde.
- Histogram: verteilt Antwortzeiten auf Zeitklassen (Buckets). Daraus berechnet histogram_quantile() z. B. die
             95. Perzentile, auch ueber mehrere Pods hinweg. Ein Mittelwert wuerde langsame Ausreisser verstecken.
- Gauge:     ein Wert, der steigen und fallen kann (Anfragen, die gerade laufen).
"""
import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUESTS = Counter(
    "http_requests_total",
    "Anzahl der HTTP-Anfragen",
    ["method", "path", "status"],
)

DURATION = Histogram(
    "http_request_duration_seconds",
    "Antwortzeit der HTTP-Anfragen in Sekunden",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Anfragen, die gerade bearbeitet werden",
)

DB_ERRORS = Counter(
    "api_database_errors_total",
    "Anfragen, die wegen einer nicht erreichbaren Datenbank mit 503 endeten",
)


POOL_TIMEOUTS = Counter(
    "api_pool_timeouts_total",
    "Anfragen, die keine Datenbankverbindung bekamen (Pool erschoepft) und mit 503 endeten",
)


def route_template(request: Request) -> str:
    """Pfad der Route, z. B. /standings. Unbekannte Pfade werden zusammengefasst,
    damit Scanner oder Tippfehler nicht unbegrenzt viele Label-Werte erzeugen."""
    route = request.scope.get("route")
    return route.path if route is not None else "unmatched"


async def metrics_middleware(request: Request, call_next):
    """Misst jede Anfrage. /metrics selbst wird nicht mitgezaehlt."""
    if request.url.path == "/metrics":
        return await call_next(request)

    IN_PROGRESS.inc()
    start = time.perf_counter()
    status = 500  # gilt, falls eine Ausnahme bis hierher durchschlaegt
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        path = route_template(request)
        IN_PROGRESS.dec()
        REQUESTS.labels(request.method, path, str(status)).inc()
        DURATION.labels(request.method, path).observe(elapsed)


def metrics_endpoint() -> Response:
    """Antwort im Textformat von Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
