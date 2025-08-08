# Saathy Makefile
# Build automation and common development tasks

.DEFAULT_GOAL := help
.PHONY: help dev prod test lint format clean build deploy setup docs

# Variables
PYTHON := python3
PYTEST := pytest
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_PROD := docker-compose -f docker-compose.prod.yml
RUFF := ruff
BLACK := black

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

## Help
help:
	@echo "$(BLUE)Saathy Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make setup      - Initial project setup"
	@echo "  make dev        - Start development environment"
	@echo "  make stop       - Stop development environment"
	@echo "  make restart    - Restart development environment"
	@echo "  make logs       - Show development logs"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test       - Run all tests"
	@echo "  make test-unit  - Run unit tests only"
	@echo "  make test-int   - Run integration tests only"
	@echo "  make test-cov   - Run tests with coverage report"
	@echo "  make test-watch - Run tests in watch mode"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint       - Run code linters"
	@echo "  make format     - Format code with black"
	@echo "  make check      - Run all checks (lint + test)"
	@echo "  make todo       - Show all TODO/FIXME comments"
	@echo ""
	@echo "$(GREEN)Building:$(NC)"
	@echo "  make build      - Build all Docker images"
	@echo "  make build-core - Build core API image"
	@echo "  make build-conv - Build conversational AI images"
	@echo ""
	@echo "$(GREEN)Production:$(NC)"
	@echo "  make prod       - Start production environment"
	@echo "  make prod-stop  - Stop production environment"
	@echo "  make deploy     - Deploy to production"
	@echo "  make backup     - Backup production data"
	@echo ""
	@echo "$(GREEN)Documentation:$(NC)"
	@echo "  make docs       - Build documentation"
	@echo "  make docs-serve - Serve documentation locally"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make prune      - Clean Docker system"
	@echo "  make fresh      - Clean and rebuild everything"

## Setup
setup:
	@echo "$(BLUE)Setting up Saathy development environment...$(NC)"
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "$(RED)Python 3 is required but not installed.$(NC)" >&2; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Docker is required but not installed.$(NC)" >&2; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "$(RED)Docker Compose is required but not installed.$(NC)" >&2; exit 1; }
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	@pip install poetry
	@poetry install
	@echo "$(GREEN)Creating necessary directories...$(NC)"
	@mkdir -p logs secrets
	@echo "$(GREEN)Copying environment templates...$(NC)"
	@test -f .env || cp .env.example .env
	@echo "$(GREEN)Setup complete! Run 'make dev' to start development environment.$(NC)"

## Development
dev:
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Development environment started!$(NC)"
	@echo "Services available at:"
	@echo "  - API: http://localhost:8000"
	@echo "  - Qdrant: http://localhost:6333"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000"

stop:
	@echo "$(BLUE)Stopping development environment...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Development environment stopped.$(NC)"

restart: stop dev

logs:
	@$(DOCKER_COMPOSE) logs -f

## Testing
test:
	@echo "$(BLUE)Running all tests...$(NC)"
	@$(PYTEST) -v

test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(PYTEST) -v -m "not integration and not slow"

test-int:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@$(PYTEST) -v -m "integration"

test-cov:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	@$(PYTEST) -v --cov=src --cov=saathy-conversational-ai --cov-report=html --cov-report=term-missing

test-watch:
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	@$(PYTEST) -v --watch

## Code Quality
lint:
	@echo "$(BLUE)Running linters...$(NC)"
	@$(RUFF) check .
	@echo "$(GREEN)Linting passed!$(NC)"

format:
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(BLACK) .
	@$(RUFF) check --fix .
	@echo "$(GREEN)Code formatted!$(NC)"

check: lint test
	@echo "$(GREEN)All checks passed!$(NC)"

todo:
	@echo "$(BLUE)TODO/FIXME comments in codebase:$(NC)"
	@grep -rn "TODO\|FIXME\|XXX\|HACK" --include="*.py" --include="*.js" --include="*.ts" --include="*.jsx" --include="*.tsx" . | grep -v node_modules | grep -v .git

## Building
build:
	@echo "$(BLUE)Building all Docker images...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)Build complete!$(NC)"

build-core:
	@echo "$(BLUE)Building core API image...$(NC)"
	@docker build -t saathy-core:latest -f Dockerfile .
	@echo "$(GREEN)Core API build complete!$(NC)"

build-conv:
	@echo "$(BLUE)Building conversational AI images...$(NC)"
	@docker build -t saathy-conv-backend:latest -f saathy-conversational-ai/backend/Dockerfile saathy-conversational-ai/backend
	@docker build -t saathy-conv-frontend:latest -f saathy-conversational-ai/frontend/Dockerfile saathy-conversational-ai/frontend
	@echo "$(GREEN)Conversational AI build complete!$(NC)"

## Production
prod:
	@echo "$(BLUE)Starting production environment...$(NC)"
	@$(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)Production environment started!$(NC)"

prod-stop:
	@echo "$(BLUE)Stopping production environment...$(NC)"
	@$(DOCKER_COMPOSE_PROD) down
	@echo "$(GREEN)Production environment stopped.$(NC)"

deploy:
	@echo "$(BLUE)Deploying to production...$(NC)"
	@./deploy.sh
	@echo "$(GREEN)Deployment complete!$(NC)"

backup:
	@echo "$(BLUE)Backing up production data...$(NC)"
	@./scripts/backup.sh
	@echo "$(GREEN)Backup complete!$(NC)"

## Documentation
docs:
	@echo "$(BLUE)Building documentation...$(NC)"
	@cd docs && mkdocs build
	@echo "$(GREEN)Documentation built!$(NC)"

docs-serve:
	@echo "$(BLUE)Serving documentation locally...$(NC)"
	@cd docs && mkdocs serve

## Maintenance
clean:
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete
	@echo "$(GREEN)Clean complete!$(NC)"

prune:
	@echo "$(BLUE)Pruning Docker system...$(NC)"
	@docker system prune -af --volumes
	@echo "$(GREEN)Docker system pruned!$(NC)"

fresh: clean prune build dev
	@echo "$(GREEN)Fresh environment ready!$(NC)"

# Special targets
.PHONY: install-hooks
install-hooks:
	@echo "$(BLUE)Installing git hooks...$(NC)"
	@pre-commit install
	@echo "$(GREEN)Git hooks installed!$(NC)"

.PHONY: update-deps
update-deps:
	@echo "$(BLUE)Updating dependencies...$(NC)"
	@poetry update
	@cd saathy-conversational-ai/backend && pip-compile requirements.in
	@cd saathy-conversational-ai/frontend && npm update
	@echo "$(GREEN)Dependencies updated!$(NC)"

.PHONY: security-scan
security-scan:
	@echo "$(BLUE)Running security scan...$(NC)"
	@poetry run safety check
	@poetry run bandit -r src/
	@echo "$(GREEN)Security scan complete!$(NC)"

.PHONY: perf-test
perf-test:
	@echo "$(BLUE)Running performance tests...$(NC)"
	@$(PYTEST) -v tests/performance/
	@echo "$(GREEN)Performance tests complete!$(NC)"

# Database operations
.PHONY: db-migrate
db-migrate:
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker-compose exec conversational-ai-backend alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

.PHONY: db-rollback
db-rollback:
	@echo "$(BLUE)Rolling back database migration...$(NC)"
	@docker-compose exec conversational-ai-backend alembic downgrade -1
	@echo "$(GREEN)Rollback complete!$(NC)"

# Monitoring
.PHONY: monitor
monitor:
	@echo "$(BLUE)Opening monitoring dashboards...$(NC)"
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Grafana: http://localhost:3000"
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Prometheus: http://localhost:9090"

# Version management
.PHONY: version
version:
	@echo "Saathy version: $$(grep '^version' pyproject.toml | cut -d'"' -f2)"