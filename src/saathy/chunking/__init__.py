"""Intelligent text chunking strategies for optimal vector search.

This module provides a comprehensive chunking system with multiple strategies:

## Features
- Fixed-size chunking with configurable overlap
- Semantic chunking (sentence/paragraph boundaries) 
- Code-aware chunking (function/class boundaries)
- Document structure-aware chunking (headers, sections)
- Meeting transcript chunking (speaker turns, timestamps)
- Git commit chunking (commit messages, diffs)
- Slack message chunking (threads, mentions)
- Email chunking (headers, body)
- Content type auto-detection
- Quality validation and analysis
- Caching and optimization

## Usage

```python
from saathy.chunking import ChunkingProcessor

# Basic usage
processor = ChunkingProcessor()
chunks = processor.chunk_content("Your text content here")

# With specific content type
chunks = processor.chunk_content("def function():\n    pass", content_type="code")

# Advanced configuration
from saathy.chunking import ChunkingConfig
config = ChunkingConfig(max_chunk_size=1024, overlap=100)
processor = ChunkingProcessor(config)
```
"""

# Core models and interfaces
from .core import (
    Chunk,
    ChunkingConfig,
    ChunkingError,
    ChunkingStrategy,
    ChunkMetadata,
    ContentType,
    ValidationError,
)

# Main processor
from .processor import ChunkingProcessor

# All chunking strategies
from .strategies import (
    BaseChunkingStrategy,
    CodeChunker,
    DocumentChunker,
    EmailChunker,
    FixedSizeChunker,
    GitCommitChunker,
    MeetingChunker,
    SemanticChunker,
    SlackMessageChunker,
)

# Utilities
from .utils import (
    ChunkCache,
    ChunkMerger,
    ChunkQualityValidator,
    ContentTypeDetector,
    generate_content_hash,
)

# Analysis tools
from .analysis import ChunkAnalyzer, ChunkQualityMetrics, ChunkVisualizer

__all__ = [
    # Core
    "Chunk",
    "ChunkMetadata", 
    "ContentType",
    "ChunkingStrategy",
    "ChunkingConfig",
    "ChunkingError",
    "ValidationError",
    # Main processor
    "ChunkingProcessor",
    # All strategies
    "BaseChunkingStrategy",
    "CodeChunker",
    "DocumentChunker",
    "EmailChunker", 
    "FixedSizeChunker",
    "GitCommitChunker",
    "MeetingChunker",
    "SemanticChunker",
    "SlackMessageChunker",
    # Utilities
    "ContentTypeDetector",
    "ChunkQualityValidator", 
    "ChunkMerger",
    "ChunkCache",
    "generate_content_hash",
    # Analysis
    "ChunkAnalyzer",
    "ChunkVisualizer",
    "ChunkQualityMetrics",
]

__version__ = "0.1.0"
