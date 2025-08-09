#!/usr/bin/env python3
"""Demo script for Notion connector functionality."""

import asyncio
import logging
import os

from src.saathy.connectors.base import ConnectorStatus
from src.saathy.connectors.notion_connector import NotionConnector
from src.saathy.connectors.notion_content_extractor import NotionContentExtractor


async def demo_notion_connector():
    """Demonstrate Notion connector functionality."""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Get Notion token from environment
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        logger.error("NOTION_TOKEN environment variable not set")
        logger.info("Please set NOTION_TOKEN with your Notion integration token")
        return

    # Configuration for the connector
    config = {
        "token": notion_token,
        "databases": os.getenv("NOTION_DATABASES", "").split(",")
        if os.getenv("NOTION_DATABASES")
        else [],
        "pages": os.getenv("NOTION_PAGES", "").split(",")
        if os.getenv("NOTION_PAGES")
        else [],
        "poll_interval": int(os.getenv("NOTION_POLL_INTERVAL", "300")),
    }

    logger.info("Initializing Notion connector...")
    logger.info(f"Configuration: {config}")

    # Create and start the connector
    connector = NotionConnector(config)

    try:
        # Start the connector
        await connector.start()

        if connector.status == ConnectorStatus.ACTIVE:
            logger.info("✅ Notion connector started successfully!")

            # Get connector status
            status = connector.get_status()
            logger.info(f"Connector status: {status}")

            # Show what's being monitored
            logger.info(f"Monitoring databases: {connector.databases}")
            logger.info(f"Monitoring pages: {connector.pages}")
            logger.info(f"Poll interval: {connector.poll_interval} seconds")

            # Keep running for a bit to see polling in action
            logger.info("Connector is running. Press Ctrl+C to stop...")
            await asyncio.sleep(30)  # Run for 30 seconds

        else:
            logger.error(f"❌ Failed to start connector. Status: {connector.status}")

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping connector...")
    except Exception as e:
        logger.error(f"Error during connector operation: {e}")
    finally:
        # Stop the connector
        await connector.stop()
        logger.info("Connector stopped.")


async def demo_content_extraction():
    """Demonstrate content extraction functionality."""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # This would require a real Notion token and page ID
    notion_token = os.getenv("NOTION_TOKEN")
    page_id = os.getenv("NOTION_DEMO_PAGE_ID")

    if not notion_token or not page_id:
        logger.info(
            "Skipping content extraction demo - requires NOTION_TOKEN and NOTION_DEMO_PAGE_ID"
        )
        return

    logger.info("Demonstrating content extraction...")

    try:
        from notion_client import AsyncClient

        # Create client and extractor
        client = AsyncClient(auth=notion_token)
        extractor = NotionContentExtractor(client)

        # Get page data
        page_data = await client.pages.retrieve(page_id)

        # Extract content
        processed_content = await extractor.extract_page_content(page_data)

        logger.info(f"Extracted {len(processed_content)} content items:")
        for i, content in enumerate(processed_content):
            logger.info(f"  {i+1}. {content.id} ({content.content_type})")
            logger.info(f"     Content preview: {content.content[:100]}...")
            logger.info(f"     Metadata: {content.metadata}")

    except Exception as e:
        logger.error(f"Error during content extraction: {e}")


async def main():
    """Main demo function."""
    print("🚀 Notion Connector Demo")
    print("=" * 50)

    # Demo 1: Basic connector functionality
    print("\n1. Testing Notion Connector...")
    await demo_notion_connector()

    # Demo 2: Content extraction
    print("\n2. Testing Content Extraction...")
    await demo_content_extraction()

    print("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
