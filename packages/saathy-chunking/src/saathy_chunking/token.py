"""Token-based chunking strategy using tiktoken."""

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4

import tiktoken

from saathy_core import Chunk, ContentType
from .base import ChunkingStrategy

logger = logging.getLogger(__name__)


class TokenChunker(ChunkingStrategy):
    """Chunk text based on token count using tiktoken."""
    
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
    ):
        """
        Initialize token chunker.
        
        Args:
            model_name: OpenAI model name for tokenizer
            chunk_size: Target token count per chunk
            chunk_overlap: Number of tokens to overlap
            min_chunk_size: Minimum tokens per chunk
        """
        super().__init__(chunk_size, chunk_overlap, min_chunk_size)
        self.model_name = model_name
        
        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            logger.warning(f"Model {model_name} not found, using cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk text based on token count."""
        text = self.clean_text(text)
        if not text:
            return []
        
        # Tokenize the entire text
        tokens = self.encoding.encode(text)
        
        if len(tokens) <= self.chunk_size:
            # Text fits in a single chunk
            return [self._create_chunk(text, tokens, 0, 1, metadata)]
        
        # Split into chunks
        chunks = []
        chunk_start = 0
        chunk_index = 0
        
        while chunk_start < len(tokens):
            # Determine chunk end
            chunk_end = min(chunk_start + self.chunk_size, len(tokens))
            
            # Try to find a good split point
            if chunk_end < len(tokens):
                chunk_tokens = tokens[chunk_start:chunk_end]
                chunk_text = self.encoding.decode(chunk_tokens)
                
                # Find split point in text
                split_pos = self.find_split_point(
                    chunk_text,
                    len(chunk_text) - 1,
                    ["\n\n", "\n", ". ", "! ", "? ", "; ", ", "]
                )
                
                # Re-tokenize up to split point
                if split_pos < len(chunk_text):
                    chunk_text = chunk_text[:split_pos]
                    chunk_tokens = self.encoding.encode(chunk_text)
                    chunk_end = chunk_start + len(chunk_tokens)
            else:
                chunk_tokens = tokens[chunk_start:chunk_end]
            
            # Create chunk
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(
                self._create_chunk(
                    chunk_text,
                    chunk_tokens,
                    chunk_index,
                    -1,  # Total will be set later
                    metadata
                )
            )
            
            # Move to next chunk with overlap
            chunk_start = chunk_end - self.chunk_overlap
            if chunk_start <= chunk_index * self.chunk_size:
                # Prevent infinite loop
                chunk_start = chunk_end
            
            chunk_index += 1
        
        # Update total chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.metadata.total_chunks = total_chunks
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        tokens: List[int],
        index: int,
        total: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk with token information."""
        parent_id = str(uuid4())
        source = metadata.get("source", "unknown") if metadata else "unknown"
        content_type = ContentType(metadata.get("content_type", "text")) if metadata else ContentType.TEXT
        
        chunk_metadata = metadata.copy() if metadata else {}
        chunk_metadata.update({
            "tokenizer": self.model_name,
            "token_count": len(tokens),
        })
        
        chunk = self.create_chunk(
            content=text,
            index=index,
            total=total,
            parent_id=parent_id,
            source=source,
            content_type=content_type,
            additional_metadata=chunk_metadata
        )
        
        # Store token count
        chunk.tokens = len(tokens)
        
        return chunk
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))