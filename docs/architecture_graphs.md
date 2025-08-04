# Saathy Architecture Graphs

This document provides comprehensive visual representations of the Saathy AI copilot architecture, from high-level system overview to detailed component relationships.

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "External Systems"
        GH[GitHub]
        SL[Slack]
        OAI[OpenAI API]
    end
    
    subgraph "Saathy AI Copilot"
        API[FastAPI Application]
        CONN[Connector Framework]
        CHUNK[Chunking System]
        EMB[Embedding Service]
        VEC[Vector Database Layer]
        TELEM[Telemetry & Observability]
    end
    
    subgraph "Infrastructure"
        NGINX[Nginx Reverse Proxy]
        QDRANT[Qdrant Vector DB]
        JAEGER[Jaeger Tracing]
        PROM[Prometheus Metrics]
        GRAFANA[Grafana Dashboards]
    end
    
    GH --> API
    SL --> API
    OAI --> EMB
    
    API --> CONN
    API --> CHUNK
    API --> EMB
    API --> VEC
    API --> TELEM
    
    CONN --> CHUNK
    CHUNK --> EMB
    EMB --> VEC
    
    VEC --> QDRANT
    TELEM --> JAEGER
    TELEM --> PROM
    PROM --> GRAFANA
    
    NGINX --> API
```

## 2. Application Layer Architecture

```mermaid
graph TB
    subgraph "API Layer"
        MAIN[__main__.py]
        API[api.py]
        CONFIG[config.py]
        SCHED[scheduler.py]
    end
    
    subgraph "Core Services"
        CHUNK[chunking/]
        CONN[connectors/]
        EMB[embedding/]
        VEC[vector/]
        TELEM[telemetry.py]
    end
    
    subgraph "External Dependencies"
        FASTAPI[FastAPI]
        UVICORN[Uvicorn]
        PYDANTIC[Pydantic Settings]
        APSCHED[APScheduler]
        OTEL[OpenTelemetry]
    end
    
    MAIN --> API
    API --> CONFIG
    API --> SCHED
    API --> CHUNK
    API --> CONN
    API --> EMB
    API --> VEC
    API --> TELEM
    
    MAIN --> FASTAPI
    MAIN --> UVICORN
    CONFIG --> PYDANTIC
    SCHED --> APSCHED
    TELEM --> OTEL
```

## 3. Connector Framework Architecture

```mermaid
graph TB
    subgraph "Connector Base"
        BASE[base.py]
        CONTENT[content_processor.py]
    end
    
    subgraph "Specific Connectors"
        GH[github_connector.py]
        SL[slack_connector.py]
    end
    
    subgraph "External APIs"
        GH_API[GitHub API]
        SL_API[Slack API]
    end
    
    subgraph "Processing Pipeline"
        CHUNK[Chunking System]
        EMB[Embedding Service]
        VEC[Vector Storage]
    end
    
    BASE --> GH
    BASE --> SL
    CONTENT --> GH
    CONTENT --> SL
    
    GH --> GH_API
    SL --> SL_API
    
    GH --> CHUNK
    SL --> CHUNK
    CHUNK --> EMB
    EMB --> VEC
```

## 4. Chunking System Architecture

```mermaid
graph TB
    subgraph "Chunking Processor"
        PROC[processor.py]
        STRAT[strategies.py]
    end
    
    subgraph "Strategy Implementations"
        FIXED[fixed_size.py]
        SEM[semantic.py]
        DOC[document.py]
        CODE[code.py]
        EMAIL[email.py]
        MEET[meeting.py]
        SLACK[slack_message.py]
        GIT[git_commit.py]
    end
    
    subgraph "Core Components"
        INTERF[interfaces.py]
        MODELS[models.py]
        EXCEPT[exceptions.py]
    end
    
    subgraph "Utilities"
        CACHE[chunk_cache.py]
        MERGE[chunk_merger.py]
        DETECT[content_detector.py]
        HASH[hash_utils.py]
        QUAL[quality_validator.py]
    end
    
    subgraph "Analysis"
        ANALYZE[analyzer.py]
        VIZ[visualizer.py]
    end
    
    PROC --> STRAT
    STRAT --> FIXED
    STRAT --> SEM
    STRAT --> DOC
    STRAT --> CODE
    STRAT --> EMAIL
    STRAT --> MEET
    STRAT --> SLACK
    STRAT --> GIT
    
    PROC --> INTERF
    PROC --> MODELS
    PROC --> EXCEPT
    
    PROC --> CACHE
    PROC --> MERGE
    PROC --> DETECT
    PROC --> HASH
    PROC --> QUAL
    
    PROC --> ANALYZE
    ANALYZE --> VIZ
```

## 5. Vector Database Layer Architecture

```mermaid
graph TB
    subgraph "Vector Layer"
        CLIENT[client.py]
        REPO[repository.py]
        MODELS[models.py]
        EXCEPT[exceptions.py]
        METRICS[metrics.py]
    end
    
    subgraph "Qdrant Database"
        COLLECT[Collections]
        POINTS[Points]
        SEARCH[Search API]
        CLUSTER[Clustering]
    end
    
    subgraph "Operations"
        INSERT[Insert Operations]
        SEARCH_OP[Search Operations]
        UPDATE[Update Operations]
        DELETE[Delete Operations]
    end
    
    CLIENT --> REPO
    REPO --> MODELS
    REPO --> EXCEPT
    REPO --> METRICS
    
    CLIENT --> COLLECT
    CLIENT --> POINTS
    CLIENT --> SEARCH
    CLIENT --> CLUSTER
    
    REPO --> INSERT
    REPO --> SEARCH_OP
    REPO --> UPDATE
    REPO --> DELETE
```

## 6. Embedding Service Architecture

```mermaid
graph TB
    subgraph "Embedding Service"
        SERVICE[service.py]
        MODELS[models.py]
        PREPROC[preprocessing.py]
        CHUNK[chunking.py]
    end
    
    subgraph "Model Registry"
        MINI[all-MiniLM-L6-v2]
        MPNET[all-mpnet-base-v2]
        MULTI[multilingual-e5-large]
        CUSTOM[Custom Models]
    end
    
    subgraph "Preprocessing Pipeline"
        CLEAN[Text Cleaning]
        NORMALIZE[Normalization]
        TOKENIZE[Tokenization]
        FILTER[Content Filtering]
    end
    
    subgraph "External APIs"
        OPENAI[OpenAI API]
        HUGGINGFACE[HuggingFace]
        LOCAL[Local Models]
    end
    
    SERVICE --> MODELS
    SERVICE --> PREPROC
    SERVICE --> CHUNK
    
    MODELS --> MINI
    MODELS --> MPNET
    MODELS --> MULTI
    MODELS --> CUSTOM
    
    PREPROC --> CLEAN
    PREPROC --> NORMALIZE
    PREPROC --> TOKENIZE
    PREPROC --> FILTER
    
    MODELS --> OPENAI
    MODELS --> HUGGINGFACE
    MODELS --> LOCAL
```

## 7. Data Flow Architecture

```mermaid
sequenceDiagram
    participant U as User/Webhook
    participant API as FastAPI
    participant CONN as Connector
    participant CHUNK as Chunking
    participant EMB as Embedding
    participant VEC as Vector DB
    participant QD as Qdrant
    
    U->>API: Content Input
    API->>CONN: Process Content
    CONN->>CHUNK: Chunk Content
    CHUNK->>EMB: Generate Embeddings
    EMB->>VEC: Store Vectors
    VEC->>QD: Database Operations
    QD-->>VEC: Results
    VEC-->>EMB: Confirmation
    EMB-->>CHUNK: Embeddings
    CHUNK-->>CONN: Chunked Data
    CONN-->>API: Processed Content
    API-->>U: Response
```

## 8. Configuration Architecture

```mermaid
graph TB
    subgraph "Configuration Sources"
        ENV[Environment Variables]
        SECRETS[Secret Files]
        DEFAULTS[Default Values]
    end
    
    subgraph "Settings Categories"
        APP[Application Settings]
        DB[Database Settings]
        API[External API Settings]
        GITHUB[GitHub Settings]
        SLACK[Slack Settings]
        EMB[Embedding Settings]
        OBS[Observability Settings]
        SERVER[Server Settings]
    end
    
    subgraph "Configuration Management"
        SETTINGS[Settings Class]
        VALIDATION[Pydantic Validation]
        SECURE[Secret Management]
    end
    
    ENV --> SETTINGS
    SECRETS --> SETTINGS
    DEFAULTS --> SETTINGS
    
    SETTINGS --> VALIDATION
    SETTINGS --> SECURE
    
    VALIDATION --> APP
    VALIDATION --> DB
    VALIDATION --> API
    VALIDATION --> GITHUB
    VALIDATION --> SLACK
    VALIDATION --> EMB
    VALIDATION --> OBS
    VALIDATION --> SERVER
```

## 9. Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DEV_COMPOSE[docker-compose.dev.yml]
        DEV_OVERRIDE[docker-compose.override.yml]
    end
    
    subgraph "Production Environment"
        PROD_COMPOSE[docker-compose.prod.yml]
        NGINX[Nginx Configuration]
        SSL[SSL Certificates]
    end
    
    subgraph "Testing Environment"
        TEST_COMPOSE[docker-compose.test.yml]
        TEST_SCRIPTS[Test Scripts]
    end
    
    subgraph "Infrastructure Services"
        QDRANT[Qdrant Container]
        JAEGER[Jaeger Container]
        PROMETHEUS[Prometheus Container]
        GRAFANA[Grafana Container]
    end
    
    subgraph "Application Container"
        SAATHY[Saathy App]
        UVICORN[Uvicorn Server]
        WORKERS[Worker Processes]
    end
    
    DEV_COMPOSE --> SAATHY
    PROD_COMPOSE --> SAATHY
    TEST_COMPOSE --> SAATHY
    
    PROD_COMPOSE --> NGINX
    NGINX --> SSL
    
    SAATHY --> UVICORN
    UVICORN --> WORKERS
    
    PROD_COMPOSE --> QDRANT
    PROD_COMPOSE --> JAEGER
    PROD_COMPOSE --> PROMETHEUS
    PROD_COMPOSE --> GRAFANA
```

## 10. Monitoring and Observability Architecture

```mermaid
graph TB
    subgraph "Application Telemetry"
        OTEL[OpenTelemetry]
        TRACES[Distributed Traces]
        LOGS[Structured Logging]
        METRICS[Application Metrics]
    end
    
    subgraph "Infrastructure Monitoring"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        ALERTS[Alerting Rules]
    end
    
    subgraph "Tracing System"
        JAEGER[Jaeger]
        TRACE_UI[Tracing UI]
        TRACE_STORAGE[Trace Storage]
    end
    
    subgraph "Health Checks"
        HEALTH[Health Endpoints]
        READY[Readiness Checks]
        LIVENESS[Liveness Probes]
    end
    
    OTEL --> TRACES
    OTEL --> LOGS
    OTEL --> METRICS
    
    TRACES --> JAEGER
    LOGS --> PROMETHEUS
    METRICS --> PROMETHEUS
    
    JAEGER --> TRACE_UI
    JAEGER --> TRACE_STORAGE
    
    PROMETHEUS --> GRAFANA
    PROMETHEUS --> ALERTS
    
    HEALTH --> READY
    HEALTH --> LIVENESS
```

## 11. API Endpoints Architecture

```mermaid
graph TB
    subgraph "Health & Configuration"
        HEALTH[/healthz]
        READY[/readyz]
        CONFIG[/config]
    end
    
    subgraph "GitHub Connector"
        GH_WEBHOOK[/webhooks/github]
        GH_STATUS[/connectors/github/status]
        GH_SYNC[/connectors/github/sync]
    end
    
    subgraph "Slack Connector"
        SL_STATUS[/connectors/slack/status]
        SL_START[/connectors/slack/start]
        SL_STOP[/connectors/slack/stop]
        SL_CHANNELS[/connectors/slack/channels]
        SL_PROCESS[/connectors/slack/process]
    end
    
    subgraph "Content Processing"
        PROCESS[/process]
        CHUNK[/chunk]
        EMBED[/embed]
        SEARCH[/search]
    end
    
    subgraph "Vector Operations"
        VEC_INSERT[/vectors/insert]
        VEC_SEARCH[/vectors/search]
        VEC_UPDATE[/vectors/update]
        VEC_DELETE[/vectors/delete]
    end
    
    HEALTH --> READY
    READY --> CONFIG
    
    GH_WEBHOOK --> GH_STATUS
    GH_STATUS --> GH_SYNC
    
    SL_STATUS --> SL_START
    SL_START --> SL_STOP
    SL_STOP --> SL_CHANNELS
    SL_CHANNELS --> SL_PROCESS
    
    PROCESS --> CHUNK
    CHUNK --> EMBED
    EMBED --> SEARCH
    
    VEC_INSERT --> VEC_SEARCH
    VEC_SEARCH --> VEC_UPDATE
    VEC_UPDATE --> VEC_DELETE
```

## 12. Component Dependencies Graph

```mermaid
graph TB
    subgraph "Core Dependencies"
        FASTAPI[FastAPI]
        PYDANTIC[Pydantic]
        UVICORN[Uvicorn]
        APSCHED[APScheduler]
    end
    
    subgraph "External Services"
        QDRANT[Qdrant Client]
        OPENAI[OpenAI]
        GITHUB[GitHub API]
        SLACK[Slack API]
    end
    
    subgraph "AI/ML Libraries"
        SENTENCE_TRANSFORMERS[Sentence Transformers]
        TORCH[PyTorch]
        TRANSFORMERS[Transformers]
    end
    
    subgraph "Utilities"
        LOGGING[Logging]
        ASYNCIO[asyncio]
        TYPING[typing]
        OS[os]
    end
    
    subgraph "Development Tools"
        POETRY[Poetry]
        PRE_COMMIT[pre-commit]
        PYTEST[pytest]
        BLACK[black]
    end
    
    FASTAPI --> PYDANTIC
    FASTAPI --> UVICORN
    FASTAPI --> APSCHED
    
    QDRANT --> FASTAPI
    OPENAI --> FASTAPI
    GITHUB --> FASTAPI
    SLACK --> FASTAPI
    
    SENTENCE_TRANSFORMERS --> TORCH
    TORCH --> TRANSFORMERS
    
    LOGGING --> FASTAPI
    ASYNCIO --> FASTAPI
    TYPING --> FASTAPI
    OS --> FASTAPI
    
    POETRY --> FASTAPI
    PRE_COMMIT --> FASTAPI
    PYTEST --> FASTAPI
    BLACK --> FASTAPI
```

## Usage

These graphs provide different perspectives on the Saathy architecture:

1. **High-Level System Architecture**: Shows the overall system components and their relationships
2. **Application Layer Architecture**: Details the internal application structure
3. **Connector Framework Architecture**: Focuses on the extensible connector system
4. **Chunking System Architecture**: Shows the modular chunking strategies
5. **Vector Database Layer Architecture**: Details the vector storage implementation
6. **Embedding Service Architecture**: Shows the embedding model management
7. **Data Flow Architecture**: Illustrates the sequence of operations
8. **Configuration Architecture**: Shows how configuration is managed
9. **Deployment Architecture**: Details the containerized deployment
10. **Monitoring and Observability Architecture**: Shows the observability stack
11. **API Endpoints Architecture**: Maps all available API endpoints
12. **Component Dependencies Graph**: Shows library and service dependencies

Each graph can be rendered using Mermaid-compatible tools or viewed directly in GitHub/GitLab markdown files.