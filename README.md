# Saathy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)

A FastAPI-based application foundation for building a personal AI copilot, currently in early development with production-ready infrastructure.

## 🚀 Current Capabilities

**Implemented Features:**
- **FastAPI Web Framework**: Production-ready API with health monitoring endpoints
- **Vector Database Integration**: Qdrant client setup with health check connectivity
- **Embedding Service**: Multi-model embedding with support for text, code, and multimodal content
- **Content Preprocessing**: Specialized preprocessing for different content types (text, code, meetings, images)
- **Chunking Strategies**: Multiple chunking strategies (fixed, semantic, document-aware, code)
- **Observability**: OpenTelemetry tracing and structured logging with Jaeger integration
- **Production Deployment**: Complete Docker Compose setup with Nginx, monitoring stack
- **Development Infrastructure**: Poetry dependency management, comprehensive testing, code quality tools
- **Configuration Management**: Pydantic Settings with environment variable support

**API Endpoints:**
- `GET /healthz` - Health check with Qdrant connectivity verification
- `GET /readyz` - Readiness check for service availability
- `GET /config` - Non-sensitive configuration display
- `POST /embed` - Generate embeddings for single text
- `POST /embed/batch` - Generate embeddings for multiple texts
- `POST /embed/code` - Generate embeddings for code content
- `GET /embed/models` - List available embedding models
- `GET /embed/metrics` - Get embedding service metrics
- `GET /embed/cache/stats` - Get cache statistics
- `DELETE /embed/cache` - Clear embedding cache

## 🏗️ Architecture

```
src/saathy/
├── __init__.py          # Package initialization
├── api.py              # FastAPI application with health endpoints
├── config.py           # Pydantic Settings configuration
├── main.py             # Server entrypoint
├── scheduler.py        # APScheduler setup (basic)
├── telemetry.py        # OpenTelemetry tracing configuration
├── embedding/          # Embedding service
│   ├── __init__.py     # Embedding package exports
│   ├── models.py       # Model registry and management
│   ├── preprocessing.py # Content preprocessing
│   ├── chunking.py     # Content chunking strategies
│   └── service.py      # Main embedding service
└── vector/
    └── repository.py   # Qdrant client wrapper with health check
```

**Production Stack:**
- **Application**: FastAPI with Uvicorn/Gunicorn
- **Vector Database**: Qdrant v1.9.2
- **Reverse Proxy**: Nginx with SSL termination
- **Monitoring**: Prometheus + Grafana + OpenTelemetry Collector
- **Containerization**: Docker with multi-stage builds

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Poetry (for development)

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd saathy
   ```

2. **Install dependencies with Poetry:**
   ```bash
   poetry install
   ```

3. **Set up environment variables:**
   ```bash
   cp docs/env.example .env
   # Edit .env with your configuration
   ```

4. **Run with Docker Compose (development):**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

5. **Or run locally with Poetry:**
   ```bash
   poetry run uvicorn saathy.api:app --reload --host 0.0.0.0 --port 8000
   ```

### Production Deployment

1. **Set up secrets:**
   ```bash
   mkdir -p secrets
   echo "your-qdrant-api-key" > secrets/qdrant_api_key
   echo "your-openai-api-key" > secrets/openai_api_key
   echo "your-grafana-password" > secrets/grafana_admin_password
   ```

2. **Deploy with production compose:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Or use the deployment script:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh --init  # First time setup
   ./deploy.sh         # Regular deployment
   ```

## 🧪 Development

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=saathy

# Run specific test file
poetry run pytest tests/healthz_test.py
```

### Code Quality
```bash
# Format code
poetry run ruff format .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy src/
```

### Pre-commit Hooks
The project includes pre-commit hooks for automatic code formatting and linting:
- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatting
- **isort**: Import sorting
```bash
poetry run pre-commit run --all-files
```

### Docker Development
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f api

# Rebuild and restart
docker-compose -f docker-compose.dev.yml up -d --build
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `Saathy` |
| `ENVIRONMENT` | Environment (dev/staging/prod) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `QDRANT_URL` | Qdrant vector database URL | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant API key | `None` |
| `OPENAI_API_KEY` | OpenAI API key | `None` |
| `DEFAULT_EMBEDDING_MODEL` | Default embedding model | `all-MiniLM-L6-v2` |
| `EMBEDDING_CACHE_SIZE` | Maximum cached embeddings | `1000` |
| `EMBEDDING_CACHE_TTL` | Cache TTL in seconds | `3600` |
| `EMBEDDING_BATCH_SIZE` | Batch size for embeddings | `32` |
| `ENABLE_GPU_EMBEDDINGS` | Enable GPU acceleration | `true` |
| `EMBEDDING_QUALITY_PREFERENCE` | Quality preference (fast/balanced/high) | `balanced` |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing | `false` |
| `HOST` | Server host address | `0.0.0.0` |
| `PORT` | Server port | `8000` |

### Production Configuration

The production setup includes:
- **Nginx**: Reverse proxy with SSL termination
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **OpenTelemetry Collector**: Distributed tracing
- **Health Checks**: Container health monitoring
- **Logging**: Structured JSON logging with rotation

## 🔤 Embedding Service

The embedding service provides multi-model support for generating vector embeddings from various content types including text, code, meetings, and images. It features intelligent preprocessing, multiple chunking strategies, caching, and comprehensive monitoring.

**📖 [Complete Embedding Service Documentation](docs/embedding-service.md)**

### Quick Start

```bash
# Single text embedding
curl -X POST "http://localhost:8000/embed" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "content_type": "text"}'

# Get available models
curl "http://localhost:8000/embed/models"

# Get service metrics
curl "http://localhost:8000/embed/metrics"
```

### Key Features
- **Multi-Model Support**: Local SentenceTransformers + OpenAI API
- **Content-Specific Processing**: Text, code, meetings, images
- **Multiple Chunking Strategies**: Fixed, semantic, document-aware, code
- **Performance Optimization**: Caching, batch processing, GPU detection
- **Comprehensive Monitoring**: Processing times, error rates, quality scores

## 📊 Monitoring

### Health Checks
- **Application**: `GET /healthz` - Checks Qdrant connectivity
- **Readiness**: `GET /readyz` - Service readiness status
- **Configuration**: `GET /config` - Non-sensitive config display

### Observability
- **Tracing**: OpenTelemetry with Jaeger integration
- **Logging**: Structured logging with correlation IDs
- **Metrics**: Prometheus metrics collection
- **Dashboards**: Grafana monitoring dashboards

## 🚧 Development Status

**Current State**: Early Development
- ✅ Foundation infrastructure complete
- ✅ Production deployment pipeline
- ✅ Health monitoring and observability
- ✅ Vector database connectivity
- 🔄 Core AI features in development
- 📋 Advanced features planned

**What's Working:**
- FastAPI application with health endpoints
- Qdrant vector database connection
- OpenTelemetry tracing and logging
- Docker production deployment
- Comprehensive testing framework
- Code quality and formatting tools

**What's Not Yet Implemented:**
- Vector search and similarity matching
- Git repository integration
- Slack or other platform connectors
- Meeting transcription capabilities
- CLI tools and utilities

## 🗺️ Development Roadmap

### Phase 1: Foundation ✅
- [x] FastAPI application structure
- [x] Vector database integration
- [x] Observability and monitoring
- [x] Production deployment pipeline

### Phase 2: Core Features (In Progress)
- [x] Vector embedding service
- [x] Document processing and chunking
- [ ] Vector search and similarity matching
- [ ] Basic LLM integration
- [ ] Repository connectors

### Phase 3: Advanced Features (Planned)
- [ ] Multi-modal content support
- [ ] Advanced search algorithms
- [ ] Real-time collaboration
- [ ] Advanced analytics

### Phase 4: Platform Integration (Future)
- [ ] Slack integration
- [ ] Git platform connectors
- [ ] Notion integration
- [ ] Meeting transcription

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the existing code style (Ruff + Black)
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the test files for usage examples

---

**Note**: This is an early-stage project. The foundation infrastructure is complete and production-ready, but core AI features are still in development.
