# Intelligent Text Chunking System

## Overview

The Saathy chunking system provides sophisticated text chunking strategies optimized for different content types and vector search applications. It automatically detects content types and applies the most appropriate chunking strategy to ensure optimal retrieval performance.

## Features

### 🎯 **Multiple Chunking Strategies**
- **FixedSizeChunker**: Token/character-based with configurable overlap
- **SemanticChunker**: Sentence boundary-aware chunking
- **CodeChunker**: Function/class-aware code splitting
- **DocumentChunker**: Structure-aware (headers, sections)
- **MeetingChunker**: Speaker-turn and time-based splitting
- **GitCommitChunker**: Diff hunks and commit message separation
- **SlackMessageChunker**: Thread-aware message chunking
- **EmailChunker**: Header and body separation

### 🔍 **Automatic Content Detection**
- Pattern-based content type detection
- File extension recognition
- Intelligent strategy selection

### 📊 **Quality Validation & Analysis**
- Chunk quality metrics (coverage, coherence, efficiency)
- Content loss detection
- Overlap analysis
- Statistical reporting

### 🎨 **Visualization & Debugging**
- Chunk size distribution plots
- Overlap analysis visualization
- Quality metrics radar charts
- Chunk boundary visualization

### ⚡ **Performance Optimizations**
- Hash-based chunk caching
- Lazy chunking for large documents
- Memory-efficient streaming
- Parallel processing support

## Architecture

```
src/saathy/chunking/
├── __init__.py          # Module exports
├── strategies.py        # Chunking strategies
├── processor.py         # Main processor & orchestration
└── analysis.py          # Analysis & visualization tools
```

## Quick Start

### Basic Usage

```python
from src.saathy.chunking import ChunkingProcessor

# Initialize processor
processor = ChunkingProcessor()

# Chunk content (automatic strategy selection)
content = "Your content here..."
chunks = processor.chunk_content(content)

# Access chunk information
for chunk in chunks:
    print(f"Content: {chunk.content[:100]}...")
    print(f"Type: {chunk.chunk_type}")
    print(f"Size: {len(chunk.content)} characters")
    print(f"Metadata: {chunk.metadata.custom_fields}")
```

### Advanced Configuration

```python
from src.saathy.chunking import ChunkingProcessor, ChunkingConfig

# Custom configuration
config = ChunkingConfig(
    max_chunk_size=512,      # Maximum chunk size
    overlap=50,              # Overlap between chunks
    min_chunk_size=50,       # Minimum chunk size
    preserve_context=True,   # Preserve context across boundaries
    enable_caching=True,     # Enable chunk caching
    cache_ttl=3600,         # Cache TTL in seconds
    parallel_processing=False # Enable parallel processing
)

processor = ChunkingProcessor(config)
```

## Chunking Strategies

### FixedSizeChunker

Best for: General text content, when semantic boundaries are not critical.

```python
from src.saathy.chunking import FixedSizeChunker

chunker = FixedSizeChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk("Your content here...")
```

**Features:**
- Configurable chunk size and overlap
- Word boundary preservation
- Efficient for large documents

### SemanticChunker

Best for: Natural language text, documents, articles.

```python
from src.saathy.chunking import SemanticChunker

chunker = SemanticChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk("Your document content...")
```

**Features:**
- Sentence boundary awareness
- Semantic unit preservation
- Natural language optimization

### CodeChunker

Best for: Source code files, programming documentation.

```python
from src.saathy.chunking import CodeChunker

chunker = CodeChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk(code_content)
```

**Features:**
- Function/class boundary detection
- Import statement preservation
- Comment and docstring handling
- Multi-language support (Python, JavaScript, Java)

### DocumentChunker

Best for: Structured documents, markdown, technical docs.

```python
from src.saathy.chunking import DocumentChunker

chunker = DocumentChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk(document_content)
```

**Features:**
- Header hierarchy preservation
- Section boundary detection
- List and table handling
- Footnote preservation

### MeetingChunker

Best for: Meeting transcripts, conversation logs.

```python
from src.saathy.chunking import MeetingChunker

chunker = MeetingChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk(meeting_transcript)
```

**Features:**
- Speaker turn detection
- Timestamp preservation
- Topic shift identification
- Action item extraction

### GitCommitChunker

Best for: Git commit messages and diffs.

```python
from src.saathy.chunking import GitCommitChunker

chunker = GitCommitChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk(commit_content)
```

**Features:**
- Commit message separation
- Diff hunk preservation
- File grouping
- Metadata extraction

### SlackMessageChunker

Best for: Slack conversation exports.

```python
from src.saathy.chunking import SlackMessageChunker

chunker = SlackMessageChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk(slack_export)
```

**Features:**
- Thread awareness
- Reply context preservation
- Emoji handling
- Timestamp extraction

### EmailChunker

Best for: Email archives, communication logs.

```python
from src.saathy.chunking import EmailChunker

chunker = EmailChunker(max_chunk_size=512, overlap=50)
chunks = chunker.chunk(email_content)
```

**Features:**
- Header/body separation
- Attachment handling
- Thread preservation
- Metadata extraction

## Content Type Detection

The system automatically detects content types using pattern matching and file extensions:

```python
from src.saathy.chunking import ContentTypeDetector

detector = ContentTypeDetector()

# Detect from content
content_type = detector.detect_content_type(content)

# Detect from file extension
content_type = detector.detect_content_type(content, file_extension=".py")
```

**Supported Content Types:**
- `TEXT`: General text content
- `CODE`: Source code files
- `DOCUMENT`: Structured documents
- `MEETING`: Meeting transcripts
- `GIT_COMMIT`: Git commits
- `SLACK_MESSAGE`: Slack messages
- `EMAIL`: Email content

## Quality Analysis

### Chunk Quality Metrics

```python
from src.saathy.chunking import ChunkAnalyzer

analyzer = ChunkAnalyzer()
metrics = analyzer.analyze_chunks(chunks, original_content)

print(f"Quality Score: {metrics.quality_score}")
print(f"Coverage Ratio: {metrics.coverage_ratio}")
print(f"Semantic Coherence: {metrics.semantic_coherence}")
print(f"Overlap Efficiency: {metrics.overlap_efficiency}")
print(f"Content Loss: {metrics.content_loss}")
```

**Quality Metrics:**
- **Coverage Ratio**: Percentage of original content captured
- **Semantic Coherence**: Similarity between adjacent chunks
- **Overlap Efficiency**: Optimal use of overlap
- **Content Loss**: Information lost during chunking
- **Quality Score**: Overall weighted quality assessment

### Statistical Analysis

```python
stats = analyzer.get_chunk_statistics(chunks)

print(f"Size Statistics: {stats['size_statistics']}")
print(f"Type Distribution: {stats['type_distribution']}")
print(f"Overlap Statistics: {stats['overlap_statistics']}")
```

## Visualization

### Chunk Analysis Plots

```python
from src.saathy.chunking import ChunkVisualizer

visualizer = ChunkVisualizer()

# Size distribution
visualizer.plot_chunk_size_distribution(chunks, save_path="size_dist.png")

# Overlap analysis
visualizer.plot_chunk_overlap_analysis(chunks, save_path="overlap_analysis.png")

# Type distribution
visualizer.plot_chunk_type_distribution(chunks, save_path="type_dist.png")

# Quality metrics radar chart
visualizer.plot_quality_metrics(metrics, save_path="quality_radar.png")

# Chunk boundaries
visualizer.visualize_chunk_boundaries(chunks, original_content, save_path="boundaries.png")
```

### Comprehensive Reports

```python
# Generate detailed analysis report
visualizer.create_chunk_report(chunks, original_content, "chunk_analysis.json")
```

## Caching & Performance

### Chunk Caching

```python
from src.saathy.chunking import ChunkCache

cache = ChunkCache(ttl=3600)  # 1 hour TTL

# Cache chunks
cache.set(content_hash, chunks)

# Retrieve cached chunks
cached_chunks = cache.get(content_hash)

# Get cache statistics
stats = cache.get_stats()
```

### Performance Optimization

```python
# Enable parallel processing
config = ChunkingConfig(
    parallel_processing=True,
    max_workers=4
)

processor = ChunkingProcessor(config)

# Process multiple files in parallel
chunks_list = processor.chunk_files(file_paths)
```

## Integration with Embedding System

The chunking system integrates seamlessly with the embedding service:

```python
from src.saathy.embedding import EmbeddingService
from src.saathy.chunking import ChunkingProcessor

# Initialize services
embedding_service = EmbeddingService()
chunking_processor = ChunkingProcessor()

# Process and embed content
content = "Your content here..."
chunks = chunking_processor.chunk_content(content)

# Generate embeddings for chunks
embeddings = []
for chunk in chunks:
    embedding = embedding_service.embed_text(chunk.content)
    embeddings.append(embedding)
```

## Configuration Options

### ChunkingConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_chunk_size` | int | 512 | Maximum chunk size in characters |
| `overlap` | int | 50 | Overlap between chunks |
| `min_chunk_size` | int | 50 | Minimum chunk size |
| `preserve_context` | bool | True | Preserve context across boundaries |
| `enable_caching` | bool | True | Enable chunk caching |
| `cache_ttl` | int | 3600 | Cache TTL in seconds |
| `parallel_processing` | bool | False | Enable parallel processing |
| `max_workers` | int | 4 | Maximum parallel workers |

### Strategy-Specific Parameters

Each chunking strategy supports additional parameters:

```python
# Semantic chunking with custom parameters
semantic_chunker = SemanticChunker(
    max_chunk_size=512,
    overlap=50,
    min_chunk_size=50,
    preserve_context=True
)

# Code chunking with language detection
code_chunker = CodeChunker(
    max_chunk_size=512,
    overlap=50,
    min_chunk_size=50,
    preserve_context=True
)
```

## Best Practices

### 1. **Choose Appropriate Strategy**
- Use `SemanticChunker` for natural language text
- Use `CodeChunker` for source code
- Use `DocumentChunker` for structured documents
- Use `MeetingChunker` for conversation logs

### 2. **Optimize Chunk Sizes**
- Balance between retrieval precision and context
- Consider embedding model token limits
- Test different sizes for your use case

### 3. **Configure Overlap**
- 10-20% overlap for most use cases
- Higher overlap for critical context preservation
- Lower overlap for efficiency

### 4. **Enable Caching**
- Use caching for repeated content
- Set appropriate TTL based on content volatility
- Monitor cache performance

### 5. **Validate Quality**
- Use quality metrics to evaluate chunking
- Adjust parameters based on quality scores
- Monitor content loss and coverage

## Troubleshooting

### Common Issues

**1. Chunks too small**
```python
# Increase minimum chunk size
config = ChunkingConfig(min_chunk_size=100)
```

**2. Poor semantic coherence**
```python
# Use semantic chunking strategy
chunker = SemanticChunker(max_chunk_size=512, overlap=50)
```

**3. High content loss**
```python
# Increase overlap and check chunking strategy
config = ChunkingConfig(overlap=100, preserve_context=True)
```

**4. Performance issues**
```python
# Enable caching and parallel processing
config = ChunkingConfig(
    enable_caching=True,
    parallel_processing=True,
    max_workers=4
)
```

### Debugging Tools

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Generate analysis report
visualizer.create_chunk_report(chunks, original_content, "debug_report.json")

# Check cache statistics
cache_stats = processor.cache.get_stats()
print(f"Cache hit rate: {cache_stats['valid_entries'] / cache_stats['total_entries']}")
```

## API Reference

### ChunkingProcessor

Main processor class for content chunking.

```python
class ChunkingProcessor:
    def __init__(self, config: Optional[ChunkingConfig] = None)
    def chunk_content(self, content: str, content_type: Optional[ContentType] = None, 
                     file_extension: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]
    def chunk_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]
    def get_chunking_stats(self) -> Dict[str, Any]
```

### Chunk

Represents a content chunk with metadata.

```python
@dataclass
class Chunk:
    content: str
    start_index: int
    end_index: int
    chunk_type: str
    metadata: ChunkMetadata
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    context_before: str = ""
    context_after: str = ""
```

### ChunkMetadata

Enhanced metadata for chunks.

```python
@dataclass
class ChunkMetadata:
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
```

## Examples

### Complete Workflow Example

```python
from src.saathy.chunking import ChunkingProcessor, ChunkAnalyzer, ChunkVisualizer
from src.saathy.embedding import EmbeddingService

# Initialize services
processor = ChunkingProcessor()
analyzer = ChunkAnalyzer()
visualizer = ChunkVisualizer()
embedding_service = EmbeddingService()

# Process content
content = "Your content here..."
chunks = processor.chunk_content(content)

# Analyze quality
metrics = analyzer.analyze_chunks(chunks, content)
print(f"Quality Score: {metrics.quality_score:.2f}")

# Generate embeddings
embeddings = []
for chunk in chunks:
    embedding = embedding_service.embed_text(chunk.content)
    embeddings.append(embedding)

# Create visualization
visualizer.plot_quality_metrics(metrics, save_path="quality_analysis.png")

# Generate report
visualizer.create_chunk_report(chunks, content, "final_report.json")
```

### Batch Processing Example

```python
import os
from pathlib import Path

# Process multiple files
file_paths = list(Path("documents/").glob("*.md"))
all_chunks = []

for file_path in file_paths:
    chunks = processor.chunk_file(str(file_path))
    all_chunks.extend(chunks)

# Analyze batch results
metrics = analyzer.analyze_chunks(all_chunks, "batch_content")
print(f"Total chunks: {metrics.total_chunks}")
print(f"Average quality: {metrics.quality_score:.2f}")
```

This comprehensive chunking system provides the foundation for optimal vector search performance across diverse content types while maintaining semantic coherence and context preservation. 