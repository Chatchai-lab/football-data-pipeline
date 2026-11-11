from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Connection, text
from sqlalchemy.exc import OperationalError
from src.api.routers import gold, meta
from src.api.deps import get_db
from src.api.schemas import HealthResponse, ReadyResponse

app = FastAPI(
    title="Matchlytics API",
    description="Read-only REST-API auf den Gold-Views der Matchlytics-Datenbank.",
    version="0.1.0",
)

app.include_router(meta.router)
app.include_router(gold.router)


@app.exception_handler(OperationalError)
async def database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
    """Eine nicht erreichbare Datenbank wird fuer jeden Endpoint zu einem sauberen 503."""
    return JSONResponse(status_code=503, content={"detail": "Datenbank nicht erreichbar"})


@app.get("/health", response_model=HealthResponse, tags=["Betrieb"])
def health() -> HealthResponse:
    """Liveness: Der Prozess lebt. Kein Datenbankzugriff."""
    return HealthResponse(status="ok")


@app.get("/ready", response_model=ReadyResponse, tags=["Betrieb"])
def ready(conn: Connection = Depends(get_db)) -> ReadyResponse:
    """Readiness: Die Datenbank antwortet auf ein einfaches SELECT 1."""
    conn.execute(text("SELECT 1"))
    return ReadyResponse(status="ready", database="ok")
