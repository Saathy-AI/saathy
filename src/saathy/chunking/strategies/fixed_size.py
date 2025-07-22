"""Fixed-size chunking strategy."""

import re
from typing import Optional

from .base import BaseChunkingStrategy
from ..core.models import Chunk, ChunkMetadata


class FixedSizeChunker(BaseChunkingStrategy):
    """Token/character-based chunking with overlap."""
    
    def get_strategy_name(self) -> str:
        return "fixed_size"
    
    def _chunk_implementation(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Split content into fixed-size chunks with smart boundaries."""
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="fixed_size",
                metadata=metadata
            )]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.max_chunk_size
            
            # Try to break at word boundary
            if end < len(content):
                last_space = content.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            chunk_content = content[start:end].strip()
            if chunk_content and len(chunk_content) >= self.min_chunk_size:
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_index=start,
                    end_index=end,
                    chunk_type="fixed_size",
                    metadata=metadata
                ))
            
            start = end - self.overlap
            if start >= len(content):
                break
        
        return chunks 