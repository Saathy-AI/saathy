"""Slack real-time event streaming using WebSocket Socket Mode."""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from slack_sdk.socket_mode.async_client import AsyncSocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from .event_manager import EventManager
from .models.events import EventType, SlackEvent

logger = logging.getLogger(__name__)


class SlackStreamProcessor:
    """Processes real-time Slack events via WebSocket connection."""

    def __init__(self, bot_token: str, app_token: str, event_manager: EventManager):
        """Initialize Slack streaming processor."""
        self.bot_token = bot_token
        self.app_token = app_token
        self.event_manager = event_manager

        # Initialize Slack clients
        self.web_client = AsyncWebClient(token=bot_token)
        self.socket_client = AsyncSocketModeClient(
            app_token=app_token, web_client=self.web_client
        )

        # Register event handlers
        self.socket_client.socket_mode_request_listeners.append(self.handle_events)

        # Cache for user and channel information
        self.user_cache: dict[str, dict[str, Any]] = {}
        self.channel_cache: dict[str, dict[str, Any]] = {}

        self.is_running = False

    async def start(self):
        """Start the WebSocket connection and event processing."""
        try:
            logger.info("Starting Slack WebSocket connection...")
            self.is_running = True

            # Pre-populate cache with channel and user info
            await self.populate_caches()

            # Connect to Slack
            await self.socket_client.connect()
            logger.info("Slack WebSocket connected successfully")

        except Exception as e:
            logger.error(f"Failed to start Slack streaming: {e}")
            raise

    async def stop(self):
        """Stop the WebSocket connection."""
        try:
            self.is_running = False
            await self.socket_client.disconnect()
            logger.info("Slack WebSocket disconnected")

        except Exception as e:
            logger.error(f"Error stopping Slack streaming: {e}")

    async def populate_caches(self):
        """Pre-populate user and channel caches to reduce API calls."""
        try:
            # Get user list
            users_response = await self.web_client.users_list()
            if users_response["ok"]:
                for user in users_response["members"]:
                    self.user_cache[user["id"]] = {
                        "name": user.get("name", "unknown"),
                        "real_name": user.get("real_name", ""),
                        "is_bot": user.get("is_bot", False),
                    }

            # Get channels list
            channels_response = await self.web_client.conversations_list(
                types="public_channel,private_channel"
            )
            if channels_response["ok"]:
                for channel in channels_response["channels"]:
                    self.channel_cache[channel["id"]] = {
                        "name": channel.get("name", "unknown"),
                        "is_private": channel.get("is_private", False),
                    }

            logger.info(
                f"Cached {len(self.user_cache)} users and {len(self.channel_cache)} channels"
            )

        except Exception as e:
            logger.error(f"Error populating caches: {e}")

    async def handle_events(
        self, client: AsyncSocketModeClient, req: SocketModeRequest
    ):
        """Main event handler for all Slack events."""
        try:
            if req.type == "events_api":
                event_data = req.payload.get("event", {})
                await self.process_event(event_data)
            elif req.type == "interactive":
                # Handle interactive components (buttons, select menus, etc.)
                await self.process_interactive_event(req.payload)
            elif req.type == "slash_commands":
                # Handle /saathy slash commands
                await self.process_slash_command(req.payload)

            # Always acknowledge the event
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)

        except Exception as e:
            logger.error(f"Error handling Slack event: {e}")
            # Still acknowledge to prevent retries
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)

    async def process_event(self, event_data: dict[str, Any]):
        """Process individual Slack events and convert to our format."""
        event_type = event_data.get("type")

        try:
            if event_type == "message":
                await self.handle_message_event(event_data)
            elif event_type == "reaction_added":
                await self.handle_reaction_event(event_data)
            elif event_type == "reaction_removed":
                await self.handle_reaction_removed_event(event_data)
            elif event_type == "channel_created":
                await self.handle_channel_event(event_data)
            # Add more event types as needed
            else:
                logger.debug(f"Ignoring Slack event type: {event_type}")

        except Exception as e:
            logger.error(f"Error processing Slack event {event_type}: {e}")

    async def handle_message_event(self, event_data: dict[str, Any]):
        """Process Slack message events."""
        # Skip bot messages, hidden messages, and message changes
        if (
            event_data.get("bot_id")
            or event_data.get("hidden")
            or event_data.get("subtype") in ["message_changed", "message_deleted"]
        ):
            return

        try:
            # Extract key information
            user_id = event_data.get("user", "unknown")
            channel_id = event_data.get("channel")
            message_text = event_data.get("text", "")
            timestamp_str = event_data.get("ts", "0")
            thread_ts = event_data.get("thread_ts")

            # Convert timestamp
            timestamp = datetime.fromtimestamp(float(timestamp_str))

            # Get channel info
            channel_info = self.channel_cache.get(channel_id)
            if not channel_info:
                # Fallback to API call if not cached
                try:
                    channel_response = await self.web_client.conversations_info(
                        channel=channel_id
                    )
                    if channel_response["ok"]:
                        channel_info = {
                            "name": channel_response["channel"].get("name", "unknown"),
                            "is_private": channel_response["channel"].get(
                                "is_private", False
                            ),
                        }
                        self.channel_cache[channel_id] = channel_info
                except Exception:
                    channel_info = {"name": "unknown", "is_private": False}

            channel_name = channel_info["name"]

            # Extract mentions and keywords
            mentioned_users = self.extract_mentions(message_text)
            keywords = self.extract_keywords(message_text)
            urgency_score = self.calculate_urgency(
                message_text, mentioned_users, channel_name
            )

            # Infer project context
            project_context = self.infer_project_context(channel_name, message_text)

            # Create our standardized event
            slack_event = SlackEvent(
                event_id=f"slack_{channel_id}_{timestamp_str.replace('.', '_')}",
                event_type=EventType.SLACK_MESSAGE,
                timestamp=timestamp,
                user_id=user_id,
                platform="slack",
                raw_data=event_data,
                mentioned_users=mentioned_users,
                keywords=keywords,
                project_context=project_context,
                urgency_score=urgency_score,
                channel_id=channel_id,
                channel_name=channel_name,
                message_text=message_text,
                thread_ts=thread_ts,
                is_thread_reply=bool(thread_ts and thread_ts != timestamp_str),
                message_ts=timestamp_str,
            )

            # Send to event manager for processing
            await self.event_manager.process_event(slack_event)

            logger.debug(f"Processed Slack message from {user_id} in #{channel_name}")

        except Exception as e:
            logger.error(f"Error processing Slack message: {e}")

    async def handle_reaction_event(self, event_data: dict[str, Any]):
        """Handle reaction added events."""
        try:
            user_id = event_data.get("user", "unknown")
            channel_id = event_data.get("item", {}).get("channel")
            reaction = event_data.get("reaction", "")
            item_ts = event_data.get("item", {}).get("ts", "0")
            event_ts = event_data.get("event_ts", "0")

            # Get channel info
            channel_info = self.channel_cache.get(channel_id, {"name": "unknown"})
            channel_name = channel_info["name"]

            # Convert timestamp
            timestamp = datetime.fromtimestamp(float(event_ts))

            # Calculate urgency (reactions to urgent messages are somewhat urgent)
            urgency_score = 0.1  # Base score for reactions
            if reaction in ["🚨", "⚠️", "🔥", "❗", "⏰"]:
                urgency_score = 0.3  # Higher for urgent reaction emojis
            elif reaction in ["✅", "👍", "🎉"]:
                urgency_score = 0.2  # Medium for approval reactions

            # Create reaction event
            slack_event = SlackEvent(
                event_id=f"slack_reaction_{channel_id}_{item_ts}_{reaction}_{user_id}",
                event_type=EventType.SLACK_REACTION,
                timestamp=timestamp,
                user_id=user_id,
                platform="slack",
                raw_data=event_data,
                mentioned_users=[],  # Reactions don't have mentions
                keywords=["reaction", reaction],
                project_context=self.infer_project_context(channel_name, ""),
                urgency_score=urgency_score,
                channel_id=channel_id,
                channel_name=channel_name,
                reactions=[reaction],
                thread_ts=None,
                is_thread_reply=False,
            )

            await self.event_manager.process_event(slack_event)

            logger.debug(
                f"Processed Slack reaction {reaction} from {user_id} in #{channel_name}"
            )

        except Exception as e:
            logger.error(f"Error processing Slack reaction: {e}")

    def extract_mentions(self, text: str) -> list[str]:
        """Extract @mentions from Slack message."""
        # Slack format: <@U1234567890> or <@U1234567890|username>
        mentions = re.findall(r"<@([UW][A-Z0-9]+)(?:\|[^>]+)?>", text)

        # Convert user IDs to usernames if possible
        usernames = []
        for user_id in mentions:
            user_info = self.user_cache.get(user_id)
            if user_info:
                usernames.append(user_info["name"])
            else:
                usernames.append(user_id)  # Fallback to ID

        return usernames

    def extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from message."""
        important_words = []
        text_lower = text.lower()

        # Technical keywords that indicate work activity
        tech_keywords = [
            "bug",
            "error",
            "deploy",
            "deployment",
            "release",
            "urgent",
            "fix",
            "issue",
            "pr",
            "pull request",
            "merge",
            "review",
            "test",
            "testing",
            "production",
            "staging",
            "api",
            "database",
            "server",
            "down",
            "outage",
            "incident",
            "meeting",
            "call",
            "sync",
            "standup",
            "demo",
            "presentation",
            "deadline",
            "due",
            "milestone",
            "launch",
            "ship",
            "rollout",
        ]

        for keyword in tech_keywords:
            if keyword in text_lower:
                important_words.append(keyword)

        # Look for GitHub references
        github_patterns = [
            r"github\.com/[\w\-\.]+/[\w\-\.]+",
            r"#\d+",  # Issue/PR numbers
            r"[A-Fa-f0-9]{7,40}",  # Commit hashes
        ]

        for pattern in github_patterns:
            if re.search(pattern, text):
                important_words.append("github")
                break

        # Look for Notion references
        if "notion.so" in text_lower or "notion" in text_lower:
            important_words.append("notion")

        return important_words

    def calculate_urgency(
        self, text: str, mentioned_users: list[str], channel_name: str
    ) -> float:
        """Calculate urgency score 0-1."""
        score = 0.0
        text_lower = text.lower()

        # Urgent keywords
        if any(
            word in text_lower
            for word in ["urgent", "asap", "emergency", "critical", "immediately"]
        ):
            score += 0.4

        # Production/incident keywords
        if any(
            word in text_lower
            for word in ["production", "prod", "outage", "down", "incident"]
        ):
            score += 0.3

        # Direct mentions increase urgency
        if mentioned_users:
            score += min(0.2, len(mentioned_users) * 0.1)

        # Question marks suggest need for response
        question_count = text.count("?")
        if question_count > 0:
            score += min(0.15, question_count * 0.05)

        # Time-sensitive words
        if any(
            word in text_lower for word in ["deadline", "today", "now", "quick", "fast"]
        ):
            score += 0.2

        # Channel-based urgency
        if any(
            word in channel_name.lower()
            for word in ["alert", "incident", "urgent", "critical"]
        ):
            score += 0.2

        # Exclamation marks
        exclamation_count = text.count("!")
        if exclamation_count > 0:
            score += min(0.1, exclamation_count * 0.03)

        return min(score, 1.0)

    def infer_project_context(
        self, channel_name: str, message_text: str
    ) -> Optional[str]:
        """Infer project context from channel name or message."""
        # Channel name often indicates project
        if channel_name and channel_name != "unknown":
            # Clean up channel names for project inference
            clean_name = channel_name.replace("-", " ").replace("_", " ")

            # Skip general channels
            if clean_name.lower() not in [
                "general",
                "random",
                "water cooler",
                "announcements",
            ]:
                return channel_name

        # Look for project mentions in message
        project_indicators = [
            r"project\s+(\w+)",
            r"repo\s+(\w+)",
            r"(\w+)\.git",
            r"github\.com/[\w\-\.]+/([\w\-\.]+)",
        ]

        for pattern in project_indicators:
            match = re.search(pattern, message_text.lower())
            if match:
                return match.group(1)

        return None

    async def handle_reaction_removed_event(self, event_data: dict[str, Any]):
        """Handle reaction removed events - usually less important."""
        # For now, we don't process reaction removals as they're less actionable
        logger.debug("Ignoring reaction_removed event")
        pass

    async def handle_channel_event(self, event_data: dict[str, Any]):
        """Handle channel creation events."""
        # Update our channel cache
        channel_id = event_data.get("channel", {}).get("id")
        channel_name = event_data.get("channel", {}).get("name", "unknown")

        if channel_id:
            self.channel_cache[channel_id] = {
                "name": channel_name,
                "is_private": event_data.get("channel", {}).get("is_private", False),
            }
            logger.debug(f"Added new channel to cache: #{channel_name}")

    async def process_interactive_event(self, payload: dict[str, Any]):
        """Process interactive events (buttons, select menus, etc.)."""
        # This could be used for Saathy-specific interactions
        logger.debug("Received interactive event - could be used for action responses")
        pass

    async def process_slash_command(self, payload: dict[str, Any]):
        """Process /saathy slash commands."""
        # This could be used for manual action requests
        command = payload.get("command", "")
        if command == "/saathy":
            logger.info("Received /saathy slash command")
            # Could trigger manual action generation or show status
        pass

    async def get_channel_members(self, channel_id: str) -> list[str]:
        """Get list of members in a channel."""
        try:
            response = await self.web_client.conversations_members(channel=channel_id)
            if response["ok"]:
                return response["members"]
            return []
        except Exception as e:
            logger.error(f"Error getting channel members: {e}")
            return []

    async def send_message(
        self, channel_id: str, text: str, thread_ts: Optional[str] = None
    ):
        """Send a message to a Slack channel (for future action responses)."""
        try:
            response = await self.web_client.chat_postMessage(
                channel=channel_id, text=text, thread_ts=thread_ts
            )
            return response["ok"]
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False

    def is_running_status(self) -> bool:
        """Check if the processor is running."""
        return self.is_running and self.socket_client.is_connected()
