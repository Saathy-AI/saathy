# Saathy Cleanup Tasks

## Files to Remove/Relocate

### 1. Demo Files in Root Directory
These should be moved to `tools/demos/`:
- `demo_content_processing.py`
- `demo_modular_chunking.py`
- `demo_notion_advanced_processing.py`
- `demo_notion_connector.py`
- `demo_simple_chunking.py`
- `demo_slack_connector.py`

### 2. Redundant Documentation Files
Consolidate into unified docs:
- `IMPLEMENTATION_COMPLETE_SUMMARY.md` → Move content to docs/
- `IMPLEMENTATION_SUMMARY.md` → Move content to docs/
- `SIMPLIFIED_CHUNKING_SUMMARY.md` → Move content to docs/
- `TESTING_GUIDE.md` → Move to docs/development/
- `saathy-conversational-ai/PHASE2_3_SUMMARY.md` → Archive or integrate
- `saathy-conversational-ai/MIGRATION_GUIDE.md` → Move to docs/
- `saathy-conversational-ai/PRODUCTION_SETUP.md` → Move to docs/deployment/
- `saathy-conversational-ai/API_DOCUMENTATION.md` → Move to docs/api/
- `saathy-conversational-ai/CHANGELOG.md` → Keep but standardize location

### 3. Test/Validation Scripts in Root
Move to appropriate locations:
- `validate-setup.sh` → tools/scripts/
- `validate_settings.py` → tools/scripts/
- `test_prod_setup.py` → tools/scripts/

### 4. Duplicate Docker Compose Files
Consolidate:
- Keep `docker-compose.yml` (development)
- Keep `docker-compose.prod.yml` (production)
- Review and merge: `docker-compose.dev.yml`, `docker-compose.override.yml`, `docker-compose.test.yml`
- Move service-specific: `saathy-conversational-ai/docker-compose.yml`

### 5. Multiple Deployment Scripts
Consolidate into single deployment system:
- Root `deploy.sh`
- `saathy-conversational-ai/deploy.sh`
- `saathy-conversational-ai/test-deployment.sh`
- `saathy-conversational-ai/run_tests.sh`

## Code Refactoring Tasks

### 1. Break Down Monolithic Files
- `src/saathy/api.py` (1506 lines) → Split into:
  - `apps/core-api/src/routers/`
    - `health.py`
    - `connectors.py`
    - `chunking.py`
    - `embedding.py`
    - `intelligence.py`
    - `streaming.py`

### 2. Organize Imports and Dependencies
- Remove unused imports across all files
- Standardize import ordering (use ruff/isort)
- Update relative imports to absolute imports

### 3. Address Technical Debt
Files with TODO/FIXME comments to review:
- `src/saathy/streaming/notion_poller.py`
- `src/saathy/connectors/notion_content_extractor.py`
- `src/saathy/connectors/content_processor.py`
- `src/saathy/api.py`
- `saathy-conversational-ai/backend/app/services/information_analyzer.py`
- `saathy-conversational-ai/backend/app/agents/information_analyzer.py`
- `demo_notion_advanced_processing.py`

## Directory Structure Cleanup

### 1. Create New Structure
```bash
mkdir -p apps/{core-api,conversational-ai,enterprise}/{src,tests}
mkdir -p packages/{saathy-core,saathy-connectors,saathy-chunking,saathy-embedding,saathy-intelligence}/{src,tests}
mkdir -p infrastructure/{docker,kubernetes,terraform,monitoring}
mkdir -p docs/{api,architecture,deployment,development,user-guides}
mkdir -p tools/{scripts,demos,benchmarks}
mkdir -p tests/{e2e,integration,performance}
```

### 2. Move Existing Code
- `src/saathy/` → Split across `apps/core-api/` and `packages/`
- `saathy-conversational-ai/backend/` → `apps/conversational-ai/backend/`
- `saathy-conversational-ai/frontend/` → `apps/conversational-ai/frontend/`
- `tests/` → Distribute to appropriate service/package directories
- `scripts/` → `tools/scripts/`
- Demo files → `tools/demos/`

### 3. Infrastructure Files
- `prometheus/` → `infrastructure/monitoring/prometheus/`
- `grafana/` → `infrastructure/monitoring/grafana/`
- `nginx/` → `infrastructure/docker/nginx/`
- `otel/` → `infrastructure/monitoring/otel/`

## Documentation Consolidation

### 1. Create Documentation Index
```markdown
# docs/index.md
- Getting Started
  - Installation
  - Quick Start
  - Configuration
- Architecture
  - System Overview
  - Service Architecture
  - Data Flow
- API Reference
  - Core API
  - Conversational AI API
  - WebSocket Events
- Deployment
  - Docker Deployment
  - Kubernetes (Future)
  - Monitoring Setup
- Development
  - Setup Guide
  - Testing Guide
  - Contributing
- User Guides
  - Connector Setup
  - Intelligence Features
  - Troubleshooting
```

### 2. Migrate Existing Docs
- Combine all connector setup guides
- Merge deployment documentation
- Create unified API documentation
- Archive outdated summaries

## Testing Framework Unification

### 1. Consolidate Test Configuration
- Merge pytest configurations
- Create shared conftest.py
- Standardize test naming

### 2. Organize Test Files
- Unit tests with source code
- Integration tests in service directories
- E2E tests in root tests/

### 3. Add Missing Tests
- Frontend component tests
- E2E workflow tests
- Performance benchmarks

## Dependency Management

### 1. Consolidate Requirements
- Create unified `pyproject.toml` for monorepo
- Individual `requirements.txt` for each service
- Pin all dependency versions

### 2. Remove Duplicates
- Analyze and remove duplicate dependencies
- Use shared packages for common functionality

## Configuration Cleanup

### 1. Environment Variables
- Create `.env.example` for each service
- Document all environment variables
- Use consistent naming convention

### 2. Configuration Files
- Standardize configuration format
- Use Pydantic settings consistently
- Create configuration validation

## Build and Deployment

### 1. Makefile Creation
```makefile
# Root Makefile
.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  make dev       - Start development environment"
	@echo "  make test      - Run all tests"
	@echo "  make lint      - Run linters"
	@echo "  make build     - Build all services"
	@echo "  make deploy    - Deploy to production"
	@echo "  make clean     - Clean build artifacts"

dev:
	docker-compose up -d

test:
	pytest -v

lint:
	ruff check .
	black --check .

build:
	docker-compose build

deploy:
	./tools/scripts/deploy.sh

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	docker-compose down -v
```

### 2. CI/CD Pipeline
- Create GitHub Actions workflows
- Add pre-commit hooks
- Set up automated testing

## Monitoring and Observability

### 1. Consolidate Monitoring Config
- Single Prometheus configuration
- Unified Grafana dashboards
- Centralized logging

### 2. Add Missing Monitoring
- Application metrics
- Business metrics
- SLA monitoring

## Security Cleanup

### 1. Secrets Management
- Review secrets/ directory
- Implement proper secret rotation
- Document secret management

### 2. Security Scanning
- Add dependency scanning
- Implement SAST tools
- Regular security audits

## Timeline

1. **Week 1**: File cleanup and reorganization
2. **Week 2**: Code refactoring and modularization
3. **Week 3**: Testing framework unification
4. **Week 4**: Documentation consolidation
5. **Week 5**: Deployment simplification
6. **Week 6**: Final testing and validation

## Success Metrics

- [ ] No files in root except essential ones
- [ ] All tests passing with >80% coverage
- [ ] Single source of documentation
- [ ] Deployment time < 10 minutes
- [ ] All TODOs addressed or documented
- [ ] Clear separation of concerns
- [ ] Standardized code style