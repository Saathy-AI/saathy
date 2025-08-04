#!/usr/bin/env python3
"""Demo script for the content processing pipeline."""

import asyncio
import logging
from datetime import datetime

from saathy.config import get_settings
from saathy.connectors.base import ContentType, ProcessedContent
from saathy.connectors.content_processor import ContentProcessor
from saathy.embedding.service import get_embedding_service
from saathy.vector.client import QdrantClientWrapper
from saathy.vector.repository import VectorRepository


async def demo_content_processing():
    """Demonstrate the content processing pipeline."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Initialize services
        logger.info("Initializing services...")
        settings = get_settings()

        # Initialize embedding service
        embedding_service = await get_embedding_service()
        logger.info("Embedding service initialized")

        # Initialize vector repository
        qdrant_url = str(settings.qdrant_url)
        if qdrant_url.startswith("http://"):
            qdrant_url = qdrant_url[7:]
        elif qdrant_url.startswith("https://"):
            qdrant_url = qdrant_url[8:]

        qdrant_url = qdrant_url.split("/")[0]
        host_port = qdrant_url.split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 6333

        qdrant_client = QdrantClientWrapper(
            host=host,
            port=port,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
            api_key=settings.qdrant_api_key_str,
        )
        vector_repo = VectorRepository(client=qdrant_client)
        logger.info("Vector repository initialized")

        # Initialize content processor
        content_processor = ContentProcessor(embedding_service, vector_repo)
        logger.info("Content processor initialized")

        # Create sample Slack messages
        sample_messages = [
            ProcessedContent(
                id="demo_message_1",
                content="Hey team! I just finished implementing the new authentication system. It includes OAuth2 support and JWT tokens. Let me know if you want to review the code.",
                content_type=ContentType.TEXT,
                source="slack",
                metadata={
                    "channel_id": "C1234567890",
                    "channel_name": "dev-team",
                    "user_id": "U1234567890",
                    "timestamp": str(datetime.now().timestamp()),
                    "is_thread_reply": False,
                },
                timestamp=datetime.now(),
                raw_data={
                    "text": "Hey team! I just finished implementing the new authentication system."
                },
            ),
            ProcessedContent(
                id="demo_message_2",
                content="Great work! Can you share the PR link? I'd like to take a look at the implementation details.",
                content_type=ContentType.TEXT,
                source="slack",
                metadata={
                    "channel_id": "C1234567890",
                    "channel_name": "dev-team",
                    "user_id": "U0987654321",
                    "timestamp": str(datetime.now().timestamp()),
                    "is_thread_reply": True,
                    "thread_ts": "1234567890.123",
                },
                timestamp=datetime.now(),
                raw_data={"text": "Great work! Can you share the PR link?"},
            ),
            ProcessedContent(
                id="demo_message_3",
                content="Hi",  # This should be skipped (too short)
                content_type=ContentType.TEXT,
                source="slack",
                metadata={
                    "channel_id": "C1234567890",
                    "channel_name": "dev-team",
                    "user_id": "U1111111111",
                    "timestamp": str(datetime.now().timestamp()),
                    "is_thread_reply": False,
                },
                timestamp=datetime.now(),
                raw_data={"text": "Hi"},
            ),
        ]

        # Process the messages
        logger.info(f"Processing {len(sample_messages)} messages...")
        result = await content_processor.process_and_store(sample_messages)

        # Display results
        logger.info("Processing completed!")
        logger.info(
            f"Results: {result['processed']} processed, {result['errors']} errors, {result['skipped']} skipped"
        )
        logger.info(f"Processing time: {result['processing_time']:.2f} seconds")

        # Show details for each item
        for item in result["items"]:
            if item["status"] == "success":
                logger.info(
                    f"✅ {item['id']}: Successfully processed with {item['embedding_dimensions']} dimensions"
                )
            elif item["status"] == "skipped":
                logger.info(
                    f"⏭️  {item['id']}: Skipped - {item.get('reason', 'unknown')}"
                )
            else:
                logger.info(f"❌ {item['id']}: Error - {item.get('error', 'unknown')}")

        logger.info("Demo completed successfully!")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(demo_content_processing())
