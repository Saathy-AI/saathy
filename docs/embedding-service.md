# Embedding Service Documentation

The embedding service provides multi-model support for generating vector embeddings from various content types. It's designed to be flexible, performant, and production-ready with comprehensive monitoring and caching capabilities.

## 🏗️ Architecture

```
src/saathy/embedding/
├── __init__.py     # Embedding package exports
├── models.py       # Model registry and management
├── preprocessing.py # Content preprocessing
├── chunking.py     # Content chunking strategies
└── service.py      # Main embedding service
```

## 🔤 Supported Models

### Local Models (SentenceTransformers)
- **all-MiniLM-L6-v2**: Fast and efficient general-purpose model (384 dimensions)
  - Performance Score: 0.85
  - Download Size: ~90MB
  - Best for: Real-time operations, general text
- **all-mpnet-base-v2**: High-quality general-purpose model (768 dimensions)
  - Performance Score: 0.92
  - Download Size: ~420MB
  - Best for: High-quality embeddings, offline processing
- **microsoft/codebert-base**: Code-specialized model (768 dimensions)
  - Performance Score: 0.88
  - Download Size: ~500MB
  - Best for: Code analysis, repository processing

### Cloud Models (OpenAI)
- **text-embedding-ada-002**: OpenAI embeddings (1536 dimensions)
  - Performance Score: 0.95
  - Requires: OpenAI API key
  - Best for: Premium quality, large context windows

## 📝 Content Types

### Text Content
- **Preprocessing**: Whitespace cleaning, newline normalization, language detection
- **Quality Metrics**: Length ratio, character diversity, word count
- **Use Cases**: General documents, articles, reports

### Code Content
- **Preprocessing**: Comment removal, function extraction, whitespace normalization
- **Language Support**: Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala
- **Quality Metrics**: Function density, code complexity, length preservation
- **Use Cases**: Repository analysis, code documentation, function similarity

### Meeting Content
- **Preprocessing**: Speaker extraction, timestamp preservation, transcript cleaning
- **Features**: Speaker identification, topic extraction, participant counting
- **Quality Metrics**: Speaker diversity, content length
- **Use Cases**: Meeting transcripts, conversation analysis

### Image Content
- **Preprocessing**: OCR text extraction, visual context extraction
- **Requirements**: pytesseract and Pillow (optional)
- **Features**: Text extraction, image metadata analysis
- **Quality Metrics**: Text extraction success, visual context availability
- **Use Cases**: Document images, screenshots, diagrams

## ✂️ Chunking Strategies

### Fixed Size Chunking
- **Description**: Simple fixed-size chunks with overlap
- **Best For**: Uniform content, simple processing
- **Parameters**: `max_chunk_size`, `overlap`
- **Example**: 512 characters with 50 character overlap

### Semantic Chunking
- **Description**: Sentence-based chunking preserving meaning
- **Best For**: Natural language content, document processing
- **Features**: Sentence boundary detection, meaning preservation
- **Example**: Breaks at sentence endings, maintains context

### Document Aware Chunking
- **Description**: Respects document structure and headers
- **Best For**: Structured documents, markdown, technical docs
- **Features**: Header detection, section preservation
- **Example**: Keeps sections together, respects document hierarchy

### Code Chunking
- **Description**: Function-based chunking for code content
- **Best For**: Programming code, repository analysis
- **Features**: Function boundary detection, language-specific patterns
- **Example**: Keeps functions together, respects code structure

## 🚀 API Usage

### Single Text Embedding

```bash
curl -X POST "http://localhost:8000/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "content_type": "text",
    "model_name": "all-MiniLM-L6-v2",
    "quality": "balanced",
    "metadata": {
      "source": "user_input",
      "language": "en"
    }
  }'
```

**Response:**
```json
{
  "embeddings": [[0.1, 0.2, 0.3, ...]],
  "model_name": "all-MiniLM-L6-v2",
  "content_type": "text",
  "processing_time": 0.045,
  "quality_score": 0.85,
  "metadata": {
    "source": "user_input",
    "language": "en"
  }
}
```

### Batch Embedding

```bash
curl -X POST "http://localhost:8000/embed/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Text 1", "Text 2", "Text 3"],
    "content_type": "text",
    "quality": "fast"
  }'
```

### Code Embedding

```bash
curl -X POST "http://localhost:8000/embed/code" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(): return \"world\"",
    "language": "python",
    "metadata": {
      "file_path": "src/example.py",
      "function_name": "hello"
    }
  }'
```

### Get Available Models

```bash
curl "http://localhost:8000/embed/models"
```

**Response:**
```json
{
  "available_models": ["all-MiniLM-L6-v2", "all-mpnet-base-v2"],
  "model_details": {
    "all-MiniLM-L6-v2": {
      "name": "all-MiniLM-L6-v2",
      "dimensions": 384,
      "max_context_length": 256,
      "model_type": "local",
      "performance_score": 0.85,
      "is_loaded": true,
      "device": "cpu"
    }
  }
}
```

### Get Metrics

```bash
curl "http://localhost:8000/embed/metrics"
```

**Response:**
```json
{
  "total_models_used": 2,
  "total_content_types": 3,
  "total_errors": 0,
  "model_performance": {
    "all-MiniLM-L6-v2": {
      "usage_count": 150,
      "avg_processing_time": 0.045,
      "error_rate": 0.0
    }
  },
  "content_type_performance": {
    "text": {
      "total_processed": 100,
      "avg_quality_score": 0.85,
      "avg_word_count": 25.5
    }
  }
}
```

### Cache Management

```bash
# Get cache statistics
curl "http://localhost:8000/embed/cache/stats"

# Clear cache
curl -X DELETE "http://localhost:8000/embed/cache"
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_EMBEDDING_MODEL` | Default embedding model | `all-MiniLM-L6-v2` |
| `EMBEDDING_CACHE_SIZE` | Maximum cached embeddings | `1000` |
| `EMBEDDING_CACHE_TTL` | Cache TTL in seconds | `3600` |
| `EMBEDDING_BATCH_SIZE` | Batch size for embeddings | `32` |
| `ENABLE_GPU_EMBEDDINGS` | Enable GPU acceleration | `true` |
| `EMBEDDING_QUALITY_PREFERENCE` | Quality preference (fast/balanced/high) | `balanced` |

### Quality Preferences

- **fast**: Optimized for speed, smaller models
- **balanced**: Good balance of speed and quality
- **high**: Optimized for quality, larger models

## 🔧 Advanced Usage

### Python Client Example

```python
import asyncio
from saathy.embedding.service import get_embedding_service

async def main():
    # Get embedding service
    service = await get_embedding_service()

    # Single text embedding
    result = await service.embed_text(
        text="Hello world",
        content_type="text",
        quality="balanced"
    )
    print(f"Embedding shape: {result.embeddings.shape}")

    # Batch embedding
    texts = ["Text 1", "Text 2", "Text 3"]
    results = await service.embed_batch(texts, "text")
    print(f"Processed {len(results)} texts")

    # Code embedding
    code_result = await service.embed_code(
        code="def hello(): return 'world'",
        language="python"
    )
    print(f"Code embedding quality: {code_result.quality_score}")

asyncio.run(main())
```

### Custom Preprocessing

```python
from saathy.embedding.preprocessing import PreprocessingPipeline

pipeline = PreprocessingPipeline()

# Custom text preprocessing
result = pipeline.preprocess(
    content="Your text here",
    content_type="text",
    metadata={"source": "custom"}
)

print(f"Quality score: {result.quality_score}")
print(f"Preprocessing steps: {result.preprocessing_steps}")
```

### Custom Chunking

```python
from saathy.embedding.chunking import ChunkingPipeline

pipeline = ChunkingPipeline()

# Chunk content with custom parameters
chunks = pipeline.chunk(
    content="Your long content here...",
    strategy="semantic",
    max_chunk_size=512,
    overlap=50
)

print(f"Created {len(chunks)} chunks")

# Validate chunks
validation = pipeline.validate_chunks(chunks, "Your long content here...")
print(f"Chunks valid: {validation['valid']}")
```

## 📊 Performance Optimization

### Caching Strategy
- **In-Memory Cache**: Fast access to recently used embeddings
- **TTL Management**: Automatic expiration of old embeddings
- **LRU Eviction**: Least recently used items removed when cache is full
- **Content Hashing**: Efficient cache key generation

### Batch Processing
- **Configurable Batch Size**: Optimize for your hardware
- **Parallel Processing**: Async processing of multiple texts
- **Memory Management**: Efficient handling of large batches

### GPU Acceleration
- **Automatic Detection**: GPU availability detection
- **Fallback Support**: CPU fallback when GPU unavailable
- **Memory Optimization**: Efficient GPU memory usage

## 🐛 Troubleshooting

### Common Issues

**Model Loading Failures**
```bash
# Check if models are available
curl "http://localhost:8000/embed/models"

# Check service logs for model loading errors
docker-compose logs api
```

**Performance Issues**
```bash
# Check metrics for bottlenecks
curl "http://localhost:8000/embed/metrics"

# Adjust batch size if needed
export EMBEDDING_BATCH_SIZE=16
```

**Memory Issues**
```bash
# Reduce cache size
export EMBEDDING_CACHE_SIZE=500

# Clear cache
curl -X DELETE "http://localhost:8000/embed/cache"
```

### Debug Mode

Enable debug logging for detailed information:

```bash
export LOG_LEVEL=DEBUG
export DEBUG=true
```

## 🔮 Future Enhancements

### Planned Features
- **Multimodal Embeddings**: Image and text combined embeddings
- **Custom Model Support**: User-defined model registration
- **Advanced Caching**: Redis-based distributed caching
- **Streaming Processing**: Real-time embedding generation
- **Model Fine-tuning**: Custom model training capabilities

### Integration Points
- **Vector Search**: Integration with similarity search
- **Document Processing**: Automated document ingestion
- **Real-time Updates**: Live embedding updates
- **Analytics**: Advanced usage analytics and insights
