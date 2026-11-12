from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Connection, text
from sqlalchemy.exc import OperationalError, TimeoutError as PoolTimeoutError
from src.api.routers import gold, meta
from src.api.deps import get_db
from src.api.metrics import DB_ERRORS, POOL_TIMEOUTS, metrics_endpoint, metrics_middleware
from src.api.schemas import HealthResponse, ReadyResponse

app = FastAPI(
    title="Matchlytics API",
    description="Read-only REST-API auf den Gold-Views der Matchlytics-Datenbank.",
    version="0.1.0",
)

app.middleware("http")(metrics_middleware)
app.add_api_route("/metrics", metrics_endpoint, include_in_schema=False)

app.include_router(meta.router)
app.include_router(gold.router)


@app.exception_handler(OperationalError)
async def database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
    """Eine nicht erreichbare Datenbank wird fuer jeden Endpoint zu einem sauberen 503."""
    DB_ERRORS.inc()
    return JSONResponse(status_code=503, content={"detail": "Datenbank nicht erreichbar"})


@app.exception_handler(PoolTimeoutError)
async def pool_exhausted(request: Request, exc: PoolTimeoutError) -> JSONResponse:
    """Alle Datenbankverbindungen sind belegt: kurzer, sauberer 503 statt eines 500 nach langem Warten."""
    POOL_TIMEOUTS.inc()
    return JSONResponse(
        status_code=503,
        content={"detail": "Server ueberlastet, bitte spaeter erneut versuchen"},
        headers={"Retry-After": "2"},
    )


# Bewusst "async def": Die Funktion laeuft dann in der Event-Loop und nicht im Thread-Pool, den die
# normalen (synchronen) Endpunkte teilen. Sind unter Last alle Threads mit dem Warten auf die Datenbank
# belegt, antwortet /health trotzdem. Sonst laeuft die Liveness-Probe in ein Timeout, und Kubernetes
# startet den Pod im Moment der hoechsten Last neu.
@app.get("/health", response_model=HealthResponse, tags=["Betrieb"])
async def health() -> HealthResponse:
    """Liveness: Der Prozess lebt. Kein Datenbankzugriff."""
    return HealthResponse(status="ok")


@app.get("/ready", response_model=ReadyResponse, tags=["Betrieb"])
def ready(conn: Connection = Depends(get_db)) -> ReadyResponse:
    """Readiness: Die Datenbank antwortet auf ein einfaches SELECT 1."""
    conn.execute(text("SELECT 1"))
    return ReadyResponse(status="ready", database="ok")
