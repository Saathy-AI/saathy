# Saathy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)

A FastAPI-based AI copilot that proactively watches your work across platforms and suggests actionable next steps with full context. While competitors make you ask questions, Saathy tells you what to do next.

## ✨ Core Value Proposition

**Proactive Action Intelligence**: Saathy's V1 core differentiator is its ability to:
- **Watch** your activity across Slack, GitHub, and Notion in real-time
- **Correlate** related events across platforms using advanced similarity algorithms
- **Synthesize** context from multi-platform activity into coherent insights
- **Generate** specific, actionable recommendations using GPT-4o
- **Deliver** timely suggestions when you need them most

## 🚀 Current Capabilities

**Implemented Features:**

**🧠 Proactive Intelligence System (V1 Core):**
- **Real-Time Event Streaming**: WebSocket/webhook monitoring of Slack, GitHub, and Notion
- **Cross-Platform Event Correlation**: Intelligent linking of related activities using similarity scoring
- **Context Synthesis**: AI-powered analysis of correlated events to extract insights and urgency signals
- **GPT-4 Action Generation**: Specific, actionable recommendations with direct platform links
- **Smart Timing**: Proactive delivery based on user context and urgency

**🏗️ Foundation Infrastructure:**
- **FastAPI Web Framework**: Production-ready API with comprehensive health monitoring
- **Vector Database Integration**: Qdrant client with health check connectivity and repository layer
- **Advanced Chunking System**: Modular chunking strategies for different content types (text, code, documents, emails, meetings, Slack messages, Git commits)
- **Connector Framework**: Extensible connector system with GitHub and Slack integrations
- **Content Processing Pipeline**: Intelligent content preprocessing, chunking, and vector storage
- **Observability**: OpenTelemetry tracing and structured logging with Jaeger integration
- **Production Deployment**: Complete Docker Compose setup with Nginx, monitoring stack
- **Development Infrastructure**: Poetry dependency management, comprehensive testing, code quality tools
- **Configuration Management**: Pydantic Settings with environment variable support

**API Endpoints:**

**🧠 Intelligence & Actions:**
- `GET /actions/user/{user_id}` - Get proactive action recommendations for user
- `POST /actions/{action_id}/complete` - Mark action as completed
- `POST /actions/{action_id}/feedback` - Provide feedback on action usefulness
- `GET /correlations/user/{user_id}` - Get event correlations for user
- `GET /events/user/{user_id}` - Get recent events across platforms

**Health & Configuration:**
- `GET /healthz` - Health check with Qdrant connectivity verification
- `GET /readyz` - Readiness check for service availability
- `GET /config` - Non-sensitive configuration display

**GitHub Connector:**
- `POST /webhooks/github` - GitHub webhook endpoint for repository events (enhanced for streaming)
- `GET /connectors/github/status` - GitHub connector status and metrics
- `POST /connectors/github/sync` - Manual repository synchronization

**Slack Connector:**
- `GET /connectors/slack/status` - Slack connector status and metrics
- `POST /connectors/slack/start` - Start Slack connector (enhanced for real-time streaming)
- `POST /connectors/slack/stop` - Stop Slack connector
- `GET /connectors/slack/channels` - List available Slack channels
- `POST /connectors/slack/process` - Manually process Slack content

## 🏗️ Architecture

```
src/saathy/
├── __init__.py          # Package initialization
├── api.py              # FastAPI application with all endpoints
├── config.py           # Pydantic Settings configuration
├── scheduler.py        # APScheduler setup for background tasks
├── telemetry.py        # OpenTelemetry tracing configuration
├── streaming/          # 🧠 Real-time event streaming & correlation
│   ├── models/         # Event data models (Slack, GitHub, Notion)
│   │   └── events.py   # Pydantic models for standardized events
│   ├── event_manager.py        # Central event coordination & Redis storage
│   ├── event_correlator.py     # Cross-platform event correlation logic
│   ├── slack_stream.py         # Real-time Slack WebSocket streaming
│   ├── github_webhook.py       # Enhanced GitHub webhook processing
│   └── notion_poller.py        # Notion change detection via polling
├── intelligence/       # 🤖 AI-powered context synthesis & action generation
│   ├── models/         # Intelligence data models
│   │   └── actions.py  # Action and context bundle models
│   ├── prompts/        # GPT-4 prompt templates
│   │   └── action_generation.py  # Sophisticated prompts for action creation
│   ├── context_synthesizer.py   # Multi-platform context synthesis
│   └── action_generator.py      # GPT-4 powered action generation
├── chunking/           # Advanced chunking system
│   ├── __init__.py     # Chunking package exports
│   ├── processor.py    # Main chunking processor
│   ├── strategies/     # Chunking strategies
│   │   ├── base.py     # Base strategy interface
│   │   ├── fixed_size.py # Fixed-size chunking
│   │   ├── semantic.py # Semantic chunking
│   │   ├── document.py # Document-aware chunking
│   │   ├── code.py     # Code-specific chunking
│   │   ├── email.py    # Email chunking
│   │   ├── meeting.py  # Meeting transcript chunking
│   │   ├── slack_message.py # Slack message chunking
│   │   └── git_commit.py # Git commit chunking
│   ├── core/           # Core chunking components
│   │   ├── interfaces.py # Abstract interfaces
│   │   ├── models.py   # Data models
│   │   └── exceptions.py # Custom exceptions
│   ├── utils/          # Utility modules
│   │   ├── chunk_cache.py # Caching utilities
│   │   ├── chunk_merger.py # Chunk merging logic
│   │   ├── content_detector.py # Content type detection
│   │   ├── hash_utils.py # Hashing utilities
│   │   └── quality_validator.py # Quality validation
│   └── analysis/       # Analysis tools
│       ├── analyzer.py # Chunk analysis
│       └── visualizer.py # Visualization tools
├── connectors/         # Connector framework
│   ├── __init__.py     # Connector exports
│   ├── base.py         # Base connector interface
│   ├── github_connector.py # GitHub integration
│   ├── slack_connector.py # Slack integration
│   └── content_processor.py # Content processing pipeline
├── embedding/          # Embedding service
│   ├── __init__.py     # Embedding package exports
│   ├── models.py       # Model registry and management
│   ├── preprocessing.py # Content preprocessing
│   ├── chunking.py     # Legacy chunking (deprecated)
│   └── service.py      # Main embedding service
└── vector/             # Vector database layer
    ├── __init__.py     # Vector package exports
    ├── client.py       # Qdrant client wrapper
    ├── repository.py   # Repository pattern implementation
    ├── models.py       # Vector data models
    ├── exceptions.py   # Vector-specific exceptions
    └── metrics.py      # Vector operation metrics
```

**Production Stack:**
- **Application**: FastAPI with Uvicorn/Gunicorn
- **Vector Database**: Qdrant v1.9.2
- **Reverse Proxy**: Nginx with SSL termination and rate limiting
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
| `GITHUB_TOKEN` | GitHub personal access token | `None` |
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook secret | `None` |
| `GITHUB_REPOSITORIES` | Comma-separated list of repositories | `None` |
| `SLACK_BOT_TOKEN` | Slack bot token (xoxb-...) | `None` |
| `SLACK_APP_TOKEN` | Slack app-level token (xapp-...) | `None` |
| `SLACK_CHANNELS` | Comma-separated list of channel IDs | `None` |
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
- **Nginx**: Reverse proxy with SSL termination and rate limiting
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **OpenTelemetry Collector**: Distributed tracing
- **Health Checks**: Container health monitoring
- **Logging**: Structured JSON logging with rotation

## 🔗 Connector System

Saathy includes a flexible connector framework for integrating with external platforms and services.

### GitHub Connector

The GitHub connector processes repository events via webhooks and provides manual synchronization capabilities.

**Features:**
- Webhook event processing (pushes, pull requests, issues)
- Manual repository synchronization
- Content extraction and processing
- Git commit history analysis

**Setup:**
1. Create a GitHub personal access token
2. Configure webhook secret
3. Add repositories to monitor
4. Set up webhook URL: `https://your-domain.com/webhooks/github`

**📖 [GitHub Connector Documentation](docs/github-setup.md)**

### Slack Connector

The Slack connector provides real-time message processing and content extraction from Slack channels.

**Features:**
- Real-time message processing
- Channel monitoring and management
- Content extraction and chunking
- Thread and reply handling

**Setup:**
1. Create a Slack app with appropriate permissions
2. Configure bot token and app token
3. Add channels to monitor
4. Start the connector via API

**📖 [Slack Connector Documentation](docs/slack-setup.md)**

## 📊 Chunking System

Saathy features a sophisticated chunking system with multiple strategies optimized for different content types.

### Available Strategies

- **Fixed Size**: Token/character-based chunking with overlap
- **Semantic**: Content-aware chunking based on semantic boundaries
- **Document**: Document structure-aware chunking
- **Code**: Language-specific code chunking with function extraction
- **Email**: Email-specific chunking with header/body separation
- **Meeting**: Meeting transcript chunking with speaker detection
- **Slack Message**: Slack-specific message chunking
- **Git Commit**: Git commit history chunking

### Key Features

- **Content Type Detection**: Automatic detection of content type
- **Quality Validation**: Chunk quality metrics and validation
- **Caching**: Intelligent caching with content hashing
- **Merging**: Small chunk merging for optimal size
- **Context Preservation**: Overlap and context maintenance
- **Performance Optimization**: Batch processing and parallel execution

**📖 [Chunking System Documentation](docs/chunking-system.md)**

## 🔤 Embedding Service

The embedding service provides multi-model support for generating vector embeddings from various content types.

**📖 [Complete Embedding Service Documentation](docs/embedding-service.md)**

### Quick Start

```bash
# Get available models
curl "http://localhost:8000/embed/models"

# Get service metrics
curl "http://localhost:8000/embed/metrics"
```

### Key Features
- **Multi-Model Support**: Local SentenceTransformers + OpenAI API
- **Content-Specific Processing**: Text, code, meetings, images
- **Performance Optimization**: Caching, batch processing, GPU detection
- **Comprehensive Monitoring**: Processing times, error rates, quality scores

## 📊 Monitoring

### Health Checks
- **Application**: `GET /healthz` - Checks Qdrant connectivity
- **Readiness**: `GET /readyz` - Service readiness status
- **Configuration**: `GET /config` - Non-sensitive config display

### Connector Monitoring
- **GitHub**: `GET /connectors/github/status` - GitHub connector health
- **Slack**: `GET /connectors/slack/status` - Slack connector health

### Observability
- **Tracing**: OpenTelemetry with Jaeger integration
- **Logging**: Structured logging with correlation IDs
- **Metrics**: Prometheus metrics collection
- **Dashboards**: Grafana monitoring dashboards

## 🚧 Development Status

**Current State**: Active Development
- ✅ Foundation infrastructure complete
- ✅ Production deployment pipeline
- ✅ Health monitoring and observability
- ✅ Vector database connectivity
- ✅ Advanced chunking system
- ✅ Connector framework with GitHub and Slack
- ✅ Content processing pipeline
- 🔄 Vector search and similarity matching
- 📋 Advanced AI features planned

**What's Working:**
- FastAPI application with comprehensive endpoints
- Qdrant vector database connection
- OpenTelemetry tracing and logging
- Docker production deployment
- Comprehensive testing framework
- Code quality and formatting tools
- Advanced chunking system with multiple strategies
- GitHub and Slack connector integrations
- Content processing and storage pipeline
- **🧠 Proactive Intelligence System**: Real-time event streaming, correlation, and AI-powered action generation

## 🧪 Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src/saathy --cov-report=html

# Run specific test categories
poetry run pytest tests/streaming/        # Streaming pipeline tests
poetry run pytest tests/intelligence/     # AI intelligence tests
poetry run pytest tests/test_integration.py  # End-to-end pipeline tests
poetry run pytest tests/test_connectors/  # Connector tests
poetry run pytest tests/test_api/         # API tests

# Run tests in watch mode during development
poetry run ptw -- --testmon
```

### Test Coverage

The comprehensive test suite includes:

**🧠 Streaming Intelligence Tests:**
- **Event Models**: Validation, serialization, platform-specific fields
- **Event Manager**: Redis storage, queuing, user timelines, error handling
- **Event Correlator**: Similarity algorithms, correlation groups, cross-platform linking
- **Context Synthesizer**: Platform organization, insight extraction, narrative generation
- **Action Generator**: GPT-4 integration, validation, link enhancement, daily limits
- **Integration Tests**: End-to-end pipeline from events to actions

**🏗️ Foundation Tests:**
- **Connectors**: GitHub and Slack integration, webhook processing
- **API Endpoints**: Health checks, configuration, connector management
- **Chunking System**: Content processing and vector storage
- **Infrastructure**: Redis connectivity, telemetry, error handling

### Test Fixtures and Mocking

Tests use comprehensive mocking for external dependencies:
- **Redis**: Async Redis operations with realistic response simulation
- **OpenAI API**: GPT-4 responses for action generation and validation
- **Platform APIs**: Slack, GitHub, and Notion API responses
- **WebSocket Connections**: Slack Socket Mode event simulation

**What's Not Yet Implemented:**
- Vector search and similarity matching endpoints
- Advanced LLM integration
- Real-time collaboration features
- Advanced analytics and insights

## 🗺️ Development Roadmap

### Phase 1: Foundation ✅
- [x] FastAPI application structure
- [x] Vector database integration
- [x] Observability and monitoring
- [x] Production deployment pipeline

### Phase 2: Core Features ✅
- [x] Advanced chunking system
- [x] Connector framework
- [x] GitHub and Slack integrations
- [x] Content processing pipeline
- [ ] Vector search and similarity matching
- [ ] Basic LLM integration

### Phase 3: Advanced Features (In Progress)
- [ ] Multi-modal content support
- [ ] Advanced search algorithms
- [ ] Real-time collaboration
- [ ] Advanced analytics

### Phase 4: Platform Integration (Future)
- [ ] Additional platform connectors
- [ ] Meeting transcription
- [ ] Advanced AI features
- [ ] Enterprise features

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
- Follow the exception handling patterns (B904 compliance)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the test files for usage examples

---

**Note**: This project is actively developed with a focus on production-ready infrastructure and extensible architecture for building AI-powered applications.
