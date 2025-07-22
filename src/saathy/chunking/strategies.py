"""Advanced chunking strategies for different content types."""

import re
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content type enumeration."""
    TEXT = "text"
    CODE = "code"
    DOCUMENT = "document"
    MEETING = "meeting"
    GIT_COMMIT = "git_commit"
    SLACK_MESSAGE = "slack_message"
    EMAIL = "email"
    UNKNOWN = "unknown"


@dataclass
class ChunkMetadata:
    """Enhanced metadata for chunks."""
    content_type: ContentType
    source_file: Optional[str] = None
    source_line_start: Optional[int] = None
    source_line_end: Optional[int] = None
    chunk_id: Optional[str] = None
    parent_chunk_id: Optional[str] = None
    hierarchy_level: int = 0
    semantic_score: float = 0.0
    token_count: int = 0
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Enhanced content chunk with metadata."""
    content: str
    start_index: int
    end_index: int
    chunk_type: str
    metadata: ChunkMetadata
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    context_before: str = ""
    context_after: str = ""
    
    def __post_init__(self):
        """Generate chunk ID if not provided."""
        if not self.metadata.chunk_id:
            content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
            self.metadata.chunk_id = f"{self.chunk_type}_{content_hash}"


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""
    
    def __init__(self, 
                 max_chunk_size: int = 512, 
                 overlap: int = 50,
                 min_chunk_size: int = 50,
                 preserve_context: bool = True):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.preserve_context = preserve_context
        
    @abstractmethod
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split content into chunks."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this chunking strategy."""
        pass
    
    def _add_context(self, chunks: List[Chunk], original_content: str) -> List[Chunk]:
        """Add context before and after chunks."""
        if not self.preserve_context:
            return chunks
            
        for i, chunk in enumerate(chunks):
            # Add context before
            if i > 0:
                prev_chunk = chunks[i-1]
                context_start = max(0, prev_chunk.end_index - self.overlap)
                chunk.context_before = original_content[context_start:chunk.start_index]
            
            # Add context after
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                context_end = min(len(original_content), next_chunk.start_index + self.overlap)
                chunk.context_after = original_content[chunk.end_index:context_end]
                
        return chunks


class FixedSizeChunker(ChunkingStrategy):
    """Token/character-based chunking with overlap."""
    
    def get_strategy_name(self) -> str:
        return "fixed_size"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split content into fixed-size chunks with smart boundaries."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="fixed_size",
                metadata=metadata or ChunkMetadata(content_type=ContentType.TEXT)
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
                # Calculate overlaps
                overlap_prev = min(self.overlap, start)
                overlap_next = min(self.overlap, len(content) - end)
                
                chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.TEXT)
                chunk_metadata.token_count = len(chunk_content.split())
                
                chunks.append(Chunk(
                    content=chunk_content,
                    start_index=start,
                    end_index=end,
                    chunk_type="fixed_size",
                    metadata=chunk_metadata,
                    overlap_with_previous=overlap_prev,
                    overlap_with_next=overlap_next
                ))
                
            start = end - self.overlap
            if start >= len(content):
                break
                
        return self._add_context(chunks, content)


class SemanticChunker(ChunkingStrategy):
    """Sentence boundary-aware chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sentence_endings = r'[.!?]\s+'
        self.paragraph_breaks = r'\n\s*\n'
        self.semantic_breaks = [
            r'\n\s*[-*+]\s+',  # List items
            r'\n\s*\d+\.\s+',  # Numbered lists
            r'\n\s*[A-Z][a-z]+:\s*$',  # Section labels
        ]
        
    def get_strategy_name(self) -> str:
        return "semantic"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split content based on semantic boundaries."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="semantic",
                metadata=metadata or ChunkMetadata(content_type=ContentType.TEXT)
            )]
            
        # Split into semantic units
        semantic_units = self._split_into_semantic_units(content)
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0
        
        for unit in semantic_units:
            unit = unit.strip()
            if not unit:
                continue
                
            unit_size = len(unit)
            
            # If adding this unit would exceed max size, create a new chunk
            if current_size + unit_size > self.max_chunk_size and current_chunk:
                chunk_content = ' '.join(current_chunk)
                end_index = start_index + len(chunk_content)
                
                chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.TEXT)
                chunk_metadata.token_count = len(chunk_content.split())
                
                chunks.append(Chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="semantic",
                    metadata=chunk_metadata,
                    overlap_with_previous=self.overlap,
                    overlap_with_next=self.overlap
                ))
                
                # Start new chunk with overlap
                overlap_start = max(0, len(chunk_content) - self.overlap)
                current_chunk = [chunk_content[overlap_start:]] if overlap_start > 0 else []
                current_size = len(current_chunk[0]) if current_chunk else 0
                start_index = end_index - self.overlap
                
            # Add unit to current chunk
            current_chunk.append(unit)
            current_size += unit_size
            
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            end_index = start_index + len(chunk_content)
            
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.TEXT)
            chunk_metadata.token_count = len(chunk_content.split())
            
            chunks.append(Chunk(
                content=chunk_content,
                start_index=start_index,
                end_index=end_index,
                chunk_type="semantic",
                metadata=chunk_metadata,
                overlap_with_previous=self.overlap,
                overlap_with_next=0
            ))
            
        return self._add_context(chunks, content)
    
    def _split_into_semantic_units(self, content: str) -> List[str]:
        """Split content into semantic units."""
        # First split by paragraph breaks
        paragraphs = re.split(self.paragraph_breaks, content)
        units = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # Split paragraph into sentences
            sentences = re.split(self.sentence_endings, paragraph)
            units.extend([s.strip() for s in sentences if s.strip()])
            
        return units


class CodeChunker(ChunkingStrategy):
    """Function/class-aware code splitting."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.language_patterns = {
            'python': {
                'function': r'def\s+(\w+)\s*\([^)]*\)\s*:',
                'class': r'class\s+(\w+)(?:\([^)]*\))?\s*:',
                'import': r'^(?:from\s+\w+\s+import\s+[\w\s,]+|import\s+[\w\s,]+)',
                'comment': r'#.*$',
                'docstring': r'"""[^"]*"""|\'\'\'[^\']*\'\'\''
            },
            'javascript': {
                'function': r'(?:function\s+(\w+)|(\w+)\s*[:=]\s*function|\w+\s*[:=]\s*\([^)]*\)\s*=>)',
                'class': r'class\s+(\w+)',
                'import': r'^(?:import\s+.*|const\s+.*require\(.*\))',
                'comment': r'//.*$|/\*[\s\S]*?\*/',
                'docstring': r'/\*\*[\s\S]*?\*/'
            },
            'java': {
                'function': r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:[\w<>\[\]]+\s+)?(\w+)\s*\([^)]*\)\s*\{',
                'class': r'(?:public\s+)?class\s+(\w+)',
                'import': r'^import\s+.*;',
                'comment': r'//.*$|/\*[\s\S]*?\*/',
                'docstring': r'/\*\*[\s\S]*?\*/'
            }
        }
        
    def get_strategy_name(self) -> str:
        return "code"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split code based on function/class boundaries."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="code",
                metadata=metadata or ChunkMetadata(content_type=ContentType.CODE)
            )]
            
        # Detect language
        language = self._detect_language(content)
        patterns = self.language_patterns.get(language, self.language_patterns['python'])
        
        # Extract code structures
        structures = self._extract_code_structures(content, patterns)
        
        chunks = []
        for structure in structures:
            structure_chunks = self._chunk_structure(structure, metadata)
            chunks.extend(structure_chunks)
            
        return self._add_context(chunks, content)
    
    def _detect_language(self, content: str) -> str:
        """Detect programming language from content."""
        # Simple heuristics for language detection
        if 'def ' in content or 'import ' in content or 'class ' in content:
            return 'python'
        elif 'function ' in content or 'const ' in content or 'let ' in content:
            return 'javascript'
        elif 'public class' in content or 'import ' in content:
            return 'java'
        else:
            return 'python'  # Default
    
    def _extract_code_structures(self, content: str, patterns: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract code structures (functions, classes, etc.)."""
        structures = []
        lines = content.split('\n')
        
        current_structure = None
        brace_count = 0
        
        for i, line in enumerate(lines):
            # Check for function/class start
            for struct_type, pattern in patterns.items():
                if struct_type in ['function', 'class']:
                    match = re.search(pattern, line)
                    if match:
                        if current_structure:
                            current_structure['end_line'] = i - 1
                            structures.append(current_structure)
                        
                        current_structure = {
                            'type': struct_type,
                            'name': match.group(1) or match.group(2) or 'anonymous',
                            'start_line': i,
                            'content': [line],
                            'start': content.find(line)
                        }
                        break
            
            if current_structure:
                current_structure['content'].append(line)
                
                # Count braces for structure end detection
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0 and current_structure['content']:
                    current_structure['end_line'] = i
                    current_structure['end'] = content.find(line) + len(line)
                    structures.append(current_structure)
                    current_structure = None
                    brace_count = 0
        
        # Add any remaining structure
        if current_structure:
            current_structure['end_line'] = len(lines) - 1
            current_structure['end'] = len(content)
            structures.append(current_structure)
            
        return structures
    
    def _chunk_structure(self, structure: Dict[str, Any], metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Chunk a code structure."""
        content = '\n'.join(structure['content'])
        
        if len(content) <= self.max_chunk_size:
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.CODE)
            chunk_metadata.custom_fields.update({
                'structure_type': structure['type'],
                'structure_name': structure['name'],
                'start_line': structure['start_line'],
                'end_line': structure['end_line']
            })
            
            return [Chunk(
                content=content,
                start_index=structure['start'],
                end_index=structure['end'],
                chunk_type="code",
                metadata=chunk_metadata
            )]
        
        # For large structures, use fixed-size chunking
        chunker = FixedSizeChunker(self.max_chunk_size, self.overlap)
        chunks = chunker.chunk(content)
        
        # Update metadata for each chunk
        for chunk in chunks:
            chunk.metadata.content_type = ContentType.CODE
            chunk.metadata.custom_fields.update({
                'structure_type': structure['type'],
                'structure_name': structure['name'],
                'start_line': structure['start_line'],
                'end_line': structure['end_line']
            })
            
        return chunks


class DocumentChunker(ChunkingStrategy):
    """Structure-aware document chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.section_patterns = [
            r'^#{1,6}\s+',  # Markdown headers
            r'^[A-Z][A-Z\s]+\n[-=]+\n',  # Underlined headers
            r'^\d+\.\s+',  # Numbered sections
            r'^[A-Z][a-z]+\s*:\s*$',  # Section labels
            r'^[IVX]+\.\s+',  # Roman numerals
            r'^[A-Z]\.\s+',  # Letter sections
        ]
        
    def get_strategy_name(self) -> str:
        return "document"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split document based on structure."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="document",
                metadata=metadata or ChunkMetadata(content_type=ContentType.DOCUMENT)
            )]
            
        # Split into sections
        sections = self._split_into_sections(content)
        chunks = []
        
        for section in sections:
            section_chunks = self._chunk_section(section, metadata)
            chunks.extend(section_chunks)
            
        return self._add_context(chunks, content)
    
    def _split_into_sections(self, content: str) -> List[Dict[str, Any]]:
        """Split content into sections based on headers."""
        sections = []
        lines = content.split('\n')
        
        current_section = {
            'title': 'Introduction',
            'content': [],
            'start_line': 0,
            'level': 0
        }
        
        for i, line in enumerate(lines):
            # Check if line is a header
            header_level = self._get_header_level(line)
            
            if header_level > 0:
                # Save current section
                if current_section['content']:
                    current_section['end_line'] = i - 1
                    current_section['content'] = '\n'.join(current_section['content'])
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'title': line.strip('#').strip(),
                    'content': [],
                    'start_line': i,
                    'level': header_level
                }
            else:
                current_section['content'].append(line)
        
        # Add final section
        if current_section['content']:
            current_section['end_line'] = len(lines) - 1
            current_section['content'] = '\n'.join(current_section['content'])
            sections.append(current_section)
            
        return sections
    
    def _get_header_level(self, line: str) -> int:
        """Get header level for a line."""
        for pattern in self.section_patterns:
            if re.match(pattern, line):
                if pattern.startswith('^#{1,6}'):
                    return line.count('#')
                return 1
        return 0
    
    def _chunk_section(self, section: Dict[str, Any], metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Chunk a document section."""
        content = f"{section['title']}\n\n{section['content']}"
        
        if len(content) <= self.max_chunk_size:
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.DOCUMENT)
            chunk_metadata.custom_fields.update({
                'section_title': section['title'],
                'section_level': section['level'],
                'start_line': section['start_line'],
                'end_line': section['end_line']
            })
            
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="document",
                metadata=chunk_metadata
            )]
        
        # For large sections, use semantic chunking
        chunker = SemanticChunker(self.max_chunk_size, self.overlap)
        chunks = chunker.chunk(content)
        
        # Update metadata for each chunk
        for chunk in chunks:
            chunk.metadata.content_type = ContentType.DOCUMENT
            chunk.metadata.custom_fields.update({
                'section_title': section['title'],
                'section_level': section['level'],
                'start_line': section['start_line'],
                'end_line': section['end_line']
            })
            
        return chunks


class MeetingChunker(ChunkingStrategy):
    """Speaker-turn and time-based meeting chunking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speaker_patterns = [
            r'^(\w+):\s*',  # Simple speaker format
            r'^\[(\w+)\]\s*',  # Bracket format
            r'^(\w+)\s*\([^)]*\):\s*',  # Speaker with role
            r'^(\w+)\s*-\s*',  # Dash format
        ]
        self.time_patterns = [
            r'\[(\d{2}:\d{2}:\d{2})\]',  # Timestamp format
            r'(\d{2}:\d{2})\s*',  # Time format
        ]
        
    def get_strategy_name(self) -> str:
        return "meeting"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split meeting transcript based on speaker turns and topics."""
        if len(content) <= self.max_chunk_size:
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="meeting",
                metadata=metadata or ChunkMetadata(content_type=ContentType.MEETING)
            )]
            
        # Split into speaker turns
        turns = self._split_into_speaker_turns(content)
        chunks = []
        
        for turn in turns:
            turn_chunks = self._chunk_speaker_turn(turn, metadata)
            chunks.extend(turn_chunks)
            
        return self._add_context(chunks, content)
    
    def _split_into_speaker_turns(self, content: str) -> List[Dict[str, Any]]:
        """Split content into speaker turns."""
        turns = []
        lines = content.split('\n')
        
        current_turn = None
        
        for i, line in enumerate(lines):
            speaker = self._extract_speaker(line)
            timestamp = self._extract_timestamp(line)
            
            if speaker:
                # Save current turn
                if current_turn:
                    current_turn['end_line'] = i - 1
                    current_turn['content'] = '\n'.join(current_turn['content'])
                    turns.append(current_turn)
                
                # Start new turn
                current_turn = {
                    'speaker': speaker,
                    'timestamp': timestamp,
                    'content': [line],
                    'start_line': i
                }
            elif current_turn:
                current_turn['content'].append(line)
        
        # Add final turn
        if current_turn:
            current_turn['end_line'] = len(lines) - 1
            current_turn['content'] = '\n'.join(current_turn['content'])
            turns.append(current_turn)
            
        return turns
    
    def _extract_speaker(self, line: str) -> Optional[str]:
        """Extract speaker name from line."""
        for pattern in self.speaker_patterns:
            match = re.match(pattern, line)
            if match:
                return match.group(1)
        return None
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from line."""
        for pattern in self.time_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None
    
    def _chunk_speaker_turn(self, turn: Dict[str, Any], metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Chunk a speaker turn."""
        content = turn['content']
        
        if len(content) <= self.max_chunk_size:
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.MEETING)
            chunk_metadata.custom_fields.update({
                'speaker': turn['speaker'],
                'timestamp': turn['timestamp'],
                'start_line': turn['start_line'],
                'end_line': turn['end_line']
            })
            
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="meeting",
                metadata=chunk_metadata
            )]
        
        # For long turns, use semantic chunking
        chunker = SemanticChunker(self.max_chunk_size, self.overlap)
        chunks = chunker.chunk(content)
        
        # Update metadata for each chunk
        for chunk in chunks:
            chunk.metadata.content_type = ContentType.MEETING
            chunk.metadata.custom_fields.update({
                'speaker': turn['speaker'],
                'timestamp': turn['timestamp'],
                'start_line': turn['start_line'],
                'end_line': turn['end_line']
            })
            
        return chunks


class GitCommitChunker(ChunkingStrategy):
    """Git commit diff and message chunking."""
    
    def get_strategy_name(self) -> str:
        return "git_commit"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split git commit into message and diff chunks."""
        # Split commit message and diff
        parts = self._split_commit_parts(content)
        chunks = []
        
        for part in parts:
            part_chunks = self._chunk_commit_part(part, metadata)
            chunks.extend(part_chunks)
            
        return self._add_context(chunks, content)
    
    def _split_commit_parts(self, content: str) -> List[Dict[str, Any]]:
        """Split commit into message and diff parts."""
        parts = []
        lines = content.split('\n')
        
        # Find diff separator
        diff_start = -1
        for i, line in enumerate(lines):
            if line.startswith('diff --git') or line.startswith('---') or line.startswith('+++'):
                diff_start = i
                break
        
        if diff_start > 0:
            # Commit message
            message_content = '\n'.join(lines[:diff_start])
            parts.append({
                'type': 'message',
                'content': message_content,
                'start_line': 0,
                'end_line': diff_start - 1
            })
            
            # Diff content
            diff_content = '\n'.join(lines[diff_start:])
            parts.append({
                'type': 'diff',
                'content': diff_content,
                'start_line': diff_start,
                'end_line': len(lines) - 1
            })
        else:
            # No diff found, treat as message only
            parts.append({
                'type': 'message',
                'content': content,
                'start_line': 0,
                'end_line': len(lines) - 1
            })
            
        return parts
    
    def _chunk_commit_part(self, part: Dict[str, Any], metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Chunk a commit part (message or diff)."""
        content = part['content']
        
        if len(content) <= self.max_chunk_size:
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.GIT_COMMIT)
            chunk_metadata.custom_fields.update({
                'commit_part_type': part['type'],
                'start_line': part['start_line'],
                'end_line': part['end_line']
            })
            
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="git_commit",
                metadata=chunk_metadata
            )]
        
        # For large parts, use appropriate chunking strategy
        if part['type'] == 'diff':
            chunker = FixedSizeChunker(self.max_chunk_size, self.overlap)
        else:
            chunker = SemanticChunker(self.max_chunk_size, self.overlap)
            
        chunks = chunker.chunk(content)
        
        # Update metadata for each chunk
        for chunk in chunks:
            chunk.metadata.content_type = ContentType.GIT_COMMIT
            chunk.metadata.custom_fields.update({
                'commit_part_type': part['type'],
                'start_line': part['start_line'],
                'end_line': part['end_line']
            })
            
        return chunks


class SlackMessageChunker(ChunkingStrategy):
    """Slack message thread-aware chunking."""
    
    def get_strategy_name(self) -> str:
        return "slack_message"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split Slack messages with thread awareness."""
        # Split into individual messages
        messages = self._split_into_messages(content)
        chunks = []
        
        for message in messages:
            message_chunks = self._chunk_message(message, metadata)
            chunks.extend(message_chunks)
            
        return self._add_context(chunks, content)
    
    def _split_into_messages(self, content: str) -> List[Dict[str, Any]]:
        """Split content into individual Slack messages."""
        messages = []
        lines = content.split('\n')
        
        current_message = None
        
        for i, line in enumerate(lines):
            # Check for message start patterns
            if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line):  # Timestamp
                # Save current message
                if current_message:
                    current_message['end_line'] = i - 1
                    current_message['content'] = '\n'.join(current_message['content'])
                    messages.append(current_message)
                
                # Start new message
                current_message = {
                    'timestamp': line.split()[0] + ' ' + line.split()[1],
                    'content': [line],
                    'start_line': i
                }
            elif current_message:
                current_message['content'].append(line)
        
        # Add final message
        if current_message:
            current_message['end_line'] = len(lines) - 1
            current_message['content'] = '\n'.join(current_message['content'])
            messages.append(current_message)
            
        return messages
    
    def _chunk_message(self, message: Dict[str, Any], metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Chunk a Slack message."""
        content = message['content']
        
        if len(content) <= self.max_chunk_size:
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.SLACK_MESSAGE)
            chunk_metadata.custom_fields.update({
                'timestamp': message['timestamp'],
                'start_line': message['start_line'],
                'end_line': message['end_line']
            })
            
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="slack_message",
                metadata=chunk_metadata
            )]
        
        # For long messages, use semantic chunking
        chunker = SemanticChunker(self.max_chunk_size, self.overlap)
        chunks = chunker.chunk(content)
        
        # Update metadata for each chunk
        for chunk in chunks:
            chunk.metadata.content_type = ContentType.SLACK_MESSAGE
            chunk.metadata.custom_fields.update({
                'timestamp': message['timestamp'],
                'start_line': message['start_line'],
                'end_line': message['end_line']
            })
            
        return chunks


class EmailChunker(ChunkingStrategy):
    """Email header and body chunking."""
    
    def get_strategy_name(self) -> str:
        return "email"
        
    def chunk(self, content: str, metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Split email into headers and body."""
        # Split email parts
        parts = self._split_email_parts(content)
        chunks = []
        
        for part in parts:
            part_chunks = self._chunk_email_part(part, metadata)
            chunks.extend(part_chunks)
            
        return self._add_context(chunks, content)
    
    def _split_email_parts(self, content: str) -> List[Dict[str, Any]]:
        """Split email into headers and body."""
        parts = []
        lines = content.split('\n')
        
        # Find body separator
        body_start = -1
        for i, line in enumerate(lines):
            if line.strip() == '' and i > 0:
                body_start = i + 1
                break
        
        if body_start > 0:
            # Headers
            header_content = '\n'.join(lines[:body_start])
            parts.append({
                'type': 'headers',
                'content': header_content,
                'start_line': 0,
                'end_line': body_start - 1
            })
            
            # Body
            body_content = '\n'.join(lines[body_start:])
            parts.append({
                'type': 'body',
                'content': body_content,
                'start_line': body_start,
                'end_line': len(lines) - 1
            })
        else:
            # No clear separation, treat as body
            parts.append({
                'type': 'body',
                'content': content,
                'start_line': 0,
                'end_line': len(lines) - 1
            })
            
        return parts
    
    def _chunk_email_part(self, part: Dict[str, Any], metadata: Optional[ChunkMetadata] = None) -> List[Chunk]:
        """Chunk an email part (headers or body)."""
        content = part['content']
        
        if len(content) <= self.max_chunk_size:
            chunk_metadata = metadata or ChunkMetadata(content_type=ContentType.EMAIL)
            chunk_metadata.custom_fields.update({
                'email_part_type': part['type'],
                'start_line': part['start_line'],
                'end_line': part['end_line']
            })
            
            return [Chunk(
                content=content,
                start_index=0,
                end_index=len(content),
                chunk_type="email",
                metadata=chunk_metadata
            )]
        
        # For large parts, use semantic chunking
        chunker = SemanticChunker(self.max_chunk_size, self.overlap)
        chunks = chunker.chunk(content)
        
        # Update metadata for each chunk
        for chunk in chunks:
            chunk.metadata.content_type = ContentType.EMAIL
            chunk.metadata.custom_fields.update({
                'email_part_type': part['type'],
                'start_line': part['start_line'],
                'end_line': part['end_line']
            })
            
        return chunks 