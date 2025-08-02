"""Comprehensive unit tests for connector components."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from saathy.connectors.base import ConnectorStatus, ContentType, ProcessedContent
from saathy.connectors.content_processor import ContentProcessor
from saathy.connectors.github_connector import GithubConnector


class TestBaseConnector:
    """Test cases for the BaseConnector abstract class."""

    def test_content_type_enum(self) -> None:
        """Test ContentType enum values."""
        assert ContentType.TEXT == "text"
        assert ContentType.CODE == "code"
        assert ContentType.MARKDOWN == "markdown"

    def test_connector_status_enum(self) -> None:
        """Test ConnectorStatus enum values."""
        assert ConnectorStatus.ACTIVE == "active"
        assert ConnectorStatus.INACTIVE == "inactive"
        assert ConnectorStatus.ERROR == "error"

    def test_processed_content_model(self) -> None:
        """Test ProcessedContent model creation and validation."""
        content = ProcessedContent(
            id="test-id",
            content="test content",
            content_type=ContentType.TEXT,
            source="test-source",
            metadata={"key": "value"},
            timestamp=datetime.utcnow(),
            raw_data={"raw": "data"},
        )

        assert content.id == "test-id"
        assert content.content == "test content"
        assert content.content_type == ContentType.TEXT
        assert content.source == "test-source"
        assert content.metadata["key"] == "value"
        assert content.raw_data["raw"] == "data"

    def test_base_connector_initialization(self) -> None:
        """Test BaseConnector initialization."""
        # Create a concrete implementation for testing
        class TestConnector(GithubConnector):
            pass

        connector = TestConnector("test-connector", {"config": "value"})
        assert connector.name == "test-connector"
        assert connector.config["config"] == "value"
        assert connector.status == ConnectorStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_base_connector_health_check(self) -> None:
        """Test BaseConnector health check method."""
        class TestConnector(GithubConnector):
            pass

        connector = TestConnector("test-connector", {})

        # Test inactive status
        assert not await connector.health_check()

        # Test active status
        connector.status = ConnectorStatus.ACTIVE
        assert await connector.health_check()

        # Test error status
        connector.status = ConnectorStatus.ERROR
        assert not await connector.health_check()


class TestGithubConnector:
    """Test cases for the GithubConnector class."""

    @pytest.fixture
    def github_connector(self) -> GithubConnector:
        """Create a GitHub connector instance for testing."""
        return GithubConnector("test-github", {
            "token": "test-token",
            "webhook_secret": "test-secret",
            "repositories": ["test/repo"],
        })

    @pytest.mark.asyncio
    async def test_github_connector_start_stop(self, github_connector: GithubConnector) -> None:
        """Test GitHub connector start and stop methods."""
        assert github_connector.status == ConnectorStatus.INACTIVE

        await github_connector.start()
        assert github_connector.status == ConnectorStatus.ACTIVE

        await github_connector.stop()
        assert github_connector.status == ConnectorStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_process_event_without_event_type(self, github_connector: GithubConnector) -> None:
        """Test processing event without event_type."""
        result = await github_connector.process_event({})
        assert result == []

    @pytest.mark.asyncio
    async def test_process_unsupported_event_type(self, github_connector: GithubConnector) -> None:
        """Test processing unsupported event type."""
        result = await github_connector.process_event({
            "event_type": "unsupported_event",
            "payload": {}
        })
        assert result == []

    @pytest.mark.asyncio
    async def test_process_push_event(self, github_connector: GithubConnector) -> None:
        """Test processing push event."""
        payload = {
            "repository": {"full_name": "test/repo"},
            "commits": [
                {
                    "id": "abc123",
                    "message": "test commit",
                    "url": "https://github.com/test/repo/commit/abc123",
                    "author": {"name": "Test User"},
                    "timestamp": "2023-01-01T00:00:00Z",
                }
            ],
            "ref": "refs/heads/main",
        }

        result = await github_connector.process_event({
            "event_type": "push",
            "payload": payload,
        })

        assert len(result) == 1
        assert result[0].id == "github:push:test/repo:abc123"
        assert result[0].content == "test commit"
        assert result[0].content_type == ContentType.TEXT
        assert result[0].metadata["author"] == "Test User"
        assert result[0].metadata["repository"] == "test/repo"

    @pytest.mark.asyncio
    async def test_process_pull_request_event(self, github_connector: GithubConnector) -> None:
        """Test processing pull request event."""
        payload = {
            "repository": {"full_name": "test/repo"},
            "pull_request": {
                "id": 123,
                "title": "Test PR",
                "body": "Test PR description",
                "html_url": "https://github.com/test/repo/pull/123",
                "user": {"login": "testuser"},
                "number": 123,
                "state": "open",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            "action": "opened",
        }

        result = await github_connector.process_event({
            "event_type": "pull_request",
            "payload": payload,
        })

        assert len(result) == 1
        assert result[0].id == "github:pull_request:test/repo:123"
        assert "Test PR" in result[0].content
        assert "Test PR description" in result[0].content
        assert result[0].content_type == ContentType.MARKDOWN
        assert result[0].metadata["action"] == "opened"
        assert result[0].metadata["user"] == "testuser"

    @pytest.mark.asyncio
    async def test_process_issues_event(self, github_connector: GithubConnector) -> None:
        """Test processing issues event."""
        payload = {
            "repository": {"full_name": "test/repo"},
            "issue": {
                "id": 456,
                "title": "Test Issue",
                "body": "Test issue description",
                "html_url": "https://github.com/test/repo/issues/456",
                "user": {"login": "testuser"},
                "number": 456,
                "state": "open",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            "action": "opened",
        }

        result = await github_connector.process_event({
            "event_type": "issues",
            "payload": payload,
        })

        assert len(result) == 1
        assert result[0].id == "github:issue:test/repo:456"
        assert "Test Issue" in result[0].content
        assert "Test issue description" in result[0].content
        assert result[0].content_type == ContentType.MARKDOWN
        assert result[0].metadata["action"] == "opened"
        assert result[0].metadata["user"] == "testuser"

    def test_extract_commit_content(self, github_connector: GithubConnector) -> None:
        """Test commit content extraction."""
        commit_data = {
            "repository": {"full_name": "test/repo"},
            "commits": [
                {
                    "id": "abc123",
                    "message": "test commit message",
                    "url": "https://github.com/test/repo/commit/abc123",
                    "author": {"name": "Test User", "email": "test@example.com"},
                    "timestamp": "2023-01-01T00:00:00Z",
                    "added": ["new_file.py"],
                    "modified": ["existing_file.py"],
                }
            ],
            "ref": "refs/heads/main",
        }

        result = github_connector.extract_commit_content(commit_data)

        # Should have 3 items: message, added file, modified file
        assert len(result) == 3

        # Check commit message
        message_item = next(item for item in result if "message" in item.id)
        assert message_item.content == "test commit message"
        assert message_item.metadata["commit_sha"] == "abc123"
        assert message_item.metadata["author"] == "Test User"
        assert message_item.metadata["branch"] == "main"

        # Check added file
        added_item = next(item for item in result if "added" in item.id)
        assert "new_file.py" in added_item.content
        assert added_item.metadata["change_type"] == "added"
        assert added_item.metadata["file_path"] == "new_file.py"

        # Check modified file
        modified_item = next(item for item in result if "modified" in item.id)
        assert "existing_file.py" in modified_item.content
        assert modified_item.metadata["change_type"] == "modified"
        assert modified_item.metadata["file_path"] == "existing_file.py"

    def test_extract_pr_content(self, github_connector: GithubConnector) -> None:
        """Test pull request content extraction."""
        pr_data = {
            "repository": {"full_name": "test/repo"},
            "pull_request": {
                "id": 123,
                "title": "Test PR Title",
                "body": "Test PR body content",
                "html_url": "https://github.com/test/repo/pull/123",
                "user": {"login": "testuser"},
                "number": 123,
                "state": "open",
                "updated_at": "2023-01-01T00:00:00Z",
                "comments": [
                    {
                        "id": 789,
                        "body": "Test comment",
                        "html_url": "https://github.com/test/repo/pull/123#issuecomment-789",
                        "user": {"login": "commenter"},
                        "created_at": "2023-01-01T01:00:00Z",
                    }
                ],
            },
            "action": "opened",
        }

        result = github_connector.extract_pr_content(pr_data)

        # Should have 3 items: title, body, comment
        assert len(result) == 3

        # Check title
        title_item = next(item for item in result if "title" in item.id)
        assert title_item.content == "Test PR Title"
        assert title_item.content_type == ContentType.TEXT

        # Check body
        body_item = next(item for item in result if "body" in item.id and "comment" not in item.id)
        assert body_item.content == "Test PR body content"
        assert body_item.content_type == ContentType.MARKDOWN

        # Check comment
        comment_item = next(item for item in result if "comment" in item.id)
        assert comment_item.content == "Test comment"
        assert comment_item.content_type == ContentType.MARKDOWN
        assert comment_item.metadata["user"] == "commenter"

    def test_extract_issue_content(self, github_connector: GithubConnector) -> None:
        """Test issue content extraction."""
        issue_data = {
            "repository": {"full_name": "test/repo"},
            "issue": {
                "id": 456,
                "title": "Test Issue Title",
                "body": "Test issue body content",
                "html_url": "https://github.com/test/repo/issues/456",
                "user": {"login": "testuser"},
                "number": 456,
                "state": "open",
                "updated_at": "2023-01-01T00:00:00Z",
                "labels": [{"name": "bug"}, {"name": "high-priority"}],
                "comments": [
                    {
                        "id": 999,
                        "body": "Test issue comment",
                        "html_url": "https://github.com/test/repo/issues/456#issuecomment-999",
                        "user": {"login": "commenter"},
                        "created_at": "2023-01-01T01:00:00Z",
                    }
                ],
            },
            "action": "opened",
        }

        result = github_connector.extract_issue_content(issue_data)

        # Should have 3 items: title, body, comment
        assert len(result) == 3

        # Check title
        title_item = next(item for item in result if "title" in item.id)
        assert title_item.content == "Test Issue Title"
        assert title_item.content_type == ContentType.TEXT
        assert "bug" in title_item.metadata["labels"]
        assert "high-priority" in title_item.metadata["labels"]

        # Check body
        body_item = next(item for item in result if "body" in item.id and "comment" not in item.id)
        assert body_item.content == "Test issue body content"
        assert body_item.content_type == ContentType.MARKDOWN

        # Check comment
        comment_item = next(item for item in result if "comment" in item.id)
        assert comment_item.content == "Test issue comment"
        assert comment_item.content_type == ContentType.MARKDOWN
        assert comment_item.metadata["user"] == "commenter"


class TestContentProcessor:
    """Test cases for the ContentProcessor class."""

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Create a mock embedding service."""
        service = MagicMock()
        service.embed_text = AsyncMock()
        service.embed_code = AsyncMock()
        return service

    @pytest.fixture
    def mock_vector_repo(self) -> MagicMock:
        """Create a mock vector repository."""
        repo = MagicMock()
        repo.upsert_vectors = AsyncMock(return_value=2)
        return repo

    @pytest.fixture
    def content_processor(self, mock_embedding_service: MagicMock, mock_vector_repo: MagicMock) -> ContentProcessor:
        """Create a content processor instance for testing."""
        return ContentProcessor(mock_embedding_service, mock_vector_repo)

    @pytest.mark.asyncio
    async def test_process_and_store_empty_list(self, content_processor: ContentProcessor) -> None:
        """Test processing empty content list."""
        result = await content_processor.process_and_store([])

        assert result["total_items"] == 0
        assert result["processed_items"] == 0
        assert result["failed_items"] == 0
        assert result["processing_time"] == 0.0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_process_and_store_text_content(self, content_processor: ContentProcessor) -> None:
        """Test processing text content."""
        # Setup mock embedding service
        mock_embedding_result = MagicMock()
        mock_embedding_result.embeddings.tolist.return_value = [0.1, 0.2, 0.3]
        mock_embedding_result.model_name = "test-model"
        mock_embedding_result.processing_time = 0.1
        mock_embedding_result.quality_score = 0.9

        content_processor.embedding_service.embed_text.return_value = mock_embedding_result

        # Create test content
        content_items = [
            ProcessedContent(
                id="test-1",
                content="test content 1",
                content_type=ContentType.TEXT,
                source="test-source-1",
                metadata={"key": "value1"},
                timestamp=datetime.utcnow(),
                raw_data={"raw": "data1"},
            ),
            ProcessedContent(
                id="test-2",
                content="test content 2",
                content_type=ContentType.TEXT,
                source="test-source-2",
                metadata={"key": "value2"},
                timestamp=datetime.utcnow(),
                raw_data={"raw": "data2"},
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["total_items"] == 2
        assert result["processed_items"] == 2
        assert result["failed_items"] == 0
        assert result["processing_time"] >= 0
        assert result["errors"] == []

        # Verify embedding service was called correctly
        assert content_processor.embedding_service.embed_text.call_count == 2
        content_processor.embedding_service.embed_text.assert_any_call(
            text="test content 1",
            content_type="text",
            metadata={"key": "value1"},
        )
        content_processor.embedding_service.embed_text.assert_any_call(
            text="test content 2",
            content_type="text",
            metadata={"key": "value2"},
        )

        # Verify vector repository was called
        content_processor.vector_repo.upsert_vectors.assert_called_once()
        call_args = content_processor.vector_repo.upsert_vectors.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0].id == "test-1"
        assert call_args[0].content == "test content 1"
        assert call_args[0].embedding == [0.1, 0.2, 0.3]
        assert call_args[0].metadata["embedding_model"] == "test-model"

    @pytest.mark.asyncio
    async def test_process_and_store_code_content(self, content_processor: ContentProcessor) -> None:
        """Test processing code content."""
        # Setup mock embedding service
        mock_embedding_result = MagicMock()
        mock_embedding_result.embeddings.tolist.return_value = [0.4, 0.5, 0.6]
        mock_embedding_result.model_name = "code-model"
        mock_embedding_result.processing_time = 0.2
        mock_embedding_result.quality_score = 0.8

        content_processor.embedding_service.embed_code.return_value = mock_embedding_result

        # Create test content
        content_items = [
            ProcessedContent(
                id="code-1",
                content="def test_function():\n    return True",
                content_type=ContentType.CODE,
                source="test-source",
                metadata={"language": "python"},
                timestamp=datetime.utcnow(),
                raw_data={"raw": "data"},
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["total_items"] == 1
        assert result["processed_items"] == 1
        assert result["failed_items"] == 0

        # Verify embedding service was called correctly
        content_processor.embedding_service.embed_code.assert_called_once_with(
            code="def test_function():\n    return True",
            metadata={"language": "python"},
        )

    @pytest.mark.asyncio
    async def test_process_and_store_embedding_failure(self, content_processor: ContentProcessor) -> None:
        """Test handling embedding service failures."""
        # Setup mock embedding service to fail
        content_processor.embedding_service.embed_text.side_effect = Exception("Embedding failed")

        content_items = [
            ProcessedContent(
                id="test-1",
                content="test content",
                content_type=ContentType.TEXT,
                source="test-source",
                metadata={},
                timestamp=datetime.utcnow(),
                raw_data={},
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["total_items"] == 1
        assert result["processed_items"] == 0
        assert result["failed_items"] == 1
        assert len(result["errors"]) == 1
        assert "Failed to process content item test-1" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_process_and_store_vector_repo_failure(self, content_processor: ContentProcessor) -> None:
        """Test handling vector repository failures."""
        # Setup mock embedding service
        mock_embedding_result = MagicMock()
        mock_embedding_result.embeddings.tolist.return_value = [0.1, 0.2, 0.3]
        mock_embedding_result.model_name = "test-model"
        mock_embedding_result.processing_time = 0.1
        mock_embedding_result.quality_score = 0.9

        content_processor.embedding_service.embed_text.return_value = mock_embedding_result

        # Setup mock vector repository to fail
        content_processor.vector_repo.upsert_vectors.side_effect = Exception("Vector repo failed")

        content_items = [
            ProcessedContent(
                id="test-1",
                content="test content",
                content_type=ContentType.TEXT,
                source="test-source",
                metadata={},
                timestamp=datetime.utcnow(),
                raw_data={},
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["total_items"] == 1
        assert result["processed_items"] == 0
        assert result["failed_items"] == 1
        assert len(result["errors"]) == 1
        assert "Failed to store documents in vector repository" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_process_and_store_mixed_content_types(self, content_processor: ContentProcessor) -> None:
        """Test processing mixed content types."""
        # Setup mock embedding service
        text_embedding_result = MagicMock()
        text_embedding_result.embeddings.tolist.return_value = [0.1, 0.2, 0.3]
        text_embedding_result.model_name = "text-model"
        text_embedding_result.processing_time = 0.1
        text_embedding_result.quality_score = 0.9

        code_embedding_result = MagicMock()
        code_embedding_result.embeddings.tolist.return_value = [0.4, 0.5, 0.6]
        code_embedding_result.model_name = "code-model"
        code_embedding_result.processing_time = 0.2
        code_embedding_result.quality_score = 0.8

        content_processor.embedding_service.embed_text.return_value = text_embedding_result
        content_processor.embedding_service.embed_code.return_value = code_embedding_result

        # Create test content with mixed types
        content_items = [
            ProcessedContent(
                id="text-1",
                content="test text content",
                content_type=ContentType.TEXT,
                source="test-source",
                metadata={},
                timestamp=datetime.utcnow(),
                raw_data={},
            ),
            ProcessedContent(
                id="code-1",
                content="def test():\n    pass",
                content_type=ContentType.CODE,
                source="test-source",
                metadata={},
                timestamp=datetime.utcnow(),
                raw_data={},
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["total_items"] == 2
        assert result["processed_items"] == 2
        assert result["failed_items"] == 0

        # Verify both embedding methods were called
        content_processor.embedding_service.embed_text.assert_called_once()
        content_processor.embedding_service.embed_code.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_commits(self) -> None:
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

    @pytest.mark.asyncio
    async def test_empty_commits_process_event(self) -> None:
        """Test process_event with empty commits."""
        connector = GithubConnector("test-github", {})

        payload = {
            "repository": {"full_name": "test/repo"},
            "commits": [],
            "ref": "refs/heads/main",
        }

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

    def test_missing_pr_fields(self) -> None:
        """Test handling of PR payloads with missing fields."""
        connector = GithubConnector("test-github", {})

        # Test with missing title
        pr_data = {
            "repository": {"full_name": "test/repo"},
            "pull_request": {
                "id": 123,
                "body": "Test PR body",
                "user": {"login": "testuser"},
                "number": 123,
            },
        }

        result = connector.extract_pr_content(pr_data)
        # Should still process body and comments if available
        assert len(result) >= 1

    def test_missing_issue_fields(self) -> None:
        """Test handling of issue payloads with missing fields."""
        connector = GithubConnector("test-github", {})

        # Test with missing title
        issue_data = {
            "repository": {"full_name": "test/repo"},
            "issue": {
                "id": 456,
                "body": "Test issue body",
                "user": {"login": "testuser"},
                "number": 456,
            },
        }

        result = connector.extract_issue_content(issue_data)
        # Should still process body and comments if available
        assert len(result) >= 1

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

    def test_content_processor_initialization(self) -> None:
        """Test ContentProcessor initialization."""
        mock_embedding_service = MagicMock()
        mock_vector_repo = MagicMock()

        processor = ContentProcessor(mock_embedding_service, mock_vector_repo)

        assert processor.embedding_service == mock_embedding_service
        assert processor.vector_repo == mock_vector_repo
