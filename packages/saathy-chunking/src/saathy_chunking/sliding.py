"""Sliding window chunking strategy."""

from typing import List, Optional, Dict, Any
from uuid import uuid4

from saathy_core import Chunk, ContentType
from .base import ChunkingStrategy


class SlidingWindowChunker(ChunkingStrategy):
    """Chunk text using a sliding window approach."""
    
    async def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk text using sliding window."""
        text = self.clean_text(text)
        if not text:
            return []
        
        chunks = []
        text_length = len(text)
        chunk_index = 0
        position = 0
        
        while position < text_length:
            # Calculate chunk boundaries
            chunk_end = min(position + self.chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = text[position:chunk_end]
            
            # Only create chunk if it meets minimum size
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, -1, metadata)
                )
                chunk_index += 1
            
            # Move window
            if chunk_end < text_length:
                position += self.chunk_size - self.chunk_overlap
            else:
                break
            
            # Ensure we make progress
            if position <= chunk_index * (self.chunk_size - self.chunk_overlap):
                position = chunk_end
        
        # Update total chunks
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        index: int,
        total: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk."""
        parent_id = str(uuid4())
        source = metadata.get("source", "unknown") if metadata else "unknown"
        content_type = ContentType(metadata.get("content_type", "text")) if metadata else ContentType.TEXT
        
        chunk_metadata = metadata.copy() if metadata else {}
        chunk_metadata["chunking_method"] = "sliding_window"
        
        return self.create_chunk(
            content=text,
            index=index,
            total=total,
            parent_id=parent_id,
            source=source,
            content_type=content_type,
            additional_metadata=chunk_metadata
        )