"""Test health check endpoints."""

from fastapi.testclient import TestClient

from saathy.api import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "qdrant" in data["dependencies"]


def test_readiness_check():
    """Test the readiness check endpoint."""
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_config_endpoint():
    """Test the config endpoint."""
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "environment" in data
    assert "debug" in data
