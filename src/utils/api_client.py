"""HTTP-Client für die Matchlytics-API.

Eine Funktion pro Endpoint. Die Basis-Adresse kommt aus der Umgebungsvariable API_URL.
Fehler werden in verständliche Ausnahmen übersetzt, damit das Dashboard eine
Fehlermeldung zeigen kann statt eines Stacktraces.
"""
import os
import time

import requests

TIMEOUT_SECONDS = 10
RETRIES = 2
BACKOFF_SECONDS = 0.5

# Diese Statuscodes sind vorübergehende Zustände, ein erneuter Versuch lohnt sich.
RETRY_MESSAGES = {
    502: "Die API ist vorübergehend nicht verfügbar.",
    503: "Die Datenbank hinter der API ist nicht erreichbar.",
    504: "Die API antwortet nicht rechtzeitig.",
}


class ApiError(Exception):
    """Die API ist nicht erreichbar oder hat einen Fehler gemeldet."""


class ApiNotFound(ApiError):
    """Die API kennt die angefragte Saison oder das Team nicht (HTTP 404)."""


def base_url() -> str | None:
    """Die Basis-Adresse der API ohne abschließenden Schrägstrich, oder None."""
    url = os.getenv("API_URL", "").strip().rstrip("/")
    return url or None


def is_enabled() -> bool:
    """True, wenn das Dashboard die API nutzen soll (API_URL ist gesetzt)."""
    return base_url() is not None


def _detail(response) -> str:
    """Liest die Fehlermeldung aus der Antwort der API, falls vorhanden."""
    try:
        return str(response.json().get("detail", ""))
    except (ValueError, AttributeError):
        return ""


def _get(path: str, params: dict | None = None):
    """GET-Aufruf mit Timeout und Wiederholungen bei vorübergehenden Fehlern."""
    base = base_url()
    if base is None:
        raise ApiError("API_URL ist nicht gesetzt.")

    last_error = "Unbekannter Fehler."
    for attempt in range(RETRIES + 1):
        if attempt:
            time.sleep(BACKOFF_SECONDS * attempt)
        try:
            response = requests.get(f"{base}{path}", params=params, timeout=TIMEOUT_SECONDS)
        except requests.exceptions.Timeout:
            last_error = "Die API antwortet nicht rechtzeitig."
            continue
        except requests.exceptions.ConnectionError:
            last_error = f"Die API unter {base} ist nicht erreichbar."
            continue

        if response.status_code in RETRY_MESSAGES:
            last_error = RETRY_MESSAGES[response.status_code]
            continue
        if response.status_code == 404:
            raise ApiNotFound(_detail(response))
        if response.status_code >= 400:
            raise ApiError(
                f"Die API meldet einen Fehler ({response.status_code}): {_detail(response)}"
            )
        return response.json()

    raise ApiError(last_error)


# --- Ein Aufruf pro Endpoint -------------------------------------------------

def status() -> dict:
    return _get("/status")


def seasons() -> list[str]:
    return _get("/seasons")


def teams(season: str) -> list[str]:
    return _get("/teams", {"season": season})


def team_meta() -> list[dict]:
    return _get("/team-meta")


def standings(season: str) -> list[dict]:
    return _get("/standings", {"season": season})


def season_trend(season: str, team: list[str] | None = None) -> list[dict]:
    return _get("/season-trend", {"season": season, "team": team})


def team_form(season: str, team: list[str] | None = None) -> list[dict]:
    return _get("/team-form", {"season": season, "team": team})


def home_away(season: str) -> list[dict]:
    return _get("/home-away", {"season": season})


def ratings(season: str) -> list[dict]:
    return _get("/ratings", {"season": season})


def matches(season: str) -> list[dict]:
    return _get("/matches", {"season": season})


def highlights(season: str) -> dict:
    return _get("/highlights", {"season": season})
