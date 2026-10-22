import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import main  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("CHAOS_ENABLED", "true")
    main._orders.clear()
    main._chaos = main.ChaosConfig()
    return TestClient(main.app)


def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_create_and_get_order(client):
    created = client.post("/orders", json={"item": "keyboard", "quantity": 2})
    assert created.status_code == 201
    order_id = created.json()["id"]
    fetched = client.get(f"/orders/{order_id}")
    assert fetched.status_code == 200
    assert fetched.json()["item"] == "keyboard"


def test_validation_rejects_bad_quantity(client):
    assert client.post("/orders", json={"item": "x", "quantity": 0}).status_code == 422


def test_missing_order_returns_404(client):
    assert client.get("/orders/does-not-exist").status_code == 404


def test_metrics_use_route_templates(client):
    client.get("/orders/abc")
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert 'route="/orders/{order_id}"' in body
    assert 'route="/orders/abc"' not in body


def test_chaos_error_injection(client):
    client.post("/chaos", json={"latency_ms": 0, "error_rate": 1.0})
    assert client.get("/orders").status_code == 500
    client.post("/chaos", json={"latency_ms": 0, "error_rate": 0.0})
    assert client.get("/orders").status_code == 200


def test_chaos_disabled_by_default(client, monkeypatch):
    monkeypatch.setenv("CHAOS_ENABLED", "false")
    assert client.post("/chaos", json={"error_rate": 0.5}).status_code == 403
