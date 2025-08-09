"""Sentence-based chunking strategy."""

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4

import nltk
from nltk.tokenize import sent_tokenize

from saathy_core import Chunk, ContentType
from .base import ChunkingStrategy

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logger.info("Downloading NLTK punkt tokenizer...")
    nltk.download('punkt', quiet=True)


class SentenceChunker(ChunkingStrategy):
    """Chunk text based on sentences."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
        language: str = "english"
    ):
        """
        Initialize sentence chunker.
        
        Args:
            chunk_size: Target characters per chunk
            chunk_overlap: Number of characters to overlap
            min_chunk_size: Minimum characters per chunk
            language: Language for sentence tokenization
        """
        super().__init__(chunk_size, chunk_overlap, min_chunk_size)
        self.language = language
    
    async def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Chunk text based on sentences."""
        text = self.clean_text(text)
        if not text:
            return []
        
        # Tokenize into sentences
        sentences = sent_tokenize(text, language=self.language)
        
        if not sentences:
            return []
        
        # Group sentences into chunks
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if current_chunk and current_size + sentence_size > self.chunk_size:
                # Create chunk from current sentences
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, -1, metadata)
                )
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Include last few sentences for overlap
                    overlap_sentences = []
                    overlap_size = 0
                    
                    for sent in reversed(current_chunk):
                        if overlap_size + len(sent) <= self.chunk_overlap:
                            overlap_sentences.insert(0, sent)
                            overlap_size += len(sent)
                        else:
                            break
                    
                    current_chunk = overlap_sentences
                    current_size = overlap_size
                else:
                    current_chunk = []
                    current_size = 0
                
                chunk_index += 1
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Create final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    self._create_chunk(chunk_text, chunk_index, -1, metadata)
                )
            elif chunks:
                # Append to previous chunk if too small
                chunks[-1].content += " " + chunk_text
        
        # Update total chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.metadata.total_chunks = total_chunks
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        index: int,
        total: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk with sentence information."""
        parent_id = str(uuid4())
        source = metadata.get("source", "unknown") if metadata else "unknown"
        content_type = ContentType(metadata.get("content_type", "text")) if metadata else ContentType.TEXT
        
        chunk_metadata = metadata.copy() if metadata else {}
        chunk_metadata.update({
            "chunking_method": "sentence",
            "language": self.language,
            "sentence_count": len(sent_tokenize(text, language=self.language)),
        })
        
        return self.create_chunk(
            content=text,
            index=index,
            total=total,
            parent_id=parent_id,
            source=source,
            content_type=content_type,
            additional_metadata=chunk_metadata
        )