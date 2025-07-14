"""Test health check endpoint."""

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from saathy.api import app, get_vector_repo


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_endpoint(client: TestClient) -> None:
    """Test that /healthz endpoint returns 200 and correct response."""

    async def mock_health_check() -> bool:
        return True

    app.dependency_overrides[get_vector_repo] = lambda: AsyncMock(
        health_check=mock_health_check,
    )

    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "dependencies": {"qdrant": "healthy"},
    }

    app.dependency_overrides.clear()
