"""Base chunking strategy interface."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from saathy_core import Chunk, ChunkMetadata, ContentType


class ChunkingStrategy(ABC):
    """Abstract base class for text chunking strategies."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """
        Initialize chunking strategy.
        
        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Number of characters/tokens to overlap between chunks
            min_chunk_size: Minimum size for a chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    @abstractmethod
    async def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of chunks
        """
        pass
    
    def create_chunk(
        self,
        content: str,
        index: int,
        total: int,
        parent_id: str,
        source: str,
        content_type: ContentType,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk with metadata."""
        metadata = ChunkMetadata(
            source=source,
            content_type=content_type,
            chunk_index=index,
            total_chunks=total,
            parent_id=parent_id,
            metadata=additional_metadata or {},
        )
        
        return Chunk(
            content=content,
            metadata=metadata,
        )
    
    def clean_text(self, text: str) -> str:
        """Clean text before chunking."""
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Remove null characters
        text = text.replace("\x00", "")
        
        return text.strip()
    
    def find_split_point(
        self,
        text: str,
        target_pos: int,
        separators: List[str]
    ) -> int:
        """
        Find a good split point near the target position.
        
        Args:
            text: Text to split
            target_pos: Target position for split
            separators: List of separators in order of preference
            
        Returns:
            Best split position
        """
        # Look for separators near the target position
        search_window = min(100, target_pos // 4)
        
        for separator in separators:
            # Search backwards from target
            pos = text.rfind(separator, max(0, target_pos - search_window), target_pos)
            if pos != -1:
                return pos + len(separator)
            
            # Search forwards from target
            pos = text.find(separator, target_pos, min(len(text), target_pos + search_window))
            if pos != -1:
                return pos + len(separator)
        
        # No good separator found, split at target
        return target_pos