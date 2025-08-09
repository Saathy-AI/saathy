# Saathy Architecture Restructuring Proposal

## Executive Summary

This document outlines a comprehensive restructuring plan for the Saathy codebase to achieve:
- Optimal modularity and maintainability
- Simplified deployment processes
- Clear separation between open-source and enterprise features
- Unified testing framework
- Centralized documentation

## Current State Analysis

### Repository Structure
```
saathy/
├── src/saathy/                    # Core knowledge layer & connectors
├── saathy-conversational-ai/      # Conversational AI service
│   ├── backend/                   # FastAPI backend
│   └── frontend/                  # React frontend
├── tests/                         # Core tests
├── docs/                          # Documentation (scattered)
├── scripts/                       # Deployment & utility scripts
└── [various demo files]           # Demo scripts in root
```

### Identified Issues

1. **Scattered Documentation**
   - Documentation spread across root, docs/, and service directories
   - Multiple README files with overlapping content
   - No unified documentation portal

2. **Inconsistent Testing**
   - Two separate test directories (tests/ and saathy-conversational-ai/backend/tests/)
   - Using pytest but no unified test configuration
   - Missing frontend tests structure

3. **Complex Deployment**
   - Multiple docker-compose files
   - Separate deployment scripts for each service
   - No unified CI/CD pipeline

4. **Mixed Concerns**
   - Demo files in root directory
   - No clear separation for enterprise features
   - Monolithic api.py with 1500+ lines

5. **Technical Debt**
   - 22 TODO/FIXME comments across codebase
   - Large monolithic files need refactoring

## Proposed Architecture

### 1. Monorepo Structure with Clear Service Boundaries

```
saathy/
├── apps/                          # Application services
│   ├── core-api/                  # Core knowledge layer API
│   │   ├── src/                   # Source code
│   │   ├── tests/                 # Unit & integration tests
│   │   ├── Dockerfile             
│   │   └── requirements.txt       
│   │
│   ├── conversational-ai/         # Conversational AI service
│   │   ├── backend/               
│   │   ├── frontend/              
│   │   ├── tests/                 # Service-specific tests
│   │   └── docker-compose.yml     
│   │
│   └── enterprise/                # Enterprise features (private)
│       ├── src/                   
│       ├── tests/                 
│       └── README.md              
│
├── packages/                      # Shared libraries
│   ├── saathy-core/              # Core domain models & interfaces
│   ├── saathy-connectors/        # Connector framework
│   ├── saathy-chunking/          # Chunking strategies
│   ├── saathy-embedding/         # Embedding services
│   └── saathy-intelligence/      # AI/ML components
│
├── infrastructure/               # Infrastructure as Code
│   ├── docker/                   # Docker configurations
│   ├── kubernetes/               # K8s manifests (future)
│   ├── terraform/                # Infrastructure provisioning
│   └── monitoring/               # Prometheus, Grafana configs
│
├── docs/                         # Centralized documentation
│   ├── api/                      # API documentation
│   ├── architecture/             # Architecture decisions
│   ├── deployment/               # Deployment guides
│   ├── development/              # Development guides
│   └── user-guides/              # End-user documentation
│
├── tools/                        # Development tools
│   ├── scripts/                  # Build & deployment scripts
│   ├── demos/                    # Demo applications
│   └── benchmarks/               # Performance benchmarks
│
├── tests/                        # Cross-cutting tests
│   ├── e2e/                      # End-to-end tests
│   ├── integration/              # Integration tests
│   └── performance/              # Performance tests
│
├── .github/                      # GitHub configurations
│   └── workflows/                # CI/CD workflows
│
├── docker-compose.yml            # Development environment
├── docker-compose.prod.yml       # Production environment
├── Makefile                      # Build automation
├── pyproject.toml                # Python project configuration
└── README.md                     # Project overview
```

### 2. Service Separation Strategy

#### Core API Service (`apps/core-api/`)
- FastAPI application for core functionality
- Handles connectors, chunking, embedding, vector storage
- Provides REST and WebSocket APIs
- Deployable as standalone service

#### Conversational AI Service (`apps/conversational-ai/`)
- Separate backend and frontend
- Consumes Core API services
- Handles conversation flow and UI
- Can be deployed independently

#### Enterprise Layer (`apps/enterprise/`)
- Private repository/submodule
- Extends core services with premium features
- Separate deployment pipeline
- License-based activation

### 3. Shared Packages Architecture

Each package in `packages/` follows:
```
saathy-{package}/
├── src/
│   └── saathy_{package}/
│       ├── __init__.py
│       ├── models.py
│       ├── interfaces.py
│       └── implementations/
├── tests/
├── pyproject.toml
└── README.md
```

### 4. Deployment Simplification

#### Unified Docker Compose
```yaml
# docker-compose.yml (development)
services:
  core-api:
    build: ./apps/core-api
    depends_on: [qdrant, redis]
  
  conversational-ai-backend:
    build: ./apps/conversational-ai/backend
    depends_on: [core-api, postgres]
  
  conversational-ai-frontend:
    build: ./apps/conversational-ai/frontend
    depends_on: [conversational-ai-backend]
  
  # Infrastructure services
  qdrant: ...
  redis: ...
  postgres: ...
```

#### Makefile for Common Tasks
```makefile
.PHONY: dev prod test lint

dev:
	docker-compose up -d

prod:
	docker-compose -f docker-compose.prod.yml up -d

test:
	pytest tests/ --cov=apps --cov=packages

lint:
	ruff check .
	black --check .
```

### 5. Testing Framework Unification

#### Centralized pytest Configuration
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["apps", "packages", "tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "-v",
    "--tb=short",
    "--cov=apps",
    "--cov=packages",
    "--cov-report=html",
    "--cov-report=term-missing",
]

[tool.coverage.run]
source = ["apps", "packages"]
omit = ["*/tests/*", "*/test_*"]
```

#### Test Organization
- Unit tests: Next to source code in each service/package
- Integration tests: In service-specific test directories
- E2E tests: In root `tests/e2e/`
- Shared fixtures: In `tests/conftest.py`

### 6. Documentation Strategy

#### Documentation Portal Structure
```
docs/
├── index.md                     # Documentation home
├── getting-started/
│   ├── installation.md
│   ├── quickstart.md
│   └── configuration.md
├── api/
│   ├── core-api.md
│   ├── conversational-ai.md
│   └── webhooks.md
├── architecture/
│   ├── overview.md
│   ├── services.md
│   ├── data-flow.md
│   └── decisions/              # ADRs
├── deployment/
│   ├── docker.md
│   ├── kubernetes.md
│   └── monitoring.md
├── development/
│   ├── setup.md
│   ├── contributing.md
│   └── testing.md
└── user-guides/
    ├── connectors/
    ├── intelligence/
    └── troubleshooting.md
```

Use MkDocs or Docusaurus for documentation portal.

### 7. Enterprise vs Open-Source Strategy

#### Feature Segregation
```python
# packages/saathy-core/src/saathy_core/features.py
from enum import Enum

class FeatureTier(Enum):
    OPEN_SOURCE = "open_source"
    ENTERPRISE = "enterprise"

class Feature:
    def __init__(self, name: str, tier: FeatureTier):
        self.name = name
        self.tier = tier
    
    def is_available(self, license_type: str) -> bool:
        if self.tier == FeatureTier.OPEN_SOURCE:
            return True
        return license_type == "enterprise"
```

#### Licensing Model
```python
# apps/core-api/src/licensing.py
class LicenseManager:
    def __init__(self):
        self.license_key = os.getenv("SAATHY_LICENSE_KEY")
        self.tier = self._validate_license()
    
    def check_feature(self, feature_name: str) -> bool:
        feature = FEATURE_REGISTRY.get(feature_name)
        return feature.is_available(self.tier)
```

#### Open-Source Features
- Basic connectors (Slack, GitHub)
- Standard chunking strategies
- Basic embedding models
- Community support

#### Enterprise Features
- Advanced connectors (Salesforce, Jira, etc.)
- Custom chunking strategies
- Advanced AI models
- Priority support
- SSO/SAML authentication
- Advanced analytics
- Compliance features (HIPAA, SOC2)

### 8. CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [core-api, conversational-ai-backend]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Run tests
        run: |
          cd apps/${{ matrix.service }}
          pytest tests/ --cov

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker images
        run: make build
      
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: make deploy
```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. Create new directory structure
2. Move existing code to appropriate locations
3. Set up shared packages
4. Configure monorepo tooling

### Phase 2: Service Separation (Week 3-4)
1. Refactor core API into smaller modules
2. Extract shared libraries
3. Update import paths
4. Update Docker configurations

### Phase 3: Testing & Documentation (Week 5-6)
1. Unify test framework
2. Migrate existing tests
3. Create documentation portal
4. Write missing documentation

### Phase 4: Deployment & CI/CD (Week 7-8)
1. Simplify deployment scripts
2. Set up GitHub Actions
3. Configure monitoring
4. Create deployment documentation

### Phase 5: Enterprise Features (Week 9-10)
1. Design license management
2. Implement feature flags
3. Create enterprise package structure
4. Set up private repository

## Migration Checklist

- [ ] Backup current repository
- [ ] Create feature branch for restructuring
- [ ] Set up new directory structure
- [ ] Move files to new locations
- [ ] Update all import statements
- [ ] Update Docker configurations
- [ ] Update CI/CD pipelines
- [ ] Migrate tests
- [ ] Update documentation
- [ ] Test all services
- [ ] Update deployment scripts
- [ ] Merge and deploy

## Benefits

1. **Modularity**: Clear separation of concerns
2. **Maintainability**: Easier to understand and modify
3. **Scalability**: Services can scale independently
4. **Testability**: Unified testing with better coverage
5. **Documentation**: Single source of truth
6. **Deployment**: Simplified with fewer manual steps
7. **Enterprise Ready**: Clear path for commercial features

## Risks and Mitigation

1. **Risk**: Breaking existing functionality
   - **Mitigation**: Comprehensive testing, gradual migration

2. **Risk**: Team learning curve
   - **Mitigation**: Documentation, training sessions

3. **Risk**: Deployment complexity during transition
   - **Mitigation**: Maintain backward compatibility, phased rollout

## Conclusion

This restructuring will transform Saathy into a professional, maintainable, and scalable platform ready for both open-source community and enterprise customers. The modular architecture enables independent development and deployment while maintaining code quality and developer experience.