"""Content processing pipeline for connectors."""

import logging
import time
from typing import Any

from saathy.connectors.base import ProcessedContent
from saathy.embedding.service import EmbeddingService
from saathy.vector.models import VectorDocument
from saathy.vector.repository import VectorRepository

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Processes content items and stores them in the vector database."""

    def __init__(
        self, embedding_service: EmbeddingService, vector_repo: VectorRepository
    ):
        """Initialize the content processor."""
        self.embedding_service = embedding_service
        self.vector_repo = vector_repo

    async def process_and_store(
        self, content_items: list[ProcessedContent]
    ) -> dict[str, Any]:
        """Process content items and store in vector database."""
        if not content_items:
            return {
                "total_items": 0,
                "processed_items": 0,
                "failed_items": 0,
                "processing_time": 0.0,
                "errors": [],
            }

        start_time = time.time()
        total_items = len(content_items)
        processed_items = 0
        failed_items = 0
        errors = []

        logger.info(f"Starting to process {total_items} content items")

        # Convert ProcessedContent to VectorDocument
        vector_documents = []

        for content_item in content_items:
            try:
                # Generate embedding based on content type
                if content_item.content_type.value == "code":
                    embedding_result = await self.embedding_service.embed_code(
                        code=content_item.content,
                        metadata=content_item.metadata,
                    )
                else:
                    embedding_result = await self.embedding_service.embed_text(
                        text=content_item.content,
                        content_type=content_item.content_type.value,
                        metadata=content_item.metadata,
                    )

                # Create VectorDocument
                vector_doc = VectorDocument(
                    id=content_item.id,
                    content=content_item.content,
                    embedding=embedding_result.embeddings.tolist(),
                    metadata={
                        **content_item.metadata,
                        "source": content_item.source,
                        "content_type": content_item.content_type.value,
                        "embedding_model": embedding_result.model_name,
                        "processing_time": embedding_result.processing_time,
                        "quality_score": embedding_result.quality_score,
                    },
                    timestamp=content_item.timestamp,
                )

                vector_documents.append(vector_doc)
                processed_items += 1

                logger.debug(
                    f"Successfully processed content item {content_item.id} "
                    f"using model {embedding_result.model_name}"
                )

            except Exception as e:
                failed_items += 1
                error_msg = (
                    f"Failed to process content item {content_item.id}: {str(e)}"
                )
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

        # Store in vector repository
        if vector_documents:
            try:
                stored_count = await self.vector_repo.upsert_vectors(vector_documents)
                logger.info(
                    f"Stored {stored_count} documents in vector repository "
                    f"out of {len(vector_documents)} processed"
                )
            except Exception as e:
                error_msg = f"Failed to store documents in vector repository: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                # Don't count these as processed since they weren't stored
                processed_items -= len(vector_documents)
                failed_items += len(vector_documents)

        processing_time = time.time() - start_time

        result = {
            "total_items": total_items,
            "processed_items": processed_items,
            "failed_items": failed_items,
            "processing_time": processing_time,
            "errors": errors,
        }

        logger.info(
            f"Content processing completed: {processed_items}/{total_items} items processed "
            f"in {processing_time:.2f}s"
        )

        return result
