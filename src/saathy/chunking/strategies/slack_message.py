"""Slack message chunking strategy."""

import re
from typing import Optional

from ..core.models import Chunk, ChunkMetadata
from .base import BaseChunkingStrategy


class SlackMessageChunker(BaseChunkingStrategy):
    """Slack conversation chunking."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message_patterns = [
            r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",  # Timestamps
            r"<@[A-Z0-9]+>",  # Mentions
            r":[a-z_]+:",  # Emojis
            r"thread_ts:",  # Thread indicators
        ]

    def get_strategy_name(self) -> str:
        return "slack_message"

    def _chunk_implementation(
        self, content: str, metadata: Optional[ChunkMetadata] = None
    ) -> list[Chunk]:
        """Split Slack content into individual messages."""
        if len(content) <= self.max_chunk_size:
            return [
                self._create_chunk(
                    content=content,
                    start_index=0,
                    end_index=len(content),
                    chunk_type="slack_message",
                    metadata=metadata,
                )
            ]

        # Split into individual messages
        messages = self._split_into_messages(content)

        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0

        for message in messages:
            message = message.strip()
            if not message:
                continue

            message_size = len(message)

            # If adding this message would exceed max size, create a new chunk
            if current_size + message_size > self.max_chunk_size and current_chunk:
                chunk_content = "\n".join(current_chunk)
                end_index = start_index + len(chunk_content)

                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start_index=start_index,
                        end_index=end_index,
                        chunk_type="slack_message",
                        metadata=metadata,
                    )
                )

                # Start new chunk with overlap
                overlap_start = max(0, len(chunk_content) - self.overlap)
                current_chunk = (
                    [chunk_content[overlap_start:]] if overlap_start > 0 else []
                )
                current_size = len(current_chunk[0]) if current_chunk else 0
                start_index = end_index - self.overlap

            # Add message to current chunk
            current_chunk.append(message)
            current_size += message_size

        # Add final chunk
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            end_index = start_index + len(chunk_content)

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="slack_message",
                    metadata=metadata,
                )
            )

        return chunks

    def _split_into_messages(self, content: str) -> list[str]:
        """Split Slack content into individual messages."""
        lines = content.split("\n")
        messages = []
        current_message = []

        for line in lines:
            # Check if line starts a new message (timestamp)
            is_new_message = bool(
                re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", line)
            )

            if is_new_message and current_message:
                messages.append("\n".join(current_message))
                current_message = []

            current_message.append(line)

        # Add final message
        if current_message:
            messages.append("\n".join(current_message))

        return messages
