"""Base chunking strategy implementation."""

import logging
from typing import Optional

from ..core.interfaces import ChunkingStrategy
from ..core.models import Chunk, ChunkMetadata
from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BaseChunkingStrategy(ChunkingStrategy):
    """Base implementation for chunking strategies."""
    
    def __init__(self, 
                 max_chunk_size: int = 512, 
                 overlap: int = 50,
                 min_chunk_size: int = 50,
                 preserve_context: bool = True):
        super().__init__(max_chunk_size, overlap, min_chunk_size, preserve_context)
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate strategy configuration."""
        if self.max_chunk_size <= 0:
            raise ValidationError("max_chunk_size must be positive")
        if self.overlap < 0:
            raise ValidationError("overlap must be non-negative")
        if self.min_chunk_size <= 0:
            raise ValidationError("min_chunk_size must be positive")
        if self.min_chunk_size > self.max_chunk_size:
            raise ValidationError("min_chunk_size cannot be greater than max_chunk_size")
    
    def _create_chunk(self, 
                     content: str, 
                     start_index: int, 
                     end_index: int, 
                     chunk_type: str,
                     metadata: Optional[ChunkMetadata] = None) -> Chunk:
        """Create a chunk with proper validation."""
        if not content.strip():
            raise ValidationError("Chunk content cannot be empty")
        
        if start_index < 0 or end_index < start_index:
            raise ValidationError("Invalid chunk indices")
        
        chunk_metadata = metadata or ChunkMetadata(content_type=metadata.content_type if metadata else None)
        
        return Chunk(
            content=content.strip(),
            start_index=start_index,
            end_index=end_index,
            chunk_type=chunk_type,
            metadata=chunk_metadata,
            overlap_with_previous=self.overlap,
            overlap_with_next=self.overlap
        )
    
    def _should_merge_chunks(self, current_chunk: Chunk, next_chunk: Chunk) -> bool:
        """Determine if chunks should be merged."""
        combined_size = len(current_chunk.content) + len(next_chunk.content)
        return (len(current_chunk.content) < self.min_chunk_size and 
                combined_size <= self.max_chunk_size)
    
    def _merge_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge small chunks to meet minimum size requirements."""
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_chunk = None
        
        for chunk in chunks:
            if current_chunk is None:
                current_chunk = chunk
                continue
            
            if self._should_merge_chunks(current_chunk, chunk):
                # Merge chunks
                merged_content = current_chunk.content + "\n" + chunk.content
                merged_chunk = self._create_chunk(
                    content=merged_content,
                    start_index=current_chunk.start_index,
                    end_index=chunk.end_index,
                    chunk_type=current_chunk.chunk_type,
                    metadata=current_chunk.metadata
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
    
    def _validate_chunks(self, chunks: list[Chunk], original_content: str) -> None:
        """Validate generated chunks."""
        if not chunks:
            logger.warning("No chunks generated")
            return
        
        total_chunk_length = sum(len(chunk.content) for chunk in chunks)
        coverage_ratio = total_chunk_length / len(original_content) if original_content else 0
        
        if coverage_ratio < 0.8:
            logger.warning(f"Low coverage ratio: {coverage_ratio:.2f}")
        
        for i, chunk in enumerate(chunks):
            if not self._validate_chunk(chunk):
                logger.warning(f"Chunk {i} size ({len(chunk.content)}) outside valid range")
    
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Main chunking method with validation and merging."""
        if not content:
            return []
        
        # Perform chunking
        chunks = self._chunk_implementation(content, metadata)
        
        # Merge small chunks
        chunks = self._merge_chunks(chunks)
        
        # Add context
        chunks = self._add_context(chunks, content)
        
        # Validate results
        self._validate_chunks(chunks, content)
        
        return chunks
    
    def _chunk_implementation(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Implementation-specific chunking logic. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement _chunk_implementation") 