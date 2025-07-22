"""Email chunking strategy."""

import re
from typing import Optional

from .base import BaseChunkingStrategy
from ..core.models import Chunk, ChunkMetadata


class EmailChunker(BaseChunkingStrategy):
    """Email header/body chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.header_patterns = [
            r'^From:\s+',  # From header
            r'^To:\s+',  # To header
            r'^Subject:\s+',  # Subject header
            r'^Date:\s+',  # Date header
            r'^Reply-To:\s+',  # Reply-To header
            r'^Content-Type:\s+',  # Content-Type header
        ]
    
    def get_strategy_name(self) -> str:
        return "email"
    
    def _chunk_implementation(self, content: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Split email into headers and body sections."""
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="email",
                metadata=metadata
            )]
        
        # Split into headers and body
        headers, body = self._split_email_parts(content)
        
        chunks = []
        
        # Chunk headers
        if headers:
            header_chunks = self._chunk_headers(headers, metadata)
            chunks.extend(header_chunks)
        
        # Chunk body
        if body:
            body_chunks = self._chunk_body(body, metadata)
            chunks.extend(body_chunks)
        
        return chunks
    
    def _split_email_parts(self, content: str) -> tuple[str, str]:
        """Split email content into headers and body parts."""
        lines = content.split('\n')
        header_lines = []
        body_lines = []
        in_body = False
        
        for line in lines:
            if line.strip() == '' and header_lines:
                in_body = True
                continue
            
            if in_body:
                body_lines.append(line)
            else:
                header_lines.append(line)
        
        return '\n'.join(header_lines), '\n'.join(body_lines)
    
    def _chunk_headers(self, headers: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Chunk email headers."""
        if len(headers) <= self.max_chunk_size:
            return [self._create_chunk(
                content=headers,
                start_index=0,
                end_index=len(headers),
                chunk_type="email_headers",
                metadata=metadata
            )]
        
        # Split headers by type
        header_groups = self._group_headers(headers)
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for group in header_groups:
            group = group.strip()
            if not group:
                continue
            
            group_size = len(group)
            
            if current_size + group_size > self.max_chunk_size and current_chunk:
                chunk_content = '\n'.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="email_headers",
                    metadata=metadata
                ))
                
                start_index = end_index
                current_chunk = []
                current_size = 0
            
            current_chunk.append(group)
            current_size += group_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="email_headers",
                metadata=metadata
            ))
        
        return chunks
    
    def _chunk_body(self, body: str, metadata: Optional[ChunkMetadata] = None) -> list[Chunk]:
        """Chunk email body using semantic boundaries."""
        if len(body) <= self.max_chunk_size:
            return [self._create_chunk(
                content=body,
                start_index=0,
                end_index=len(body),
                chunk_type="email_body",
                metadata=metadata
            )]
        
        # Split by paragraphs
        paragraphs = body.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            paragraph_size = len(paragraph)
            
            if current_size + paragraph_size > self.max_chunk_size and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="email_body",
                    metadata=metadata
                ))
                
                start_index = end_index
                current_chunk = []
                current_size = 0
            
            current_chunk.append(paragraph)
            current_size += paragraph_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunks.append(self._create_chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="email_body",
                metadata=metadata
            ))
        
        return chunks
    
    def _group_headers(self, headers: str) -> list[str]:
        """Group related headers together."""
        lines = headers.split('\n')
        groups = []
        current_group = []
        
        for line in lines:
            # Check if line starts a new header
            is_new_header = any(re.match(pattern, line) for pattern in self.header_patterns)
            
            if is_new_header and current_group:
                groups.append('\n'.join(current_group))
                current_group = []
            
            current_group.append(line)
        
        # Add final group
        if current_group:
            groups.append('\n'.join(current_group))
        
        return groups 