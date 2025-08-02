"""Chunk merging utilities."""

from ..core.interfaces import ChunkMerger as ChunkMergerInterface
from ..core.models import Chunk


class ChunkMerger(ChunkMergerInterface):
    """Merges small chunks to improve quality."""

    def __init__(self, min_chunk_size: int = 50, max_chunk_size: int = 512):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks that are too small."""
        if not chunks:
            return chunks

        merged_chunks = []
        current_chunk = None

        for chunk in chunks:
            if current_chunk is None:
                current_chunk = chunk
                continue

            # Check if we should merge
            combined_size = len(current_chunk.content) + len(chunk.content)

            if (
                len(current_chunk.content) < self.min_chunk_size
                and combined_size <= self.max_chunk_size
            ):
                # Merge chunks
                merged_content = current_chunk.content + "\n" + chunk.content
                merged_chunk = Chunk(
                    content=merged_content,
                    start_index=current_chunk.start_index,
                    end_index=chunk.end_index,
                    chunk_type=current_chunk.chunk_type,
                    metadata=current_chunk.metadata,
                    overlap_with_previous=current_chunk.overlap_with_previous,
                    overlap_with_next=chunk.overlap_with_next,
                )
                current_chunk = merged_chunk
            else:
                # Keep current chunk and start new one
                merged_chunks.append(current_chunk)
                current_chunk = chunk

        # Add final chunk
        if current_chunk:
            merged_chunks.append(current_chunk)

        return merged_chunks
