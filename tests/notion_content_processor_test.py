"""Tests for NotionContentProcessor advanced content processing capabilities."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from saathy.connectors.base import ContentType, ProcessedContent
from saathy.connectors.content_processor import (
    NotionContentProcessor,
    NotionProcessingResult,
)
from saathy.vector.models import VectorDocument


class TestNotionContentProcessor:
    """Test suite for NotionContentProcessor."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        service = AsyncMock()

        # Mock embedding result
        mock_result = MagicMock()
        mock_result.embeddings = [0.1, 0.2, 0.3, 0.4, 0.5]  # 5-dimensional vector
        mock_result.model_name = "all-MiniLM-L6-v2"
        mock_result.processing_time = 0.1
        mock_result.quality_score = 0.95

        service.embed_text.return_value = mock_result
        return service

    @pytest.fixture
    def mock_vector_repo(self):
        """Create a mock vector repository."""
        repo = AsyncMock()
        repo.upsert_vectors = AsyncMock()
        return repo

    @pytest.fixture
    def processor(self, mock_embedding_service, mock_vector_repo):
        """Create a NotionContentProcessor instance."""
        return NotionContentProcessor(mock_embedding_service, mock_vector_repo)

    @pytest.fixture
    def sample_notion_content(self):
        """Create sample Notion content for testing."""
        return ProcessedContent(
            id="test-page-123",
            content="This is a test page with some content. It has # headers and some **bold** text.",
            content_type=ContentType.TEXT,
            source="notion",
            metadata={
                "type": "page",
                "page_id": "test-page-123",
                "title": "Test Page",
                "url": "https://notion.so/test-page-123",
                "created_time": "2024-01-01T00:00:00Z",
                "last_edited_time": "2024-01-02T00:00:00Z",
                "parent_database": "Test Database",
                "database_id": "test-db-456",
            },
            timestamp=datetime.now(),
            raw_data={},
        )

    @pytest.fixture
    def sample_code_content(self):
        """Create sample code content for testing."""
        return ProcessedContent(
            id="test-code-789",
            content="```python\ndef hello_world():\n    print('Hello, World!')\n```",
            content_type=ContentType.CODE,
            source="notion",
            metadata={
                "type": "code_block",
                "page_id": "test-page-123",
                "language": "python",
                "title": "Test Code Block",
            },
            timestamp=datetime.now(),
            raw_data={},
        )

    @pytest.mark.asyncio
    async def test_process_notion_content_success(
        self, processor, sample_notion_content
    ):
        """Test successful processing of Notion content."""
        result = await processor.process_notion_content([sample_notion_content])

        assert isinstance(result, NotionProcessingResult)
        assert result.processed == 1
        assert result.errors == 0
        assert result.skipped == 0
        assert result.processing_time > 0
        assert len(result.items) == 1
        assert result.items[0]["status"] == "success"
        assert result.notion_specific_stats["pages_processed"] == 1

    @pytest.mark.asyncio
    async def test_process_notion_content_short_content(self, processor):
        """Test that very short content is skipped."""
        short_content = ProcessedContent(
            id="short-content",
            content="Hi",  # Too short
            content_type=ContentType.TEXT,
            source="notion",
            metadata={"type": "page"},
            timestamp=datetime.now(),
            raw_data={},
        )

        result = await processor.process_notion_content([short_content])

        assert result.skipped == 1
        assert result.processed == 0
        assert result.items[0]["status"] == "skipped"
        assert result.items[0]["reason"] == "content_too_short"

    @pytest.mark.asyncio
    async def test_select_embedding_model_code(self, processor, sample_code_content):
        """Test that code content selects the correct embedding model."""
        model_name = processor._select_embedding_model(sample_code_content)
        assert model_name == "microsoft/codebert-base"

    @pytest.mark.asyncio
    async def test_select_embedding_model_long_content(self, processor):
        """Test that long content selects high-quality model."""
        long_content = ProcessedContent(
            id="long-content",
            content="This is a very long piece of content. " * 50,  # > 500 chars
            content_type=ContentType.TEXT,
            source="notion",
            metadata={"type": "page"},
            timestamp=datetime.now(),
            raw_data={},
        )

        model_name = processor._select_embedding_model(long_content)
        assert model_name == "all-mpnet-base-v2"

    @pytest.mark.asyncio
    async def test_select_embedding_model_short_content(
        self, processor, sample_notion_content
    ):
        """Test that short content selects fast model."""
        model_name = processor._select_embedding_model(sample_notion_content)
        assert model_name == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio
    async def test_prepare_notion_vector_data(
        self, processor, sample_notion_content, mock_embedding_service
    ):
        """Test preparation of Notion vector data with rich metadata."""
        # Create mock embedding result
        mock_result = MagicMock()
        mock_result.embeddings = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_result.model_name = "all-MiniLM-L6-v2"
        mock_result.quality_score = 0.95

        vector_data = processor._prepare_notion_vector_data(
            sample_notion_content, mock_result
        )

        assert isinstance(vector_data, VectorDocument)
        assert vector_data.id is not None
        assert vector_data.content == sample_notion_content.content
        assert vector_data.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

        # Check rich metadata
        metadata = vector_data.metadata
        assert metadata["source"] == "notion"
        assert metadata["notion_type"] == "page"
        assert metadata["page_id"] == "test-page-123"
        assert metadata["title"] == "Test Page"
        assert metadata["parent_database"] == "Test Database"
        assert metadata["has_code"] is False
        assert metadata["has_links"] is False
        assert metadata["has_lists"] is False
        assert metadata["header_count"] == 1
        assert "notion" in metadata["tags"]
        assert "type:page" in metadata["tags"]
        assert "database:test_database" in metadata["tags"]

    @pytest.mark.asyncio
    async def test_generate_content_tags(self, processor, sample_notion_content):
        """Test generation of content tags."""
        tags = processor._generate_content_tags(
            sample_notion_content, sample_notion_content.metadata
        )

        assert "notion" in tags
        assert "type:page" in tags
        assert "database:test_database" in tags
        assert "short_form" in tags  # Content is short

    @pytest.mark.asyncio
    async def test_generate_content_tags_code(self, processor, sample_code_content):
        """Test generation of content tags for code."""
        tags = processor._generate_content_tags(
            sample_code_content, sample_code_content.metadata
        )

        assert "notion" in tags
        assert "type:code_block" in tags
        assert "code" in tags
        assert "lang:python" in tags
        assert "contains_code" in tags

    @pytest.mark.asyncio
    async def test_extract_content_hierarchy(self, processor):
        """Test extraction of content hierarchy."""
        content_with_headers = ProcessedContent(
            id="hierarchical-content",
            content="# Main Header\n## Sub Header\n### Sub Sub Header\nSome content here.",
            content_type=ContentType.TEXT,
            source="notion",
            metadata={"title": "Test Page", "parent_database": "Test Database"},
            timestamp=datetime.now(),
            raw_data={},
        )

        hierarchy = processor._extract_content_hierarchy(
            content_with_headers, content_with_headers.metadata
        )

        assert hierarchy["page_title"] == "Test Page"
        assert hierarchy["database_name"] == "Test Database"
        assert "headers" in hierarchy
        assert len(hierarchy["headers"]) == 3
        assert hierarchy["headers"][0]["text"] == "Main Header"
        assert hierarchy["headers"][0]["level"] == 1
        assert hierarchy["main_header"] == "Main Header"

    @pytest.mark.asyncio
    async def test_update_notion_stats(self, processor, sample_notion_content):
        """Test updating of Notion processing statistics."""
        stats = {
            "pages_processed": 0,
            "databases_processed": 0,
            "code_blocks_processed": 0,
            "properties_extracted": 0,
            "total_content_length": 0,
        }

        result = {"content_length": 100}

        processor._update_notion_stats(stats, sample_notion_content, result)

        assert stats["pages_processed"] == 1
        assert stats["total_content_length"] == 100

    @pytest.mark.asyncio
    async def test_process_notion_content_error_handling(
        self, processor, mock_embedding_service
    ):
        """Test error handling during content processing."""
        # Mock embedding service to raise an exception
        mock_embedding_service.embed_text.side_effect = Exception("Embedding failed")

        content = ProcessedContent(
            id="error-content",
            content="This content will cause an error",
            content_type=ContentType.TEXT,
            source="notion",
            metadata={"type": "page"},
            timestamp=datetime.now(),
            raw_data={},
        )

        result = await processor.process_notion_content([content])

        assert result.errors == 1
        assert result.processed == 0
        assert result.items[0]["status"] == "error"
        assert "Embedding failed" in result.items[0]["error"]

    @pytest.mark.asyncio
    async def test_process_notion_content_mixed_results(
        self, processor, sample_notion_content
    ):
        """Test processing with mixed success and error results."""
        # Create content that will be skipped
        short_content = ProcessedContent(
            id="short-content",
            content="Hi",
            content_type=ContentType.TEXT,
            source="notion",
            metadata={"type": "page"},
            timestamp=datetime.now(),
            raw_data={},
        )

        # Mock embedding service to fail for the second content
        processor.embedding_service.embed_text.side_effect = [
            MagicMock(
                embeddings=[0.1, 0.2, 0.3],
                model_name="test",
                processing_time=0.1,
                quality_score=0.9,
            ),
            Exception("Embedding failed"),
        ]

        result = await processor.process_notion_content(
            [sample_notion_content, short_content]
        )

        assert result.processed == 1
        assert result.skipped == 1
        assert result.errors == 0  # The error is caught and handled gracefully
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_vector_storage_integration(
        self, processor, sample_notion_content, mock_vector_repo
    ):
        """Test that vectors are properly stored in the repository."""
        await processor.process_notion_content([sample_notion_content])

        # Verify that upsert_vectors was called
        mock_vector_repo.upsert_vectors.assert_called_once()

        # Get the call arguments
        call_args = mock_vector_repo.upsert_vectors.call_args[0][0]
        assert len(call_args) == 1
        assert isinstance(call_args[0], VectorDocument)
