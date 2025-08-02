"""Integration tests for connector functionality."""

from unittest.mock import MagicMock

import pytest

from saathy.connectors.base import ContentType
from saathy.connectors.content_processor import ContentProcessor
from saathy.connectors.github_connector import GithubConnector


class TestConnectorIntegration:
    """Integration tests for connector components."""

    @pytest.fixture
    def sample_push_payload(self) -> dict:
        """Sample GitHub push event payload."""
        return {
            "repository": {
                "full_name": "test/repo",
                "name": "repo",
                "owner": {"login": "test"},
            },
            "commits": [
                {
                    "id": "abc123def456",
                    "message": "feat: add new feature",
                    "url": "https://github.com/test/repo/commit/abc123def456",
                    "author": {
                        "name": "Test User",
                        "email": "test@example.com",
                    },
                    "timestamp": "2023-01-01T12:00:00Z",
                    "added": ["src/new_file.py"],
                    "modified": ["src/existing_file.py"],
                    "removed": [],
                }
            ],
            "ref": "refs/heads/main",
            "before": "old123",
            "after": "abc123def456",
        }

    @pytest.fixture
    def sample_pr_payload(self) -> dict:
        """Sample GitHub pull request event payload."""
        return {
            "repository": {
                "full_name": "test/repo",
                "name": "repo",
                "owner": {"login": "test"},
            },
            "pull_request": {
                "id": 123,
                "number": 123,
                "title": "Add new feature",
                "body": "This PR adds a new feature to the application.",
                "html_url": "https://github.com/test/repo/pull/123",
                "user": {"login": "testuser"},
                "state": "open",
                "created_at": "2023-01-01T10:00:00Z",
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
        }

    @pytest.fixture
    def sample_issue_payload(self) -> dict:
        """Sample GitHub issue event payload."""
        return {
            "repository": {
                "full_name": "test/repo",
                "name": "repo",
                "owner": {"login": "test"},
            },
            "issue": {
                "id": 789,
                "number": 789,
                "title": "Bug report",
                "body": "There is a bug in the application.",
                "html_url": "https://github.com/test/repo/issues/789",
                "user": {"login": "reporter"},
                "state": "open",
                "created_at": "2023-01-01T09:00:00Z",
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
        }

    @pytest.mark.asyncio
    async def test_push_event_processing(self, sample_push_payload: dict) -> None:
        """Test push event processing through the connector."""
        connector = GithubConnector("test-github", {})

        # Test the process_event method
        event_data = {"event_type": "push", "payload": sample_push_payload}
        result = await connector.process_event(event_data)

        assert len(result) == 1
        assert result[0].content == "feat: add new feature"
        assert result[0].content_type == ContentType.TEXT
        assert result[0].metadata["author"] == "Test User"
        assert result[0].metadata["repository"] == "test/repo"
        assert result[0].metadata["ref"] == "refs/heads/main"

        # Test the extract_commit_content method
        extracted = connector.extract_commit_content(sample_push_payload)
        assert len(extracted) == 3  # message + added file + modified file

        # Check commit message
        message_item = next(item for item in extracted if "message" in item.id)
        assert message_item.content == "feat: add new feature"
        assert message_item.metadata["commit_sha"] == "abc123def456"
        assert message_item.metadata["branch"] == "main"
        assert message_item.metadata["author"] == "Test User"
        assert message_item.metadata["author_email"] == "test@example.com"

        # Check added file
        added_item = next(item for item in extracted if "added" in item.id)
        assert "new_file.py" in added_item.content
        assert added_item.metadata["change_type"] == "added"
        assert added_item.metadata["file_path"] == "src/new_file.py"

        # Check modified file
        modified_item = next(item for item in extracted if "modified" in item.id)
        assert "existing_file.py" in modified_item.content
        assert modified_item.metadata["change_type"] == "modified"
        assert modified_item.metadata["file_path"] == "src/existing_file.py"

    @pytest.mark.asyncio
    async def test_pr_event_processing(self, sample_pr_payload: dict) -> None:
        """Test pull request event processing through the connector."""
        connector = GithubConnector("test-github", {})

        # Test the process_event method
        event_data = {"event_type": "pull_request", "payload": sample_pr_payload}
        result = await connector.process_event(event_data)

        assert len(result) == 1
        assert "Add new feature" in result[0].content
        assert "This PR adds a new feature" in result[0].content
        assert result[0].content_type == ContentType.MARKDOWN
        assert result[0].metadata["action"] == "opened"
        assert result[0].metadata["user"] == "testuser"
        assert result[0].metadata["number"] == 123

        # Test the extract_pr_content method
        extracted = connector.extract_pr_content(sample_pr_payload)
        assert len(extracted) == 3  # title + body + comment

        # Check title
        title_item = next(item for item in extracted if "title" in item.id)
        assert title_item.content == "Add new feature"
        assert title_item.content_type == ContentType.TEXT
        assert title_item.metadata["pr_number"] == 123
        assert title_item.metadata["user"] == "testuser"

        # Check body
        body_item = next(item for item in extracted if "body" in item.id and "comment" not in item.id)
        assert body_item.content == "This PR adds a new feature to the application."
        assert body_item.content_type == ContentType.MARKDOWN
        assert body_item.metadata["pr_number"] == 123

        # Check comment
        comment_item = next(item for item in extracted if "comment" in item.id)
        assert comment_item.content == "Great work!"
        assert comment_item.content_type == ContentType.MARKDOWN
        assert comment_item.metadata["user"] == "reviewer"
        assert comment_item.metadata["comment_id"] == 456

    @pytest.mark.asyncio
    async def test_issue_event_processing(self, sample_issue_payload: dict) -> None:
        """Test issue event processing through the connector."""
        connector = GithubConnector("test-github", {})

        # Test the process_event method
        event_data = {"event_type": "issues", "payload": sample_issue_payload}
        result = await connector.process_event(event_data)

        assert len(result) == 1
        assert "Bug report" in result[0].content
        assert "There is a bug in the application" in result[0].content
        assert result[0].content_type == ContentType.MARKDOWN
        assert result[0].metadata["action"] == "opened"
        assert result[0].metadata["user"] == "reporter"
        assert result[0].metadata["number"] == 789

        # Test the extract_issue_content method
        extracted = connector.extract_issue_content(sample_issue_payload)
        assert len(extracted) == 3  # title + body + comment

        # Check title
        title_item = next(item for item in extracted if "title" in item.id)
        assert title_item.content == "Bug report"
        assert title_item.content_type == ContentType.TEXT
        assert "bug" in title_item.metadata["labels"]
        assert "high-priority" in title_item.metadata["labels"]
        assert title_item.metadata["issue_number"] == 789
        assert title_item.metadata["user"] == "reporter"

        # Check body
        body_item = next(item for item in extracted if "body" in item.id and "comment" not in item.id)
        assert body_item.content == "There is a bug in the application."
        assert body_item.content_type == ContentType.MARKDOWN
        assert body_item.metadata["issue_number"] == 789

        # Check comment
        comment_item = next(item for item in extracted if "comment" in item.id)
        assert comment_item.content == "I can reproduce this issue."
        assert comment_item.content_type == ContentType.MARKDOWN
        assert comment_item.metadata["user"] == "developer"
        assert comment_item.metadata["comment_id"] == 999

    @pytest.mark.asyncio
    async def test_connector_lifecycle(self) -> None:
        """Test connector lifecycle (start/stop/health check)."""
        connector = GithubConnector("test-github", {
            "token": "test-token",
            "webhook_secret": "test-secret",
            "repositories": ["test/repo"],
        })

        # Initial state
        assert connector.name == "test-github"
        assert connector.status.value == "inactive"
        assert not await connector.health_check()

        # Start connector
        await connector.start()
        assert connector.status.value == "active"
        assert await connector.health_check()

        # Stop connector
        await connector.stop()
        assert connector.status.value == "inactive"
        assert not await connector.health_check()

    def test_content_processor_with_mocks(self) -> None:
        """Test content processor with mocked dependencies."""
        # Create mock dependencies
        mock_embedding_service = MagicMock()
        mock_vector_repo = MagicMock()

        # Create content processor
        processor = ContentProcessor(mock_embedding_service, mock_vector_repo)

        # Test that processor can be created and has expected attributes
        assert processor.embedding_service == mock_embedding_service
        assert processor.vector_repo == mock_vector_repo

    @pytest.mark.asyncio
    async def test_unsupported_event_type(self) -> None:
        """Test handling of unsupported event types."""
        connector = GithubConnector("test-github", {})

        event_data = {
            "event_type": "unsupported_event",
            "payload": {"test": "data"}
        }

        # This should return an empty list for unsupported events
        result = await connector.process_event(event_data)
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_commits(self) -> None:
        """Test handling of push events with no commits."""
        connector = GithubConnector("test-github", {})

        payload = {
            "repository": {"full_name": "test/repo"},
            "commits": [],
            "ref": "refs/heads/main",
        }

        # Test extract_commit_content with empty commits
        result = connector.extract_commit_content(payload)
        assert result == []

        # Test process_event with empty commits
        event_data = {"event_type": "push", "payload": payload}
        result = await connector.process_event(event_data)
        assert result == []

    def test_missing_required_fields(self) -> None:
        """Test handling of payloads with missing required fields."""
        connector = GithubConnector("test-github", {})

        # Test with missing repository
        payload = {"commits": [{"id": "abc123", "message": "test"}]}
        result = connector.extract_commit_content(payload)
        assert len(result) == 1  # Should still process the commit
        assert result[0].metadata["repository"] == "unknown"

        # Test with missing commit ID
        payload = {
            "repository": {"full_name": "test/repo"},
            "commits": [{"message": "test"}],  # No ID
        }
        result = connector.extract_commit_content(payload)
        assert result == []  # Should skip commits without ID
