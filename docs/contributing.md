# Contributing to Saathy

Thank you for your interest in contributing to Saathy! This document provides guidelines and information for contributors to help make the contribution process smooth and effective.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Standards](#code-standards)
4. [Git Workflow](#git-workflow)
5. [Pull Request Process](#pull-request-process)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Issue Reporting](#issue-reporting)
9. [Community Guidelines](#community-guidelines)
10. [Release Process](#release-process)

## Getting Started

### Before You Begin

1. **Read the Documentation**: Familiarize yourself with the project by reading the [README](README.md) and other documentation in the `docs/` directory.

2. **Check Existing Issues**: Before creating a new issue or starting work, check if your idea has already been discussed or implemented.

3. **Join the Community**: Consider joining our community channels for discussions and support.

### Types of Contributions

We welcome various types of contributions:

- **Bug Fixes**: Fixing existing issues
- **Feature Development**: Adding new functionality
- **Documentation**: Improving or adding documentation
- **Testing**: Adding tests or improving test coverage
- **Performance Improvements**: Optimizing existing code
- **Code Quality**: Refactoring and improving code structure
- **Translations**: Adding support for additional languages

## Development Setup

### Prerequisites

Ensure you have the following installed:

- **Python 3.9+**: [Download from python.org](https://www.python.org/downloads/)
- **Poetry**: [Installation guide](https://python-poetry.org/docs/#installation)
- **Docker & Docker Compose**: [Installation guide](https://docs.docker.com/get-docker/)
- **Git**: [Download from git-scm.com](https://git-scm.com/downloads)

### Local Development Environment

1. **Fork and Clone**:
   ```bash
   # Fork the repository on GitHub
   # Then clone your fork
   git clone https://github.com/your-username/saathy.git
   cd saathy
   ```

2. **Set up Poetry Environment**:
   ```bash
   # Install dependencies
   poetry install
   
   # Activate the virtual environment
   poetry shell
   ```

3. **Install Pre-commit Hooks**:
   ```bash
   poetry run pre-commit install
   ```

4. **Set up Environment Variables**:
   ```bash
   cp docs/env.example .env
   # Edit .env with your configuration
   ```

5. **Start Development Services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

6. **Run the Application**:
   ```bash
   poetry run uvicorn saathy.api:app --reload --host 0.0.0.0 --port 8000
   ```

### IDE Configuration

#### VS Code Setup

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

#### PyCharm Setup

1. Open the project in PyCharm
2. Configure the Poetry interpreter:
   - Go to Settings → Project → Python Interpreter
   - Add interpreter → Poetry Environment
   - Select the project's `pyproject.toml`

## Code Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications enforced by Ruff:

- **Line Length**: 88 characters (Black default)
- **Import Organization**: Standard library, third-party, local imports
- **Type Hints**: Required for all public functions and methods
- **Docstrings**: Google-style docstrings for all public APIs

### Code Formatting

We use **Ruff** for formatting and linting:

```bash
# Format code
poetry run ruff format .

# Lint code
poetry run ruff check .

# Fix auto-fixable issues
poetry run ruff check --fix .
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Run type checking
poetry run mypy src/
```

### Import Organization

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

### Function Documentation

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
        
    Example:
        >>> processor = ChunkingProcessor()
        >>> chunks = processor.chunk_content("Hello world")
        >>> len(chunks)
        1
    """
    pass
```

### Error Handling

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

## Git Workflow

### Branch Naming Convention

Use descriptive branch names with prefixes:

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks

Examples:
- `feature/add-slack-connector`
- `fix/qdrant-connection-issue`
- `docs/update-api-reference`
- `refactor/chunking-processor`

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(connectors): add GitHub webhook support

fix(chunking): resolve memory leak in large document processing

docs(api): update endpoint documentation with examples

test(embedding): add unit tests for embedding service
```

### Git Workflow Steps

1. **Create Feature Branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   ```bash
   # Make your changes
   # Run tests and linting
   poetry run pytest
   poetry run ruff check .
   ```

3. **Commit Changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

4. **Push to Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**:
   - Go to your fork on GitHub
   - Click "New Pull Request"
   - Select your feature branch
   - Fill out the PR template

## Pull Request Process

### Before Submitting

1. **Run Tests**: Ensure all tests pass
   ```bash
   poetry run pytest
   poetry run pytest --cov=saathy --cov-report=html
   ```

2. **Code Quality Checks**:
   ```bash
   poetry run ruff check .
   poetry run ruff format .
   poetry run mypy src/
   ```

3. **Update Documentation**: Add or update documentation as needed

4. **Check for Conflicts**: Ensure your branch is up to date with main

### Pull Request Template

When creating a PR, use the following template:

```markdown
## Description

Brief description of the changes made.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Code coverage maintained or improved

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Related Issues

Closes #(issue number)
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and quality checks
2. **Code Review**: At least one maintainer reviews the code
3. **Address Feedback**: Respond to review comments and make requested changes
4. **Approval**: Once approved, the PR can be merged

### Merge Strategy

- **Squash and Merge**: For feature branches
- **Rebase and Merge**: For clean commit history
- **Merge Commit**: For complex changes with multiple commits

## Testing Guidelines

### Test Structure

```
tests/
├── conftest.py            # Pytest configuration and fixtures
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
    """Test that ChunkingProcessor initializes correctly."""
    processor = ChunkingProcessor()
    assert processor is not None
    assert processor.config is not None

def test_fixed_size_chunking():
    """Test fixed-size chunking strategy."""
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
    """Test health check endpoint."""
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
    """Test Qdrant database connection."""
    client = QdrantClient()
    is_connected = await client.health_check()
    assert is_connected is True
```

### Test Fixtures

```python
# conftest.py
import pytest
from typing import Dict, Any

@pytest.fixture
def sample_content() -> str:
    """Provide sample content for testing."""
    return "This is sample content for testing chunking strategies."

@pytest.fixture
def github_webhook_payload() -> Dict[str, Any]:
    """Provide sample GitHub webhook payload."""
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

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=saathy --cov-report=html

# Run specific test file
poetry run pytest tests/test_api.py

# Run integration tests
poetry run pytest -m integration

# Run slow tests
poetry run pytest -m slow

# Run tests in parallel
poetry run pytest -n auto
```

## Documentation

### Documentation Standards

1. **Keep it Updated**: Update documentation when code changes
2. **Be Clear and Concise**: Write clear, easy-to-understand documentation
3. **Include Examples**: Provide practical examples for complex features
4. **Use Consistent Formatting**: Follow markdown formatting guidelines

### Documentation Structure

```
docs/
├── README.md              # Project overview
├── api-reference.md       # API documentation
├── development-guide.md   # Development setup and workflow
├── deployment-guide.md    # Production deployment
├── architecture.md        # System architecture
├── contributing.md        # This file
├── chunking-system.md     # Chunking system documentation
├── embedding-service.md   # Embedding service documentation
├── slack-setup.md         # Slack connector setup
├── vps-setup.md          # VPS deployment guide
└── env.example           # Environment variables template
```

### Code Documentation

```python
class ChunkingProcessor:
    """
    Main processor for content chunking operations.
    
    This class orchestrates the chunking process by selecting appropriate
    strategies, managing caching, and validating chunk quality.
    
    Attributes:
        config: Configuration for chunking operations
        strategies: Available chunking strategies
        cache: Cache for storing chunk results
        validator: Quality validator for chunks
    """
    
    def __init__(self, config: ChunkingConfig):
        """
        Initialize the chunking processor.
        
        Args:
            config: Configuration object for chunking settings
        """
        self.config = config
        self.strategies = self._load_strategies()
        self.cache = ChunkCache(config.cache_size)
        self.validator = QualityValidator()
```

## Issue Reporting

### Before Creating an Issue

1. **Search Existing Issues**: Check if the issue has already been reported
2. **Check Documentation**: Ensure the issue isn't covered in the documentation
3. **Reproduce the Issue**: Make sure you can consistently reproduce the problem

### Issue Template

Use the following template when creating issues:

```markdown
## Bug Report

### Description
Clear and concise description of the bug.

### Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

### Expected Behavior
What you expected to happen.

### Actual Behavior
What actually happened.

### Environment
- OS: [e.g. Ubuntu 20.04]
- Python Version: [e.g. 3.9.7]
- Saathy Version: [e.g. 0.1.0]
- Docker Version: [e.g. 20.10.0]

### Additional Context
Add any other context about the problem here.

### Logs
Include relevant logs if applicable.
```

### Feature Request Template

```markdown
## Feature Request

### Description
Clear and concise description of the feature you'd like to see.

### Use Case
Describe the use case for this feature.

### Proposed Solution
Describe your proposed solution if you have one.

### Alternatives Considered
Describe any alternative solutions you've considered.

### Additional Context
Add any other context or screenshots about the feature request.
```

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please:

- **Be Respectful**: Treat all community members with respect
- **Be Inclusive**: Welcome contributors from diverse backgrounds
- **Be Constructive**: Provide constructive feedback and suggestions
- **Be Patient**: Understand that maintainers are volunteers

### Communication Channels

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and discussions
- **Pull Requests**: For code contributions

### Getting Help

1. **Check Documentation**: Start with the documentation in the `docs/` directory
2. **Search Issues**: Look for similar issues or discussions
3. **Create an Issue**: If you can't find an answer, create a new issue
4. **Be Specific**: Provide detailed information when asking for help

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/) (SemVer):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

Before a release:

1. **Update Version**: Update version in `pyproject.toml`
2. **Update Changelog**: Add release notes to `CHANGELOG.md`
3. **Run Tests**: Ensure all tests pass
4. **Update Documentation**: Update any relevant documentation
5. **Create Release**: Create a GitHub release with release notes

### Release Process

1. **Create Release Branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b release/v1.0.0
   ```

2. **Update Version**:
   ```bash
   # Update pyproject.toml version
   # Update CHANGELOG.md
   git add .
   git commit -m "chore: prepare release v1.0.0"
   ```

3. **Create Release**:
   - Push the release branch
   - Create a pull request
   - After review, merge to main
   - Create a GitHub release with the tag

### Changelog Format

```markdown
# Changelog

## [1.0.0] - 2024-01-01

### Added
- New feature A
- New feature B

### Changed
- Updated feature C
- Improved performance

### Fixed
- Bug fix X
- Bug fix Y

### Removed
- Deprecated feature Z
```

## Recognition

We appreciate all contributions to Saathy! Contributors will be:

- **Acknowledged**: Listed in the contributors section
- **Credited**: Mentioned in release notes for significant contributions
- **Thanked**: Personally thanked for their contributions

## Questions?

If you have questions about contributing, please:

1. Check this document first
2. Look at existing issues and discussions
3. Create a new issue with the "question" label

Thank you for contributing to Saathy! 🚀