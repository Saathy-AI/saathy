#!/usr/bin/env python3
"""Demo script for Slack connector integration with Saathy."""

import asyncio
import logging
from typing import Any, dict

from src.saathy.config import settings
from src.saathy.connectors.slack_connector import SlackConnector


async def main():
    """Main demo function."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Check if Slack tokens are configured
    if not settings.slack_bot_token_str:
        logger.error("Slack bot token not configured. Please set SLACK_BOT_TOKEN")
        return

    # Parse channels from config
    channels = []
    if settings.slack_channels:
        channels = [
            ch.strip() for ch in settings.slack_channels.split(",") if ch.strip()
        ]

    # Create Slack connector configuration
    config: dict[str, Any] = {
        "bot_token": settings.slack_bot_token_str,
        "channels": channels,
    }

    logger.info(f"Starting Slack connector with {len(channels)} channels: {channels}")

    # Create and start the connector
    connector = SlackConnector(config)

    try:
        await connector.start()
        logger.info("Slack connector started successfully")

        # Demonstrate getting messages from configured channels
        if channels:
            logger.info("Getting recent messages from configured channels...")
            for channel in channels:
                messages = await connector.get_channel_messages(channel, limit=10)
                logger.info(f"Found {len(messages)} messages in channel {channel}")
                for msg in messages[:3]:  # Show first 3 messages
                    logger.info(f"  - {msg.content[:50]}...")

        # Keep the connector running
        logger.info("Press Ctrl+C to stop the connector")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping connector...")
    except Exception as e:
        logger.error(f"Error running Slack connector: {e}")
    finally:
        await connector.stop()
        logger.info("Slack connector stopped")


if __name__ == "__main__":
    asyncio.run(main())
