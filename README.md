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

## Quick Deploy to VPS

### Prerequisites

- Ubuntu 20.04+ VPS
- SSH access with sudo privileges
- Domain name (optional, for HTTPS)

### 3-Step Deployment

1. **Initial VPS Setup**
   ```bash
   # Follow the complete setup guide
   # See: docs/vps-setup.md
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env  # Set your API keys and domain
   ```

3. **Deploy**
   ```bash
   ./deploy.sh --init  # First time setup
   ./deploy.sh         # Regular deployments
   ```

### What Gets Deployed

- **FastAPI Application**: Running with Gunicorn (4 workers)
- **Qdrant**: Vector database with persistent storage
- **Nginx**: Reverse proxy with SSL/TLS termination
- **Security**: Rate limiting, security headers, non-root containers

### Post-Deployment

- Application available at `https://your-domain.com` (or `http://your-server-ip`)
- Health check: `curl https://your-domain.com/healthz`
- Container logs: `docker-compose -f docker-compose.prod.yml logs -f`

## Initial VPS Setup

For complete VPS setup instructions, see [docs/vps-setup.md](docs/vps-setup.md).

Key steps:
1. **System Updates**: `sudo apt update && sudo apt upgrade -y`
2. **Security**: Configure SSH, firewall, fail2ban
3. **Docker**: Install Docker and Docker Compose
4. **SSL**: Set up Let's Encrypt certificates
5. **Deploy**: Run `./deploy.sh --init`

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check application health
curl -f https://your-domain.com/healthz

# Check container status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Backup Management

```bash
# Create backup
./scripts/backup.sh

# List backups
./scripts/backup.sh --help

# Restore from backup
./scripts/restore.sh qdrant-backup-YYYYMMDD-HHMMSS.tar.gz
```

### Updates and Rollbacks

```bash
# Regular deployment
./deploy.sh

# Test deployment (dry run)
./deploy.sh --dry-run

# Rollback if needed
./deploy.sh --rollback
```

## Project Structure

```
src/saathy/
├── api.py          # FastAPI instance
├── config.py       # Pydantic Settings singleton
├── vector/         # Qdrant repository layer
│   └── repository.py
├── scheduler.py    # APScheduler init
└── main.py         # Gunicorn/Uvicorn entrypoint

docker-compose.prod.yml  # Production services
deploy.sh               # Deployment script
nginx/                  # Nginx configuration
├── nginx.conf
└── ssl/               # SSL certificates
scripts/               # Maintenance scripts
├── backup.sh
└── restore.sh
docs/                  # Documentation
└── vps-setup.md      # Complete VPS setup guide
```