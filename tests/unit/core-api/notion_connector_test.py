"""Tests for Notion connector functionality."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from saathy.connectors.base import ConnectorStatus, ContentType, ProcessedContent
from saathy.connectors.notion_connector import NotionConnector
from saathy.connectors.notion_content_extractor import NotionContentExtractor


class TestNotionConnector:
    """Test Notion connector functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for Notion connector."""
        return {
            "token": "test_token",
            "databases": ["db1", "db2"],
            "pages": ["page1", "page2"],
            "poll_interval": 300,
        }

    @pytest.fixture
    def notion_connector(self, mock_config):
        """Create Notion connector instance."""
        return NotionConnector(mock_config)

    @pytest.mark.asyncio
    async def test_connector_initialization(self, notion_connector):
        """Test connector initialization."""
        assert notion_connector.name == "notion"
        assert notion_connector.token == "test_token"
        assert notion_connector.databases == ["db1", "db2"]
        assert notion_connector.pages == ["page1", "page2"]
        assert notion_connector.poll_interval == 300
        assert notion_connector.status == ConnectorStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_connector_start_without_token(self):
        """Test connector start without token."""
        connector = NotionConnector({"token": None})
        await connector.start()
        assert connector.status == ConnectorStatus.ERROR

    @pytest.mark.asyncio
    async def test_connector_start_success(self, notion_connector):
        """Test successful connector start."""
        with patch(
            "saathy.connectors.notion_connector.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.users.list.return_value = {"results": []}

            await notion_connector.start()

            assert notion_connector.status == ConnectorStatus.ACTIVE
            assert notion_connector._running is True
            mock_client_class.assert_called_once_with(auth="test_token")

    @pytest.mark.asyncio
    async def test_connector_stop(self, notion_connector):
        """Test connector stop."""
        notion_connector._running = True
        notion_connector.client = AsyncMock()

        await notion_connector.stop()

        assert notion_connector._running is False
        assert notion_connector.status == ConnectorStatus.INACTIVE
        assert notion_connector.client is None

    @pytest.mark.asyncio
    async def test_extract_title(self, notion_connector):
        """Test title extraction from Notion title array."""
        title_array = [
            {"plain_text": "Hello"},
            {"plain_text": " "},
            {"plain_text": "World"},
        ]
        result = notion_connector._extract_title(title_array)
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_extract_title_empty(self, notion_connector):
        """Test title extraction from empty array."""
        result = notion_connector._extract_title([])
        assert result == "Untitled"

    @pytest.mark.asyncio
    async def test_process_event(self, notion_connector):
        """Test event processing."""
        with patch.object(notion_connector, "content_extractor") as mock_extractor:
            mock_extractor.extract_page_content = AsyncMock(
                return_value=[
                    ProcessedContent(
                        id="test_id",
                        content="test content",
                        content_type=ContentType.TEXT,
                        source="notion_page",
                        metadata={},
                        timestamp=datetime.now(timezone.utc),
                        raw_data={},
                    )
                ]
            )

            event_data = {"type": "page", "id": "test_page_id"}
            result = await notion_connector.process_event(event_data)

            assert len(result) == 1
            assert result[0].id == "test_id"
            assert result[0].content == "test content"


class TestNotionContentExtractor:
    """Test Notion content extractor functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock Notion client."""
        return AsyncMock()

    @pytest.fixture
    def extractor(self, mock_client):
        """Create content extractor instance."""
        return NotionContentExtractor(mock_client)

    @pytest.mark.asyncio
    async def test_extract_rich_text(self, extractor):
        """Test rich text extraction."""
        rich_text_array = [
            {"plain_text": "Hello"},
            {"plain_text": " "},
            {"plain_text": "World"},
        ]
        result = extractor._extract_rich_text(rich_text_array)
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_extract_rich_text_empty(self, extractor):
        """Test rich text extraction from empty array."""
        result = extractor._extract_rich_text([])
        assert result == ""

    def test_extract_title(self, extractor):
        """Test title extraction."""
        title_array = [
            {"plain_text": "Test"},
            {"plain_text": " "},
            {"plain_text": "Title"},
        ]
        result = extractor._extract_title(title_array)
        assert result == "Test Title"

    def test_extract_title_empty(self, extractor):
        """Test title extraction from empty array."""
        result = extractor._extract_title([])
        assert result == "Untitled"

    def test_get_content_type_for_block(self, extractor):
        """Test content type determination for blocks."""
        assert extractor._get_content_type_for_block("code") == ContentType.CODE
        assert (
            extractor._get_content_type_for_block("paragraph") == ContentType.MARKDOWN
        )
        assert (
            extractor._get_content_type_for_block("heading_1") == ContentType.MARKDOWN
        )
        assert (
            extractor._get_content_type_for_block("bulleted_list_item")
            == ContentType.TEXT
        )

    def test_extract_block_text_paragraph(self, extractor):
        """Test paragraph block text extraction."""
        block = {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "This is a paragraph"}]},
        }
        result = extractor._extract_block_text(block)
        assert result == "This is a paragraph"

    def test_extract_block_text_heading(self, extractor):
        """Test heading block text extraction."""
        block = {
            "type": "heading_1",
            "heading_1": {"rich_text": [{"plain_text": "This is a heading"}]},
        }
        result = extractor._extract_block_text(block)
        assert result == "# This is a heading"

    def test_extract_block_text_code(self, extractor):
        """Test code block text extraction."""
        block = {
            "type": "code",
            "code": {
                "language": "python",
                "rich_text": [{"plain_text": "print('Hello World')"}],
            },
        }
        result = extractor._extract_block_text(block)
        assert result == "```python\nprint('Hello World')\n```"

    def test_extract_block_text_todo(self, extractor):
        """Test todo block text extraction."""
        block = {
            "type": "to_do",
            "to_do": {"checked": True, "rich_text": [{"plain_text": "Completed task"}]},
        }
        result = extractor._extract_block_text(block)
        assert result == "☑ Completed task"

    @pytest.mark.asyncio
    async def test_extract_page_content(self, extractor):
        """Test page content extraction."""
        page_data = {
            "id": "test_page_id",
            "properties": {"title": {"title": [{"plain_text": "Test Page"}]}},
            "url": "https://notion.so/test",
            "created_time": "2023-01-01T00:00:00Z",
            "last_edited_time": "2023-01-01T00:00:00Z",
            "archived": False,
        }

        # Mock blocks response
        extractor.client.blocks.children.list.return_value = {
            "results": [],
            "has_more": False,
        }

        result = await extractor.extract_page_content(page_data)

        assert len(result) == 1
        assert result[0].id == "page_test_page_id"
        assert result[0].content_type == ContentType.TEXT
        assert result[0].source == "notion_page"
        assert result[0].metadata["page_id"] == "test_page_id"
        assert result[0].metadata["page_title"] == "Test Page"
