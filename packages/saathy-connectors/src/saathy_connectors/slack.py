"""Slack connector implementation."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.errors import SlackApiError

from saathy_core import ContentType, ProcessedContent, ProcessingStatus
from .base import BaseConnector

logger = logging.getLogger(__name__)


class SlackConnector(BaseConnector):
    """Connector for Slack integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("slack", config)
        self.bot_token = config.get("bot_token")
        self.app_token = config.get("app_token")
        self.signing_secret = config.get("signing_secret")
        self.default_channels = config.get("default_channels", [])
        self._web_client: Optional[AsyncWebClient] = None
        self._socket_client: Optional[SocketModeClient] = None
        self._event_handlers = {}
    
    async def validate_config(self) -> bool:
        """Validate Slack configuration."""
        if not self.bot_token:
            self.logger.error("Slack bot token not provided")
            return False
        
        if not self.app_token:
            self.logger.error("Slack app token not provided")
            return False
        
        if not self.signing_secret:
            self.logger.error("Slack signing secret not provided")
            return False
        
        return True
    
    async def _start_connector(self) -> None:
        """Start the Slack connector."""
        # Initialize Slack clients
        self._web_client = AsyncWebClient(token=self.bot_token)
        self._socket_client = SocketModeClient(
            app_token=self.app_token,
            web_client=self._web_client
        )
        
        # Register event handlers
        self._register_event_handlers()
        
        # Test connection
        try:
            response = await self._web_client.auth_test()
            self.logger.info(f"Connected to Slack as {response['user']}")
            
            # Start socket mode client
            await self._socket_client.connect()
            
            # Join default channels
            for channel in self.default_channels:
                try:
                    await self._web_client.conversations_join(channel=channel)
                    self.logger.info(f"Joined channel: {channel}")
                except SlackApiError as e:
                    if e.response["error"] != "already_in_channel":
                        self.logger.error(f"Failed to join channel {channel}: {e}")
                        
        except SlackApiError as e:
            raise ValueError(f"Failed to connect to Slack: {e}")
    
    async def _stop_connector(self) -> None:
        """Stop the Slack connector."""
        if self._socket_client:
            await self._socket_client.disconnect()
            self._socket_client = None
        
        self._web_client = None
    
    def _register_event_handlers(self) -> None:
        """Register Socket Mode event handlers."""
        if not self._socket_client:
            return
        
        # Message events
        @self._socket_client.socket_mode_request_listeners.append
        async def process_socket_mode_request(client, req):
            """Process Socket Mode requests."""
            if req.type == "events_api":
                # Handle Events API events
                await self._handle_event(req.payload)
                
            elif req.type == "slash_commands":
                # Handle slash commands
                await self._handle_slash_command(req.payload)
                
            elif req.type == "interactive":
                # Handle interactive components
                await self._handle_interactive(req.payload)
            
            # Acknowledge the request
            response = await client.send_socket_mode_response(
                socket_mode_request=req
            )
    
    async def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """Handle Events API events."""
        event = event_data.get("event", {})
        event_type = event.get("type")
        
        if event_type == "message":
            await self._process_message_event(event)
        elif event_type == "app_mention":
            await self._process_mention_event(event)
        elif event_type == "channel_joined":
            await self._process_channel_joined(event)
    
    async def _handle_slash_command(self, command_data: Dict[str, Any]) -> None:
        """Handle slash commands."""
        command = command_data.get("command")
        text = command_data.get("text", "")
        user_id = command_data.get("user_id")
        channel_id = command_data.get("channel_id")
        
        # Process the command
        response_text = f"Received command: {command} {text}"
        
        # Send response
        if self._web_client:
            await self._web_client.chat_postMessage(
                channel=channel_id,
                text=response_text,
                user=user_id
            )
    
    async def _handle_interactive(self, interaction_data: Dict[str, Any]) -> None:
        """Handle interactive components."""
        # Process button clicks, select menus, etc.
        pass
    
    async def _process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Process Slack event."""
        event_type = event_data.get("type")
        
        if event_type == "message":
            return await self._process_message_event(event_data)
        elif event_type == "app_mention":
            return await self._process_mention_event(event_data)
        elif event_type == "url_verification":
            # This is handled in the webhook endpoint
            return []
        
        self.logger.warning(f"Unsupported Slack event type: {event_type}")
        return []
    
    async def _process_message_event(self, event: Dict[str, Any]) -> List[ProcessedContent]:
        """Process message event."""
        # Skip bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return []
        
        content = ProcessedContent(
            content_type=ContentType.MESSAGE,
            title=f"Slack message in {event.get('channel', 'unknown')}",
            content=event.get("text", ""),
            source=f"slack:{event.get('team', 'unknown')}",
            source_id=event.get("client_msg_id", event.get("ts", "")),
            metadata={
                "event_type": "message",
                "channel": event.get("channel"),
                "user": event.get("user"),
                "ts": event.get("ts"),
                "thread_ts": event.get("thread_ts"),
                "team": event.get("team"),
            },
            timestamp=datetime.fromtimestamp(float(event.get("ts", 0))),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        return [content]
    
    async def _process_mention_event(self, event: Dict[str, Any]) -> List[ProcessedContent]:
        """Process app mention event."""
        content = ProcessedContent(
            content_type=ContentType.MESSAGE,
            title=f"Mentioned in Slack",
            content=event.get("text", ""),
            source=f"slack:{event.get('team', 'unknown')}",
            source_id=event.get("client_msg_id", event.get("ts", "")),
            metadata={
                "event_type": "app_mention",
                "channel": event.get("channel"),
                "user": event.get("user"),
                "ts": event.get("ts"),
                "thread_ts": event.get("thread_ts"),
                "team": event.get("team"),
            },
            timestamp=datetime.fromtimestamp(float(event.get("ts", 0))),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        return [content]
    
    async def _process_channel_joined(self, event: Dict[str, Any]) -> List[ProcessedContent]:
        """Process channel joined event."""
        channel = event.get("channel", "")
        self.logger.info(f"Joined channel: {channel}")
        return []
    
    async def list_channels(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """List available Slack channels."""
        if not self._web_client:
            raise RuntimeError("Slack client not initialized")
        
        channels = []
        
        try:
            # Get public channels
            response = await self._web_client.conversations_list(
                types="public_channel",
                exclude_archived=True
            )
            
            for channel in response.get("channels", []):
                channels.append({
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_member": channel.get("is_member", False),
                    "is_private": False,
                    "num_members": channel.get("num_members", 0),
                })
            
            # Get private channels if requested
            if include_private:
                response = await self._web_client.conversations_list(
                    types="private_channel",
                    exclude_archived=True
                )
                
                for channel in response.get("channels", []):
                    channels.append({
                        "id": channel["id"],
                        "name": channel["name"],
                        "is_member": channel.get("is_member", False),
                        "is_private": True,
                        "num_members": channel.get("num_members", 0),
                    })
            
        except SlackApiError as e:
            self.logger.error(f"Failed to list channels: {e}")
            raise
        
        return channels
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a message to Slack."""
        if not self._web_client:
            raise RuntimeError("Slack client not initialized")
        
        try:
            response = await self._web_client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                blocks=blocks
            )
            return response.data
        except SlackApiError as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about a Slack user."""
        if not self._web_client:
            raise RuntimeError("Slack client not initialized")
        
        try:
            response = await self._web_client.users_info(user=user_id)
            return response.get("user", {})
        except SlackApiError as e:
            self.logger.error(f"Failed to get user info: {e}")
            raise