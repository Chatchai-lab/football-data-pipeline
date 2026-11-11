"""Tests des API-Clients ohne Netzwerk: requests.get wird durch eine Attrappe ersetzt."""
import pytest
import requests

from src.utils import api_client
from src.utils.api_client import ApiError, ApiNotFound


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("kein JSON")
        return self._payload


@pytest.fixture(autouse=True)
def api_url(monkeypatch):
    """Setzt eine Basis-Adresse und schaltet die Wartezeit zwischen Versuchen ab."""
    monkeypatch.setenv("API_URL", "http://api:8000")
    monkeypatch.setattr(api_client.time, "sleep", lambda seconds: None)


def patch_get(monkeypatch, *outcomes):
    """Ersetzt requests.get: jeder Aufruf liefert das nächste Ergebnis oder wirft es."""
    calls = []
    remaining = list(outcomes)

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        outcome = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    return calls


def test_is_enabled_haengt_an_api_url(monkeypatch):
    assert api_client.is_enabled() is True
    monkeypatch.delenv("API_URL")
    assert api_client.is_enabled() is False
    monkeypatch.setenv("API_URL", "   ")
    assert api_client.is_enabled() is False


def test_abschliessender_schraegstrich_wird_entfernt(monkeypatch):
    monkeypatch.setenv("API_URL", "http://api:8000/")
    calls = patch_get(monkeypatch, FakeResponse(200, ["2026"]))
    assert api_client.seasons() == ["2026"]
    assert calls[0]["url"] == "http://api:8000/seasons"


def test_ohne_api_url_wird_ein_fehler_geworfen(monkeypatch):
    monkeypatch.delenv("API_URL")
    with pytest.raises(ApiError, match="API_URL"):
        api_client.seasons()


def test_parameter_und_timeout_werden_uebergeben(monkeypatch):
    calls = patch_get(monkeypatch, FakeResponse(200, []))
    api_client.season_trend("2026", team=["FC Test", "SV Beispiel"])
    assert calls[0]["url"] == "http://api:8000/season-trend"
    assert calls[0]["params"] == {"season": "2026", "team": ["FC Test", "SV Beispiel"]}
    assert calls[0]["timeout"] == api_client.TIMEOUT_SECONDS


def test_nicht_erreichbare_api_wird_wiederholt_und_dann_gemeldet(monkeypatch):
    calls = patch_get(monkeypatch, requests.exceptions.ConnectionError("down"))
    with pytest.raises(ApiError, match="nicht erreichbar"):
        api_client.status()
    assert len(calls) == api_client.RETRIES + 1


def test_timeout_wird_verstaendlich_gemeldet(monkeypatch):
    patch_get(monkeypatch, requests.exceptions.Timeout("langsam"))
    with pytest.raises(ApiError, match="nicht rechtzeitig"):
        api_client.status()


def test_503_wird_wiederholt_und_als_datenbankproblem_gemeldet(monkeypatch):
    calls = patch_get(monkeypatch, FakeResponse(503, {"detail": "Datenbank nicht erreichbar"}))
    with pytest.raises(ApiError, match="Datenbank"):
        api_client.status()
    assert len(calls) == api_client.RETRIES + 1


def test_erfolg_nach_kurzem_ausfall(monkeypatch):
    calls = patch_get(
        monkeypatch,
        requests.exceptions.ConnectionError("down"),
        FakeResponse(200, ["2026"]),
    )
    assert api_client.seasons() == ["2026"]
    assert len(calls) == 2


def test_404_wird_nicht_wiederholt(monkeypatch):
    calls = patch_get(monkeypatch, FakeResponse(404, {"detail": "Saison 1999 nicht gefunden"}))
    with pytest.raises(ApiNotFound, match="1999"):
        api_client.standings("1999")
    assert len(calls) == 1


def test_422_wird_als_fehler_mit_statuscode_gemeldet(monkeypatch):
    patch_get(monkeypatch, FakeResponse(422, {"detail": "ungueltig"}))
    with pytest.raises(ApiError, match="422"):
        api_client.standings("abc")


def test_apinotfound_ist_ein_apierror():
    assert issubclass(ApiNotFound, ApiError)
