"""Meeting transcript chunking strategy."""

import re
from typing import Optional

from ..core.models import Chunk, ChunkMetadata
from .base import BaseChunkingStrategy


class MeetingChunker(BaseChunkingStrategy):
    """Speaker-turn aware meeting chunking."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speaker_patterns = [
            r"^(\w+):\s*",  # Speaker format
            r"^\[(\w+)\]\s*",  # Bracket speaker format
            r"^(\w+)\s*\([^)]*\):\s*",  # Speaker with role
        ]
        self.timestamp_pattern = r"\[\d{2}:\d{2}:\d{2}\]"

    def get_strategy_name(self) -> str:
        return "meeting"

    def _chunk_implementation(
        self, content: str, metadata: Optional[ChunkMetadata] = None
    ) -> list[Chunk]:
        """Split meeting transcript by speaker turns."""
        if len(content) <= self.max_chunk_size:
            return [
                self._create_chunk(
                    content=content,
                    start_index=0,
                    end_index=len(content),
                    chunk_type="meeting",
                    metadata=metadata,
                )
            ]

        # Split into speaker turns
        turns = self._split_into_turns(content)

        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0

        for turn in turns:
            turn = turn.strip()
            if not turn:
                continue

            turn_size = len(turn)

            # If adding this turn would exceed max size, create a new chunk
            if current_size + turn_size > self.max_chunk_size and current_chunk:
                chunk_content = "\n".join(current_chunk)
                end_index = start_index + len(chunk_content)

                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start_index=start_index,
                        end_index=end_index,
                        chunk_type="meeting",
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

            # Add turn to current chunk
            current_chunk.append(turn)
            current_size += turn_size

        # Add final chunk
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            end_index = start_index + len(chunk_content)

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="meeting",
                    metadata=metadata,
                )
            )

        return chunks

    def _split_into_turns(self, content: str) -> list[str]:
        """Split meeting content into speaker turns."""
        lines = content.split("\n")
        turns = []
        current_turn = []

        for line in lines:
            # Check if line starts a new speaker turn
            is_new_turn = any(
                re.match(pattern, line) for pattern in self.speaker_patterns
            )

            if is_new_turn and current_turn:
                turns.append("\n".join(current_turn))
                current_turn = []

            current_turn.append(line)

        # Add final turn
        if current_turn:
            turns.append("\n".join(current_turn))

        return turns
