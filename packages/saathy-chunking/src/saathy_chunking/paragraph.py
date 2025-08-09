"""Paragraph-based chunking strategy."""

from typing import List, Optional, Dict, Any
from uuid import uuid4

from saathy_core import Chunk, ContentType
from .base import ChunkingStrategy


class ParagraphChunker(ChunkingStrategy):
    """Chunk text based on paragraphs."""
    
    async def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk text based on paragraphs."""
        text = self.clean_text(text)
        if not text:
            return []
        
        # Split by double newlines for paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        if not paragraphs:
            return []
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_chunk and current_size + para_size > self.chunk_size:
                # Create chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(self._create_chunk(chunk_text, chunk_index, -1, metadata))
                current_chunk = []
                current_size = 0
                chunk_index += 1
            
            current_chunk.append(para)
            current_size += para_size
        
        # Final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(self._create_chunk(chunk_text, chunk_index, -1, metadata))
        
        # Update totals
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
        
        return self.create_chunk(
            content=text,
            index=index,
            total=total,
            parent_id=parent_id,
            source=source,
            content_type=content_type,
            additional_metadata=metadata
        )