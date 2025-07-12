"""Test health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from saathy.api import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


def test_healthz_endpoint(client: TestClient) -> None:
    """Test that /healthz endpoint returns 200 and correct response."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"} 