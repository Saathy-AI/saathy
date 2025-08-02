"""Pytest configuration and common fixtures for connector tests."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from saathy.connectors.base import ContentType, ProcessedContent
from saathy.connectors.github_connector import GithubConnector


@pytest.fixture
def sample_processed_content() -> ProcessedContent:
    """Create a sample ProcessedContent instance for testing."""
    return ProcessedContent(
        id="test-content-1",
        content="This is test content for processing",
        content_type=ContentType.TEXT,
        source="test-source",
        metadata={
            "author": "testuser",
            "repository": "test/repo",
            "event_type": "test",
        },
        timestamp=datetime.utcnow(),
        raw_data={"test": "data"},
    )


@pytest.fixture
def sample_github_connector() -> GithubConnector:
    """Create a sample GitHub connector for testing."""
    return GithubConnector("test-github", {
        "token": "test-token",
        "webhook_secret": "test-secret",
        "repositories": ["test/repo"],
    })


@pytest.fixture
def sample_push_event_data() -> dict:
    """Sample GitHub push event data."""
    return {
        "event_type": "push",
        "payload": {
            "repository": {"full_name": "test/repo"},
            "commits": [
                {
                    "id": "abc123",
                    "message": "feat: add new feature",
                    "url": "https://github.com/test/repo/commit/abc123",
                    "author": {"name": "Test User", "email": "test@example.com"},
                    "timestamp": "2023-01-01T12:00:00Z",
                    "added": ["src/new_file.py"],
                    "modified": ["src/existing_file.py"],
                }
            ],
            "ref": "refs/heads/main",
        },
    }


@pytest.fixture
def sample_pr_event_data() -> dict:
    """Sample GitHub pull request event data."""
    return {
        "event_type": "pull_request",
        "payload": {
            "repository": {"full_name": "test/repo"},
            "pull_request": {
                "id": 123,
                "title": "Add new feature",
                "body": "This PR adds a new feature to the application.",
                "html_url": "https://github.com/test/repo/pull/123",
                "user": {"login": "testuser"},
                "number": 123,
                "state": "open",
                "updated_at": "2023-01-01T10:00:00Z",
                "comments": [
                    {
                        "id": 456,
                        "body": "Great work!",
                        "html_url": "https://github.com/test/repo/pull/123#issuecomment-456",
                        "user": {"login": "reviewer"},
                        "created_at": "2023-01-01T11:00:00Z",
                    }
                ],
            },
            "action": "opened",
        },
    }


@pytest.fixture
def sample_issue_event_data() -> dict:
    """Sample GitHub issue event data."""
    return {
        "event_type": "issues",
        "payload": {
            "repository": {"full_name": "test/repo"},
            "issue": {
                "id": 789,
                "title": "Bug report",
                "body": "There is a bug in the application.",
                "html_url": "https://github.com/test/repo/issues/789",
                "user": {"login": "reporter"},
                "number": 789,
                "state": "open",
                "updated_at": "2023-01-01T09:00:00Z",
                "labels": [
                    {"name": "bug"},
                    {"name": "high-priority"},
                ],
                "comments": [
                    {
                        "id": 999,
                        "body": "I can reproduce this issue.",
                        "html_url": "https://github.com/test/repo/issues/789#issuecomment-999",
                        "user": {"login": "developer"},
                        "created_at": "2023-01-01T10:00:00Z",
                    }
                ],
            },
            "action": "opened",
        },
    }


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = MagicMock()
    service.embed_text = MagicMock()
    service.embed_code = MagicMock()
    return service


@pytest.fixture
def mock_vector_repository():
    """Create a mock vector repository."""
    repo = MagicMock()
    repo.upsert_vectors = MagicMock(return_value=1)
    repo.health_check = MagicMock(return_value=True)
    return repo


@pytest.fixture
def mock_settings():
    """Create mock settings with GitHub configuration."""
    settings = MagicMock()
    settings.github_webhook_secret_str = "test-secret"
    settings.github_token_str = "test-token"
    settings.github_repositories = "test/repo"
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_collection_name = "test-collection"
    settings.qdrant_vector_size = 384
    settings.qdrant_api_key_str = None
    return settings
