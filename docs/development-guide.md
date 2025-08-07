# Development Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Code Quality](#code-quality)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

Before you begin development, ensure you have the following installed:

- **Python 3.9+**: [Download from python.org](https://www.python.org/downloads/)
- **Poetry**: [Installation guide](https://python-poetry.org/docs/#installation)
- **Docker & Docker Compose**: [Installation guide](https://docs.docker.com/get-docker/)
- **Git**: [Download from git-scm.com](https://git-scm.com/downloads)
- **VS Code** (recommended): [Download from code.visualstudio.com](https://code.visualstudio.com/)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd saathy
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Set up environment variables:**
   ```bash
   cp docs/env.example .env
   # Edit .env with your configuration
   ```

4. **Install pre-commit hooks:**
   ```bash
   poetry run pre-commit install
   ```

5. **Start development services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

6. **Run the application:**
   ```bash
   poetry run uvicorn saathy.api:app --reload --host 0.0.0.0 --port 8000
   ```

## Development Environment

### VS Code Configuration

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true
  }
}
```

### Recommended Extensions

- **Python**: Microsoft's Python extension
- **Pylance**: Python language server
- **Ruff**: Fast Python linter
- **Docker**: Docker integration
- **GitLens**: Enhanced Git capabilities
- **Thunder Client**: API testing (alternative to Postman)

### Environment Variables

Key environment variables for development:

```bash
# Application
APP_NAME=Saathy
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key

# Embedding Service
OPENAI_API_KEY=your-openai-key
DEFAULT_EMBEDDING_MODEL=all-MiniLM-L6-v2
ENABLE_GPU_EMBEDDINGS=true

# Connectors
GITHUB_TOKEN=your-github-token
GITHUB_WEBHOOK_SECRET=your-webhook-secret
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# Observability
ENABLE_TRACING=true
```

## Project Structure

```
saathy/
├── src/saathy/              # Main application code
│   ├── api.py              # FastAPI application
│   ├── config.py           # Configuration management
│   ├── chunking/           # Chunking system
│   ├── connectors/         # Connector framework
│   ├── embedding/          # Embedding service
│   └── vector/             # Vector database layer
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── docker-compose.*.yml    # Docker configurations
├── pyproject.toml          # Poetry configuration
└── README.md              # Project overview
```

### Key Modules

#### API Layer (`src/saathy/api.py`)
- FastAPI application setup
- Route definitions
- Middleware configuration
- Error handling

#### Configuration (`src/saathy/config.py`)
- Pydantic Settings for environment variables
- Configuration validation
- Default value management

#### Chunking System (`src/saathy/chunking/`)
- Content chunking strategies
- Quality validation
- Caching mechanisms

#### Connectors (`src/saathy/connectors/`)
- Base connector interface
- GitHub and Slack integrations
- Content processing pipeline

#### Embedding Service (`src/saathy/embedding/`)
- Multi-model embedding support
- Content preprocessing
- Performance optimization

#### Vector Database (`src/saathy/vector/`)
- Qdrant client wrapper
- Repository pattern implementation
- Metrics collection

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature-name
```

### 2. Code Review Process

1. **Self-review**: Run tests and linting before pushing
2. **Create PR**: Use the PR template
3. **CI checks**: Ensure all checks pass
4. **Review feedback**: Address reviewer comments
5. **Merge**: Squash and merge when approved

### 3. Testing Strategy

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_api.py

# Run with coverage
poetry run pytest --cov=saathy --cov-report=html

# Run integration tests
poetry run pytest -m integration

# Run slow tests
poetry run pytest -m slow
```

### 4. Database Migrations

```bash
# Check Qdrant collections
curl http://localhost:6333/collections

# Create new collection
curl -X PUT http://localhost:6333/collections/new-collection \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 384, "distance": "Cosine"}}'
```

## Testing

### Test Structure

```
tests/
├── conftest.py            # Pytest configuration
├── test_api.py           # API endpoint tests
├── test_chunking.py      # Chunking system tests
├── test_connectors.py    # Connector tests
├── test_embedding.py     # Embedding service tests
├── test_vector.py        # Vector database tests
└── integration/          # Integration tests
    ├── test_github.py    # GitHub integration tests
    └── test_slack.py     # Slack integration tests
```

### Writing Tests

#### Unit Tests

```python
import pytest
from saathy.chunking import ChunkingProcessor

def test_chunking_processor_initialization():
    processor = ChunkingProcessor()
    assert processor is not None
    assert processor.config is not None

def test_fixed_size_chunking():
    processor = ChunkingProcessor()
    content = "This is a test content that should be chunked."
    chunks = processor.chunk_content(content, strategy="fixed_size")
    
    assert len(chunks) > 0
    assert all(len(chunk.content) <= processor.config.max_chunk_size for chunk in chunks)
```

#### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from saathy.api import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "qdrant_connected" in data["data"]
```

#### Async Tests

```python
import pytest
import asyncio
from saathy.vector import QdrantClient

@pytest.mark.asyncio
async def test_qdrant_connection():
    client = QdrantClient()
    is_connected = await client.health_check()
    assert is_connected is True
```

### Test Data Management

```python
# conftest.py
import pytest
from typing import Dict, Any

@pytest.fixture
def sample_content() -> str:
    return "This is sample content for testing chunking strategies."

@pytest.fixture
def github_webhook_payload() -> Dict[str, Any]:
    return {
        "ref": "refs/heads/main",
        "repository": {
            "name": "test-repo",
            "full_name": "testuser/test-repo"
        },
        "commits": [
            {
                "id": "abc123",
                "message": "Test commit",
                "added": ["test.md"],
                "modified": [],
                "removed": []
            }
        ]
    }
```

### Mocking External Services

```python
import pytest
from unittest.mock import Mock, patch
from saathy.connectors.github_connector import GitHubConnector

@pytest.fixture
def mock_github_api():
    with patch('saathy.connectors.github_connector.GitHubAPI') as mock:
        mock.return_value.get_repo.return_value = Mock()
        yield mock

def test_github_connector_sync(mock_github_api):
    connector = GitHubConnector()
    result = connector.sync_repository("testuser/test-repo")
    assert result is not None
```

## Debugging

### Logging Configuration

```python
import structlog
import logging

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

### Debug Mode

```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debug logging
poetry run uvicorn saathy.api:app --reload --log-level debug
```

### Using Debugger

```python
import pdb
from saathy.chunking import ChunkingProcessor

def debug_chunking():
    processor = ChunkingProcessor()
    content = "Debug this content"
    
    # Set breakpoint
    pdb.set_trace()
    
    chunks = processor.chunk_content(content)
    return chunks
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["saathy.api:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "env": {
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### Performance Profiling

```python
import cProfile
import pstats
from saathy.chunking import ChunkingProcessor

def profile_chunking():
    profiler = cProfile.Profile()
    profiler.enable()
    
    processor = ChunkingProcessor()
    content = "Large content for profiling..."
    chunks = processor.chunk_content(content)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    
    return chunks
```

## Code Quality

### Pre-commit Hooks

The project uses pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run all hooks
poetry run pre-commit run --all-files

# Run specific hook
poetry run pre-commit run ruff --all-files
```

### Linting and Formatting

```bash
# Format code
poetry run ruff format .

# Lint code
poetry run ruff check .

# Fix auto-fixable issues
poetry run ruff check --fix .

# Type checking
poetry run mypy src/
```

### Code Style Guidelines

1. **Import Organization**:
   ```python
   # Standard library imports
   import os
   import sys
   from typing import Dict, List, Optional
   
   # Third-party imports
   import fastapi
   import pydantic
   
   # Local imports
   from saathy.config import Settings
   from saathy.chunking import ChunkingProcessor
   ```

2. **Function Documentation**:
   ```python
   def chunk_content(
       self, 
       content: str, 
       strategy: Optional[str] = None
   ) -> List[Chunk]:
       """
       Chunk content using the specified strategy.
       
       Args:
           content: The content to chunk
           strategy: Chunking strategy to use (auto-detected if None)
           
       Returns:
           List of content chunks
           
       Raises:
           ChunkingError: If chunking fails
       """
   ```

3. **Error Handling**:
   ```python
   try:
       result = process_content(content)
   except ValidationError as e:
       logger.error("Validation failed", error=str(e), content_length=len(content))
       raise ChunkingError(f"Content validation failed: {e}")
   except Exception as e:
       logger.exception("Unexpected error during processing")
       raise ChunkingError(f"Processing failed: {e}")
   ```

## Performance Optimization

### Profiling Tools

```bash
# Install profiling tools
poetry add --group dev py-spy memory-profiler

# CPU profiling
poetry run py-spy top -- python -m saathy

# Memory profiling
poetry run python -m memory_profiler your_script.py
```

### Database Optimization

```python
# Batch operations
async def batch_insert_vectors(self, vectors: List[Vector]):
    """Insert vectors in batches for better performance."""
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        await self.client.upsert(
            collection_name=self.collection_name,
            points=batch
        )
```

### Caching Strategies

```python
from functools import lru_cache
import hashlib

class ChunkingProcessor:
    def __init__(self):
        self._cache = {}
    
    def _get_cache_key(self, content: str, strategy: str) -> str:
        """Generate cache key for content and strategy."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{strategy}:{content_hash}"
    
    def chunk_content(self, content: str, strategy: str = None) -> List[Chunk]:
        cache_key = self._get_cache_key(content, strategy or "auto")
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        chunks = self._process_chunking(content, strategy)
        self._cache[cache_key] = chunks
        return chunks
```

### Async Optimization

```python
import asyncio
from typing import List

async def process_multiple_contents(self, contents: List[str]) -> List[List[Chunk]]:
    """Process multiple contents concurrently."""
    tasks = [
        self.chunk_content_async(content) 
        for content in contents
    ]
    return await asyncio.gather(*tasks)
```

## Troubleshooting

### Common Issues

#### 1. Qdrant Connection Issues

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check Qdrant logs
docker-compose -f docker-compose.dev.yml logs qdrant

# Test Qdrant connectivity
curl http://localhost:6333/collections
```

#### 2. Poetry Environment Issues

```bash
# Clear Poetry cache
poetry cache clear --all pypi

# Reinstall dependencies
poetry install --sync

# Update Poetry
poetry self update
```

#### 3. Docker Issues

```bash
# Clean up Docker resources
docker system prune -a

# Rebuild containers
docker-compose -f docker-compose.dev.yml build --no-cache

# Check container logs
docker-compose -f docker-compose.dev.yml logs -f
```

#### 4. Import Errors

```bash
# Check Python path
poetry run python -c "import sys; print(sys.path)"

# Verify package installation
poetry run python -c "import saathy; print(saathy.__file__)"
```

### Debugging Tools

#### 1. Health Check Script

```bash
# Run health check
./validate-setup.sh

# Check specific component
python validate_settings.py
```

#### 2. Log Analysis

```bash
# Search logs for errors
grep -i error logs/app.log

# Monitor real-time logs
tail -f logs/app.log | grep -i error
```

#### 3. Network Debugging

```bash
# Check port availability
netstat -tulpn | grep :8000

# Test API endpoints
curl -v http://localhost:8000/healthz
```

## Best Practices

### 1. Code Organization

- Keep functions small and focused
- Use meaningful variable and function names
- Group related functionality in modules
- Follow the single responsibility principle

### 2. Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors with context
- Handle errors at appropriate levels

### 3. Testing

- Write tests for new features
- Maintain high test coverage
- Use descriptive test names
- Test both success and failure cases

### 4. Documentation

- Document public APIs
- Keep documentation up to date
- Use type hints
- Add examples for complex functionality

### 5. Performance

- Profile before optimizing
- Use appropriate data structures
- Implement caching where beneficial
- Monitor resource usage

### 6. Security

- Validate all inputs
- Use environment variables for secrets
- Implement rate limiting
- Follow security best practices

### 7. Monitoring

- Add comprehensive logging
- Implement health checks
- Monitor performance metrics
- Set up alerting for critical issues

### 8. Git Workflow

- Use descriptive commit messages
- Keep commits atomic
- Review code before merging
- Use feature branches

This development guide should help you get started with contributing to the Saathy project. For additional help, check the other documentation files or open an issue on GitHub.