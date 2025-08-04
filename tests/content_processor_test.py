"""Tests for the content processing pipeline."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from saathy.connectors.base import ContentType, ProcessedContent
from saathy.connectors.content_processor import ContentProcessor
from saathy.embedding.service import EmbeddingService
from saathy.vector.repository import VectorRepository


class TestContentProcessor:
    """Test the ContentProcessor class."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = AsyncMock(spec=EmbeddingService)

        # Mock embedding result
        mock_result = MagicMock()
        mock_result.embeddings = [0.1, 0.2, 0.3, 0.4, 0.5] * 20  # 100-dim vector
        mock_result.model_name = "text-embedding-ada-002"
        mock_result.quality_score = 0.95
        mock_result.processing_time = 0.5

        service.embed_text.return_value = mock_result
        return service

    @pytest.fixture
    def mock_vector_repo(self):
        """Create a mock vector repository."""
        repo = AsyncMock(spec=VectorRepository)
        repo.store_vectors = AsyncMock()
        return repo

    @pytest.fixture
    def content_processor(self, mock_embedding_service, mock_vector_repo):
        """Create a content processor with mocked dependencies."""
        return ContentProcessor(mock_embedding_service, mock_vector_repo)

    @pytest.fixture
    def sample_content(self):
        """Create a sample ProcessedContent for testing."""
        return ProcessedContent(
            id="test_message_123",
            content="This is a test Slack message with some meaningful content.",
            content_type=ContentType.TEXT,
            source="slack",
            metadata={
                "channel_id": "C1234567890",
                "channel_name": "test-channel",
                "user_id": "U1234567890",
                "timestamp": "1234567890.123",
                "is_thread_reply": False,
            },
            timestamp=datetime.now(),
            raw_data={
                "text": "This is a test Slack message with some meaningful content."
            },
        )

    async def test_process_single_content_success(
        self,
        content_processor,
        sample_content,
        mock_embedding_service,
        mock_vector_repo,
    ):
        """Test successful processing of a single content item."""
        result = await content_processor.process_and_store([sample_content])

        assert result["processed"] == 1
        assert result["errors_count"] == 0
        assert result["processing_time"] > 0

        # Verify embedding service was called
        mock_embedding_service.embed_text.assert_called_once_with(
            text=sample_content.content,
            content_type="text",
            metadata=sample_content.metadata,
        )

        # Verify vector repository was called
        mock_vector_repo.upsert_vectors.assert_called_once()
        call_args = mock_vector_repo.upsert_vectors.call_args[0][0]
        assert len(call_args) == 1

        vector_data = call_args[0]
        # Check that it's a VectorDocument object
        assert hasattr(vector_data, "id")
        assert hasattr(vector_data, "content")
        assert hasattr(vector_data, "embedding")
        assert hasattr(vector_data, "metadata")
        assert vector_data.metadata["source"] == "slack"
        assert vector_data.metadata["content_type"] == "text"
        assert vector_data.metadata["channel_id"] == "C1234567890"

    async def test_process_single_content_too_short(self, content_processor):
        """Test that very short content is skipped."""
        short_content = ProcessedContent(
            id="short_message",
            content="Hi",
            content_type=ContentType.TEXT,
            source="slack",
            metadata={},
            timestamp=datetime.now(),
            raw_data={"text": "Hi"},
        )

        result = await content_processor._process_single_content(short_content)

        assert result["status"] == "skipped"
        assert result["reason"] == "content_too_short"

    async def test_process_single_content_embedding_failure(
        self, content_processor, sample_content, mock_embedding_service
    ):
        """Test handling of embedding generation failure."""
        mock_embedding_service.embed_text.return_value = None

        result = await content_processor._process_single_content(sample_content)

        assert result["status"] == "error"
        assert result["error"] == "failed_to_generate_embedding"

    async def test_process_and_store_multiple_items(
        self,
        content_processor,
        sample_content,
        mock_embedding_service,
        mock_vector_repo,
    ):
        """Test processing multiple content items."""
        content_items = [
            sample_content,
            ProcessedContent(
                id="test_message_456",
                content="Another test message with sufficient content length.",
                content_type=ContentType.TEXT,
                source="slack",
                metadata={"channel_id": "C0987654321"},
                timestamp=datetime.now(),
                raw_data={
                    "text": "Another test message with sufficient content length."
                },
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["processed"] == 2
        assert result["errors_count"] == 0
        assert result["skipped"] == 0
        assert result["processing_time"] > 0
        assert len(result["items"]) == 2

        # Verify all items were processed successfully
        for item in result["items"]:
            assert item["status"] == "success"

    async def test_process_and_store_with_errors(
        self, content_processor, sample_content, mock_embedding_service
    ):
        """Test processing with some errors."""
        # Make embedding service fail for one item
        mock_embedding_service.embed_text.side_effect = [
            Exception("Embedding failed"),  # First call fails
            MagicMock(
                embeddings=[0.1] * 100,
                model_name="test",
                quality_score=0.9,
                processing_time=0.1,
            ),  # Second call succeeds
        ]

        content_items = [
            sample_content,
            ProcessedContent(
                id="test_message_789",
                content="This should succeed.",
                content_type=ContentType.TEXT,
                source="slack",
                metadata={},
                timestamp=datetime.now(),
                raw_data={"text": "This should succeed."},
            ),
        ]

        result = await content_processor.process_and_store(content_items)

        assert result["processed"] == 1
        assert result["errors_count"] == 1
        assert result["skipped"] == 0
        assert len(result["items"]) == 2

    def test_prepare_vector_data(
        self, content_processor, sample_content, mock_embedding_service
    ):
        """Test vector data preparation."""
        mock_result = MagicMock()
        mock_result.embeddings = [0.1, 0.2, 0.3] * 33  # 99-dim vector
        mock_result.model_name = "test-model"
        mock_result.quality_score = 0.88

        vector_data = content_processor._prepare_vector_data_dict(
            sample_content, mock_result
        )

        assert "id" in vector_data
        assert "vector" in vector_data
        assert "payload" in vector_data

        payload = vector_data["payload"]
        assert payload["source"] == "slack"
        assert payload["content_type"] == "text"
        assert payload["channel_id"] == "C1234567890"
        assert payload["channel_name"] == "test-channel"
        assert payload["user_id"] == "U1234567890"
        assert payload["model_name"] == "test-model"
        assert payload["embedding_quality"] == 0.88
        assert payload["content_length"] == len(sample_content.content)
        assert payload["word_count"] == len(sample_content.content.split())
