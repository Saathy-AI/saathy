"""Test health check endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from saathy.api import app, get_vector_repo

client = TestClient(app)


@pytest.fixture
def mock_vector_repo():
    """Mock vector repository for testing."""
    mock_repo = AsyncMock()
    mock_repo.health_check.return_value = True
    return mock_repo


def test_health_check(mock_vector_repo):
    """Test the health check endpoint."""
    # Override the dependency
    app.dependency_overrides[get_vector_repo] = lambda: mock_vector_repo

    try:
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data
        assert "qdrant" in data["dependencies"]
        assert data["status"] == "healthy"
        assert data["dependencies"]["qdrant"] == "healthy"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


def test_health_check_qdrant_unhealthy(mock_vector_repo):
    """Test the health check endpoint when Qdrant is unhealthy."""
    mock_vector_repo.health_check.return_value = False

    # Override the dependency
    app.dependency_overrides[get_vector_repo] = lambda: mock_vector_repo

    try:
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["dependencies"]["qdrant"] == "unhealthy"
    finally:
        # Clean up the override
        app.dependency_overrides.clear()


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
