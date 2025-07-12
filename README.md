# Saathy

A FastAPI-based application with vector search capabilities using Qdrant and sentence transformers.

## Features

- FastAPI web framework
- Vector search with Qdrant
- Sentence transformers for embeddings
- Background job scheduling with APScheduler
- Comprehensive testing with pytest
- Code quality with Ruff and Black

## Local Development

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)

### 3-Step Local Run Guide

#### Option 1: Poetry (Development)

1. **Install dependencies**
   ```bash
   poetry install
   ```

2. **Run the application**
   ```bash
   poetry run python -m saathy.main
   ```

3. **Test the health endpoint**
   ```bash
   curl http://localhost:8000/healthz
   ```

#### Option 2: Docker (Recommended)

1. **Start services with Docker Compose**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

2. **Test the health endpoint**
   ```bash
   curl http://localhost:8000/healthz
   ```

3. **Access Qdrant dashboard**
   ```bash
   open http://localhost:6333/dashboard
   ```

The application will be available at `http://localhost:8000`

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run ruff check .
poetry run ruff format .
```

### Automatic Code Quality

This project uses pre-commit hooks to ensure code quality automatically. The hooks run on every commit and include:

- **Ruff**: Linting and auto-fixing Python code
- **Black**: Code formatting
- **isort**: Import sorting (Black profile)
- **Typos**: Spell checking and correction
- **Pre-commit hooks**: Various file checks (YAML, JSON, TOML, etc.)

#### Setup

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files

# Run on staged files only
poetry run pre-commit run
```

#### What's Checked

- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (Ruff)
- ✅ Spell checking (Typos)
- ✅ File format validation
- ✅ Merge conflict detection
- ✅ Large file detection
- ✅ Debug statement detection

### Docker

#### Building the Image

```bash
docker build -t saathy .
```

#### Running with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up

# Start in background
docker-compose -f docker-compose.dev.yml up -d

# Stop services
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f api
```

#### Services

- **API**: FastAPI application on port 8000
- **Qdrant**: Vector database on port 6333 (gRPC) and 6334 (HTTP)
- **Volume**: `qdata` for persistent Qdrant storage

### API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
src/saathy/
├── api.py          # FastAPI instance
├── config.py       # Pydantic Settings singleton
├── vector/         # Qdrant repository layer
│   └── repository.py
├── scheduler.py    # APScheduler init
└── main.py         # Gunicorn/Uvicorn entrypoint
```