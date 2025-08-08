"""Slack connector using Socket Mode for real-time message processing."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from slack_sdk.web.async_client import AsyncWebClient

from .base import BaseConnector, ConnectorStatus, ContentType, ProcessedContent
from .content_processor import ContentProcessor


class SlackConnector(BaseConnector):
    """Slack connector using Socket Mode for real-time event processing."""

    def __init__(self, config: dict[str, Any]):
        super().__init__("slack", config)
        self.bot_token = config.get("bot_token")
        self.app_token = config.get("app_token")
        self.channels = config.get("channels", [])

        self.web_client: Optional[AsyncWebClient] = None
        self.content_processor: Optional[ContentProcessor] = None
        self._running = False

    async def start(self) -> None:
        """Start Slack connector."""
        if not self.bot_token:
            self.logger.error("Missing Slack bot token")
            self.status = ConnectorStatus.ERROR
            return

        try:
            self.logger.info("Starting Slack connector...")

            # Initialize web client
            self.web_client = AsyncWebClient(token=self.bot_token)

            # Test connection
            try:
                auth_test = await self.web_client.auth_test()
                if not auth_test["ok"]:
                    raise Exception("Failed to authenticate with Slack")
                self.logger.info(
                    f"Connected to Slack workspace: {auth_test.get('team', 'Unknown')}"
                )
            except Exception as e:
                self.logger.error(f"Failed to authenticate with Slack: {e}")
                raise

            self.status = ConnectorStatus.ACTIVE
            self._running = True
            self.logger.info("Slack connector started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start Slack connector: {e}")
            self.status = ConnectorStatus.ERROR
            raise

    def set_content_processor(self, processor: ContentProcessor) -> None:
        """Set the content processor for this connector."""
        self.content_processor = processor
        self.logger.info("Content processor set for Slack connector")

    async def stop(self) -> None:
        """Stop Slack connector."""
        self._running = False
        self.status = ConnectorStatus.INACTIVE

        if self.web_client:
            # AsyncWebClient doesn't have a close method, just set to None
            self.web_client = None

        self.logger.info("Slack connector stopped")

    async def process_event(self, event_data: dict[str, Any]) -> list[ProcessedContent]:
        """Convert Slack event to ProcessedContent objects."""
        processed_items = []

        try:
            event_type = event_data.get("type", "")

            if event_type == "message":
                content = await self._extract_message_content(event_data)
                if content:
                    processed_items.append(content)

        except Exception as e:
            self.logger.error(f"Error processing event: {e}")

        return processed_items

    async def process_message_event(self, event: dict[str, Any]) -> None:
        """Process message events and store in vector database."""
        try:
            # Skip bot messages and message updates
            if event.get("subtype") or event.get("bot_id"):
                return

            channel = event.get("channel")
            if self.channels and channel not in self.channels:
                return

            # Process the message into ProcessedContent
            processed_content = await self.process_event(event)

            # If we have a content processor, process and store
            if self.content_processor and processed_content:
                result = await self.content_processor.process_and_store(
                    processed_content
                )
                self.logger.info(
                    f"Processed {result['processed']} messages, {result['errors']} errors"
                )
            else:
                self.logger.warning("No content processor configured")

        except Exception as e:
            self.logger.error(f"Error processing message event: {e}")

    async def _extract_message_content(
        self, message_data: dict[str, Any]
    ) -> Optional[ProcessedContent]:
        """Extract content from Slack message."""
        try:
            text = message_data.get("text", "")
            if not text.strip():
                return None

            # Get additional context
            channel_id = message_data.get("channel")
            user_id = message_data.get("user")
            ts = message_data.get("ts")
            thread_ts = message_data.get("thread_ts")

            # Fetch channel info
            channel_info = {}
            if self.web_client and channel_id:
                try:
                    channel_response = await self.web_client.conversations_info(
                        channel=channel_id
                    )
                    if channel_response and channel_response.get("ok"):
                        channel_info = channel_response.get("channel", {})
                except Exception as e:
                    self.logger.warning(f"Failed to fetch channel info: {e}")

            # Create ProcessedContent
            content_id = f"slack_{channel_id}_{ts}"

            metadata = {
                "source": "slack",
                "channel_id": channel_id,
                "channel_name": channel_info.get("name", "unknown"),
                "user_id": user_id,
                "timestamp": ts,
                "thread_ts": thread_ts,
                "is_thread_reply": bool(thread_ts and thread_ts != ts),
                "has_files": bool(message_data.get("files")),
                "has_attachments": bool(message_data.get("attachments")),
            }

            # Handle timestamp conversion safely
            timestamp = datetime.now(timezone.utc)
            if ts:
                try:
                    timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid timestamp format: {ts}")

            return ProcessedContent(
                id=content_id,
                content=text,
                content_type=ContentType.TEXT,
                source="slack",
                metadata=metadata,
                timestamp=timestamp,
                raw_data=message_data,
            )

        except Exception as e:
            self.logger.error(f"Error extracting message content: {e}")
            return None

    async def get_channel_messages(
        self, channel_id: str, limit: int = 100
    ) -> list[ProcessedContent]:
        """Get recent messages from a channel."""
        if not self.web_client:
            self.logger.error("Web client not initialized")
            return []

        try:
            response = await self.web_client.conversations_history(
                channel=channel_id, limit=limit
            )

            if not response["ok"]:
                self.logger.error(
                    f"Failed to get channel history: {response.get('error')}"
                )
                return []

            messages = []
            response_messages = response.get("messages", [])
            for message in response_messages:
                content = await self._extract_message_content(message)
                if content:
                    messages.append(content)

            return messages

        except Exception as e:
            self.logger.error(f"Error getting channel messages: {e}")
            return []

    async def get_user_info(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get user information."""
        if not self.web_client:
            return None

        try:
            response = await self.web_client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
            return None
        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return None

    async def fetch_recent_messages(
        self, channel_id: str, minutes: int = 15
    ) -> list[ProcessedContent]:
        """Fetch messages from the last N minutes from a channel."""
        if not self.web_client:
            self.logger.error("Web client not initialized")
            return []

        try:
            # Calculate the timestamp for N minutes ago
            oldest_timestamp = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            oldest_ts = str(oldest_timestamp.timestamp())

            response = await self.web_client.conversations_history(
                channel=channel_id,
                oldest=oldest_ts,
                limit=100,  # Slack API max limit per request
            )

            if not response["ok"]:
                self.logger.error(
                    f"Failed to get channel history: {response.get('error')}"
                )
                return []

            messages = []
            response_messages = response.get("messages", [])

            # Filter out messages we've already processed
            for message in response_messages:
                # Skip bot messages, edited messages, and other subtypes
                if message.get("subtype") or message.get("bot_id"):
                    continue

                content = await self._extract_message_content(message)
                if content:
                    messages.append(content)

            self.logger.info(
                f"Fetched {len(messages)} recent messages from channel {channel_id}"
            )
            return messages

        except Exception as e:
            self.logger.error(f"Error fetching recent messages: {e}")
            return []
