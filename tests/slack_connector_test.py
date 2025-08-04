"""Tests for Slack connector functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from saathy.connectors.base import ConnectorStatus, ContentType
from saathy.connectors.slack_connector import SlackConnector


@pytest.fixture
def slack_config():
    """Sample Slack configuration for testing."""
    return {
        "bot_token": "xoxb-test-bot-token",
        "app_token": "xapp-test-app-token",
        "channels": ["C1234567890", "C0987654321"],
    }


@pytest.fixture
def slack_connector(slack_config):
    """Create a Slack connector instance for testing."""
    return SlackConnector(slack_config)


class TestSlackConnector:
    """Test cases for SlackConnector."""

    def test_initialization(self, slack_connector, slack_config):
        """Test connector initialization."""
        assert slack_connector.name == "slack"
        assert slack_connector.bot_token == slack_config["bot_token"]
        assert slack_connector.channels == slack_config["channels"]
        assert slack_connector.status == ConnectorStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_start_success(self, slack_connector):
        """Test successful connector start."""
        # Create a mock web client instance
        mock_web_instance = AsyncMock()
        mock_web_instance.auth_test = AsyncMock(
            return_value={"ok": True, "team": "Test Team"}
        )

        # Patch the AsyncWebClient constructor to return our mock
        with patch(
            "saathy.connectors.slack_connector.AsyncWebClient",
            return_value=mock_web_instance,
        ):
            # Start the connector
            await slack_connector.start()

            # Verify status and client initialization
            assert slack_connector.status == ConnectorStatus.ACTIVE
            assert slack_connector.web_client is not None
            assert slack_connector._running is True

    @pytest.mark.asyncio
    async def test_start_missing_tokens(self):
        """Test start with missing tokens."""
        connector = SlackConnector({})
        await connector.start()
        assert connector.status == ConnectorStatus.ERROR

    @pytest.mark.asyncio
    async def test_stop(self, slack_connector):
        """Test connector stop."""
        # Mock the web client
        slack_connector.web_client = AsyncMock()
        slack_connector._running = True
        slack_connector.status = ConnectorStatus.ACTIVE

        await slack_connector.stop()

        assert slack_connector.status == ConnectorStatus.INACTIVE
        assert slack_connector._running is False
        assert slack_connector.web_client is None

    @pytest.mark.asyncio
    async def test_get_channel_messages(self, slack_connector):
        """Test getting channel messages."""
        # Create a mock web client with all necessary methods
        mock_web_client = AsyncMock()
        mock_web_client.conversations_history = AsyncMock(
            return_value={
                "ok": True,
                "messages": [
                    {
                        "type": "message",
                        "text": "Test message",
                        "channel": "C1234567890",
                        "user": "U1234567890",
                        "ts": "1234567890.123456",
                    }
                ],
            }
        )
        mock_web_client.conversations_info = AsyncMock(
            return_value={"ok": True, "channel": {"name": "test-channel"}}
        )

        # Set the mock web client
        slack_connector.web_client = mock_web_client

        messages = await slack_connector.get_channel_messages("C1234567890")
        assert len(messages) == 1
        assert messages[0].content == "Test message"

    @pytest.mark.asyncio
    async def test_process_event_message(self, slack_connector):
        """Test processing message events into ProcessedContent."""
        message_data = {
            "type": "message",
            "text": "Test message content",
            "channel": "C1234567890",
            "user": "U1234567890",
            "ts": "1234567890.123456",
        }

        with patch.object(slack_connector, "_extract_message_content") as mock_extract:
            mock_content = MagicMock()
            mock_extract.return_value = mock_content

            result = await slack_connector.process_event(message_data)

            assert len(result) == 1
            assert result[0] == mock_content
            mock_extract.assert_called_once_with(message_data)

    @pytest.mark.asyncio
    async def test_extract_message_content(self, slack_connector):
        """Test extracting content from Slack messages."""
        message_data = {
            "text": "Test message content",
            "channel": "C1234567890",
            "user": "U1234567890",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }

        # Set up web_client as AsyncMock
        slack_connector.web_client = AsyncMock()
        mock_response = {"ok": True, "channel": {"name": "test-channel"}}
        slack_connector.web_client.conversations_info = AsyncMock(
            return_value=mock_response
        )

        result = await slack_connector._extract_message_content(message_data)

        assert result is not None
        assert result.content == "Test message content"
        assert result.content_type == ContentType.TEXT
        assert result.source == "slack"
        assert result.metadata["channel_id"] == "C1234567890"
        assert result.metadata["channel_name"] == "test-channel"
        assert result.metadata["user_id"] == "U1234567890"

    def test_get_status(self, slack_connector):
        """Test getting connector status."""
        status = slack_connector.get_status()

        assert status["name"] == "slack"
        assert status["status"] == ConnectorStatus.INACTIVE.value
        assert "bot_token" not in status["config"]
        assert "channels" in status["config"]

    @pytest.mark.asyncio
    async def test_health_check(self, slack_connector):
        """Test health check functionality."""
        # Test when inactive
        assert not await slack_connector.health_check()

        # Test when active
        slack_connector.status = ConnectorStatus.ACTIVE
        assert await slack_connector.health_check()

    @pytest.mark.asyncio
    async def test_get_user_info(self, slack_connector):
        """Test getting user information."""
        slack_connector.web_client = AsyncMock()
        mock_response = {
            "ok": True,
            "user": {"id": "U1234567890", "name": "testuser", "real_name": "Test User"},
        }
        slack_connector.web_client.users_info = AsyncMock(return_value=mock_response)

        user_info = await slack_connector.get_user_info("U1234567890")
        assert user_info is not None
        assert user_info["id"] == "U1234567890"
        assert user_info["name"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, slack_connector):
        """Test getting user information when it fails."""
        slack_connector.web_client = AsyncMock()
        mock_response = {"ok": False, "error": "user_not_found"}
        slack_connector.web_client.users_info = AsyncMock(return_value=mock_response)

        user_info = await slack_connector.get_user_info("U1234567890")
        assert user_info is None

    @pytest.mark.asyncio
    async def test_get_user_info_no_web_client(self, slack_connector):
        """Test getting user information when web_client is None."""
        slack_connector.web_client = None
        user_info = await slack_connector.get_user_info("U1234567890")
        assert user_info is None

    @pytest.mark.asyncio
    async def test_get_channel_messages_no_web_client(self, slack_connector):
        """Test getting channel messages when web_client is None."""
        slack_connector.web_client = None
        messages = await slack_connector.get_channel_messages("C1234567890")
        assert messages == []

    @pytest.mark.asyncio
    async def test_extract_message_content_invalid_timestamp(self, slack_connector):
        """Test extracting content with invalid timestamp."""
        message_data = {
            "text": "Test message content",
            "channel": "C1234567890",
            "user": "U1234567890",
            "ts": "invalid_timestamp",
            "thread_ts": None,
        }

        # Set up web_client as AsyncMock
        slack_connector.web_client = AsyncMock()
        mock_response = {"ok": True, "channel": {"name": "test-channel"}}
        slack_connector.web_client.conversations_info = AsyncMock(
            return_value=mock_response
        )

        result = await slack_connector._extract_message_content(message_data)

        assert result is not None
        assert result.content == "Test message content"
        # Should use current timestamp when invalid timestamp is provided
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_extract_message_content_empty_text(self, slack_connector):
        """Test extracting content with empty text."""
        message_data = {
            "text": "",
            "channel": "C1234567890",
            "user": "U1234567890",
            "ts": "1234567890.123456",
            "thread_ts": None,
        }

        result = await slack_connector._extract_message_content(message_data)
        assert result is None
