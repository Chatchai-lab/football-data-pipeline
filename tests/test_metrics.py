"""Tests der Prometheus-Metriken: /metrics der API und der Push der Pipeline."""
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from src.api.main import app
from src.utils import metrics_push

client = TestClient(app)


def metrics_text() -> str:
    response = client.get("/metrics")
    assert response.status_code == 200
    return response.text


# --- API: /metrics ---------------------------------------------------------

def test_metrics_endpoint_is_text_format():
    response = client.get("/metrics")
    assert response.headers["content-type"].startswith("text/plain")


def test_requests_are_counted_with_route_template():
    client.get("/health")
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in metrics_text()


def test_duration_is_a_histogram_with_buckets():
    client.get("/health")
    body = metrics_text()
    assert 'http_request_duration_seconds_bucket{le="0.1",method="GET",path="/health"}' in body
    assert 'http_request_duration_seconds_count{method="GET",path="/health"}' in body


def test_unknown_paths_do_not_create_new_labels():
    client.get("/gibt-es-nicht-4711")
    body = metrics_text()
    assert 'path="unmatched"' in body
    assert "gibt-es-nicht-4711" not in body


def test_metrics_endpoint_is_not_counted_itself():
    client.get("/metrics")
    assert 'path="/metrics"' not in metrics_text()


def test_gauge_and_database_error_counter_exist():
    body = metrics_text()
    assert "http_requests_in_progress" in body
    assert "api_database_errors_total" in body


# --- Pipeline: Push an das Pushgateway --------------------------------------

def test_push_is_skipped_without_gateway_url(monkeypatch, mocker):
    monkeypatch.delenv("PUSHGATEWAY_URL", raising=False)
    push = mocker.patch("prometheus_client.pushadd_to_gateway")
    assert metrics_push.push_pipeline_metrics(12.5, 18, 306, success=True) is False
    push.assert_not_called()


def test_push_sends_all_pipeline_metrics(monkeypatch, mocker):
    monkeypatch.setenv("PUSHGATEWAY_URL", "pushgateway:9091")
    push = mocker.patch("prometheus_client.pushadd_to_gateway")

    assert metrics_push.push_pipeline_metrics(12.5, 18, 306, success=True) is True

    args, kwargs = push.call_args
    assert args[0] == "pushgateway:9091"
    assert kwargs["job"] == "matchlytics_pipeline"
    body = generate_latest(kwargs["registry"]).decode()
    assert "matchlytics_pipeline_duration_seconds 12.5" in body
    assert "matchlytics_pipeline_teams_loaded 18.0" in body
    assert "matchlytics_pipeline_matches_loaded 306.0" in body
    assert "matchlytics_pipeline_errors 0.0" in body
    assert "matchlytics_pipeline_last_success_timestamp_seconds" in body


def test_failed_run_reports_error_and_no_success_timestamp(monkeypatch, mocker):
    monkeypatch.setenv("PUSHGATEWAY_URL", "pushgateway:9091")
    push = mocker.patch("prometheus_client.pushadd_to_gateway")

    metrics_push.push_pipeline_metrics(3.0, 0, 0, success=False)

    body = generate_latest(push.call_args.kwargs["registry"]).decode()
    assert "matchlytics_pipeline_errors 1.0" in body
    assert "last_success_timestamp" not in body


def test_unreachable_gateway_never_breaks_the_pipeline(monkeypatch, mocker):
    monkeypatch.setenv("PUSHGATEWAY_URL", "pushgateway:9091")
    mocker.patch("prometheus_client.pushadd_to_gateway", side_effect=OSError("Verbindung abgelehnt"))
    assert metrics_push.push_pipeline_metrics(1.0, 1, 1, success=True) is False
