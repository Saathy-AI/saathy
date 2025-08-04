# Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Architecture](#component-architecture)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Design Patterns](#design-patterns)
8. [Security Architecture](#security-architecture)
9. [Scalability Considerations](#scalability-considerations)
10. [Performance Characteristics](#performance-characteristics)
11. [Monitoring & Observability](#monitoring--observability)
12. [Deployment Architecture](#deployment-architecture)

## System Overview

Saathy is a FastAPI-based AI application foundation designed to build personal AI copilots with advanced content processing capabilities. The system integrates multiple data sources, processes content through intelligent chunking strategies, and provides vector search capabilities for semantic retrieval.

### Core Capabilities

- **Content Processing**: Multi-source content ingestion and processing
- **Intelligent Chunking**: Content-aware chunking strategies for different data types
- **Vector Storage**: High-performance vector database integration
- **Connector Framework**: Extensible connector system for external platforms
- **Embedding Service**: Multi-model embedding generation
- **Real-time Processing**: Event-driven content processing pipeline
- **Observability**: Comprehensive monitoring and tracing

## Architecture Principles

### 1. Modularity
- **Loose Coupling**: Components interact through well-defined interfaces
- **High Cohesion**: Related functionality is grouped together
- **Separation of Concerns**: Each component has a single responsibility

### 2. Scalability
- **Horizontal Scaling**: Support for multiple instances
- **Vertical Scaling**: Resource optimization for single instances
- **Stateless Design**: No session state in application layer

### 3. Reliability
- **Fault Tolerance**: Graceful handling of component failures
- **Health Monitoring**: Comprehensive health checks
- **Error Recovery**: Automatic recovery mechanisms

### 4. Observability
- **Structured Logging**: Consistent log format across components
- **Distributed Tracing**: End-to-end request tracing
- **Metrics Collection**: Performance and business metrics

### 5. Security
- **Defense in Depth**: Multiple security layers
- **Least Privilege**: Minimal required permissions
- **Secure by Default**: Secure configurations out of the box

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  Web Clients  │  Mobile Apps  │  API Clients  │  Webhooks      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Nginx (Reverse Proxy)  │  Rate Limiting  │  SSL Termination  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application  │  Request Routing  │  Middleware Stack │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  Chunking Service  │  Embedding Service  │  Connector Service │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  Vector Database  │  Cache Layer  │  File Storage  │  Logs     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  Container Runtime  │  Monitoring Stack  │  Backup Systems   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. API Layer (`src/saathy/api.py`)

**Purpose**: HTTP API interface and request handling

**Key Components**:
- **FastAPI Application**: Main application instance
- **Router Modules**: Endpoint organization
- **Middleware Stack**: Request/response processing
- **Error Handlers**: Centralized error handling
- **Dependency Injection**: Service injection

**Design Patterns**:
- **Dependency Injection**: Services injected via FastAPI dependencies
- **Middleware Pattern**: Cross-cutting concerns handled by middleware
- **Router Pattern**: Endpoints organized by functionality

```python
# Example: API Layer Structure
app = FastAPI(
    title="Saathy API",
    description="AI-powered content processing platform",
    version="0.1.0"
)

# Middleware stack
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(LoggingMiddleware, ...)
app.add_middleware(TracingMiddleware, ...)

# Router organization
app.include_router(health_router, prefix="/healthz", tags=["health"])
app.include_router(connector_router, prefix="/connectors", tags=["connectors"])
app.include_router(embedding_router, prefix="/embed", tags=["embedding"])
```

### 2. Configuration Management (`src/saathy/config.py`)

**Purpose**: Centralized configuration management

**Key Components**:
- **Pydantic Settings**: Type-safe configuration
- **Environment Variables**: External configuration
- **Validation**: Configuration validation
- **Defaults**: Sensible defaults

**Design Patterns**:
- **Singleton Pattern**: Single configuration instance
- **Builder Pattern**: Configuration building with validation
- **Factory Pattern**: Environment-specific configuration

```python
# Example: Configuration Structure
class Settings(BaseSettings):
    # Application settings
    app_name: str = "Saathy"
    environment: str = "development"
    debug: bool = False
    
    # Database settings
    qdrant_url: str
    qdrant_api_key: Optional[str] = None
    
    # Service settings
    default_embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_size: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 3. Chunking System (`src/saathy/chunking/`)

**Purpose**: Intelligent content chunking for vector storage

**Key Components**:
- **ChunkingProcessor**: Main orchestration component
- **Strategy Pattern**: Multiple chunking strategies
- **Quality Validator**: Chunk quality assessment
- **Cache Manager**: Chunk caching
- **Content Detector**: Content type detection

**Design Patterns**:
- **Strategy Pattern**: Different chunking algorithms
- **Factory Pattern**: Strategy creation
- **Observer Pattern**: Quality monitoring
- **Cache Pattern**: Performance optimization

```python
# Example: Chunking System Structure
class ChunkingProcessor:
    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.strategies = self._load_strategies()
        self.cache = ChunkCache(config.cache_size)
        self.validator = QualityValidator()
    
    def chunk_content(self, content: str, strategy: str = None) -> List[Chunk]:
        # Strategy selection
        strategy = strategy or self._detect_strategy(content)
        chunker = self.strategies[strategy]
        
        # Chunking with caching
        cache_key = self._generate_cache_key(content, strategy)
        if cached := self.cache.get(cache_key):
            return cached
        
        # Process and validate
        chunks = chunker.chunk(content)
        validated_chunks = [self.validator.validate(chunk) for chunk in chunks]
        
        # Cache results
        self.cache.set(cache_key, validated_chunks)
        return validated_chunks
```

### 4. Connector Framework (`src/saathy/connectors/`)

**Purpose**: External platform integration

**Key Components**:
- **Base Connector**: Abstract connector interface
- **GitHub Connector**: GitHub integration
- **Slack Connector**: Slack integration
- **Content Processor**: Content processing pipeline
- **Event Handler**: Event processing

**Design Patterns**:
- **Template Method Pattern**: Common connector behavior
- **Observer Pattern**: Event handling
- **Pipeline Pattern**: Content processing
- **Adapter Pattern**: Platform-specific adapters

```python
# Example: Connector Framework Structure
class BaseConnector(ABC):
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.processor = ContentProcessor()
        self.event_handlers = self._register_handlers()
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to platform"""
        pass
    
    @abstractmethod
    def process_events(self) -> List[ProcessedEvent]:
        """Process platform events"""
        pass
    
    def process_content(self, content: str) -> List[Chunk]:
        """Process content through pipeline"""
        return self.processor.process(content)

class GitHubConnector(BaseConnector):
    def connect(self) -> bool:
        # GitHub-specific connection logic
        pass
    
    def process_events(self) -> List[ProcessedEvent]:
        # GitHub webhook event processing
        pass
```

### 5. Embedding Service (`src/saathy/embedding/`)

**Purpose**: Vector embedding generation

**Key Components**:
- **Model Registry**: Embedding model management
- **Preprocessor**: Content preprocessing
- **Embedding Generator**: Vector generation
- **Cache Manager**: Embedding caching
- **Quality Assessor**: Embedding quality

**Design Patterns**:
- **Registry Pattern**: Model management
- **Factory Pattern**: Model creation
- **Cache Pattern**: Performance optimization
- **Strategy Pattern**: Different embedding approaches

```python
# Example: Embedding Service Structure
class EmbeddingService:
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model_registry = ModelRegistry()
        self.preprocessor = ContentPreprocessor()
        self.cache = EmbeddingCache(config.cache_size)
    
    async def generate_embedding(
        self, 
        content: str, 
        model: str = None
    ) -> Embedding:
        # Model selection
        model = model or self.config.default_model
        embedding_model = self.model_registry.get_model(model)
        
        # Preprocessing
        processed_content = self.preprocessor.preprocess(content)
        
        # Cache check
        cache_key = self._generate_cache_key(processed_content, model)
        if cached := self.cache.get(cache_key):
            return cached
        
        # Generate embedding
        embedding = await embedding_model.embed(processed_content)
        
        # Cache result
        self.cache.set(cache_key, embedding)
        return embedding
```

### 6. Vector Database Layer (`src/saathy/vector/`)

**Purpose**: Vector storage and retrieval

**Key Components**:
- **Qdrant Client**: Database client wrapper
- **Repository Pattern**: Data access abstraction
- **Model Definitions**: Vector data models
- **Metrics Collector**: Performance metrics
- **Connection Pool**: Connection management

**Design Patterns**:
- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Client creation
- **Pool Pattern**: Connection management
- **Observer Pattern**: Metrics collection

```python
# Example: Vector Database Structure
class VectorRepository:
    def __init__(self, client: QdrantClient):
        self.client = client
        self.metrics = MetricsCollector()
    
    async def store_vectors(
        self, 
        collection: str, 
        vectors: List[Vector]
    ) -> bool:
        try:
            result = await self.client.upsert(
                collection_name=collection,
                points=vectors
            )
            self.metrics.record_operation("store", len(vectors))
            return result
        except Exception as e:
            self.metrics.record_error("store", str(e))
            raise
    
    async def search_vectors(
        self, 
        collection: str, 
        query_vector: List[float], 
        limit: int = 10
    ) -> List[SearchResult]:
        try:
            results = await self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit
            )
            self.metrics.record_operation("search", 1)
            return results
        except Exception as e:
            self.metrics.record_error("search", str(e))
            raise
```

## Data Flow

### 1. Content Ingestion Flow

```
External Platform (GitHub/Slack)
           │
           ▼
    Webhook/Event Handler
           │
           ▼
    Content Processor
           │
           ▼
    Chunking Processor
           │
           ▼
    Embedding Service
           │
           ▼
    Vector Database
```

### 2. Search Request Flow

```
Client Request
      │
      ▼
API Gateway (Nginx)
      │
      ▼
FastAPI Application
      │
      ▼
Search Service
      │
      ▼
Embedding Service (Query)
      │
      ▼
Vector Database (Search)
      │
      ▼
Results Processing
      │
      ▼
Client Response
```

### 3. Health Check Flow

```
Health Check Request
         │
         ▼
Health Check Endpoint
         │
         ▼
Dependency Health Checks
    ├── Qdrant Connection
    ├── Embedding Service
    ├── Connector Status
    └── System Resources
         │
         ▼
Aggregated Health Response
```

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and settings management
- **Uvicorn/Gunicorn**: ASGI/WSGI servers

### Vector Database
- **Qdrant**: High-performance vector database
- **Qdrant Client**: Python client library

### Embedding Models
- **SentenceTransformers**: Local embedding models
- **OpenAI API**: Cloud-based embedding service
- **PyTorch**: Deep learning framework

### Connectors
- **GitHub API**: GitHub integration
- **Slack SDK**: Slack integration
- **aiohttp**: Async HTTP client

### Monitoring & Observability
- **OpenTelemetry**: Distributed tracing
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Structlog**: Structured logging

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy and load balancing

### Development Tools
- **Poetry**: Dependency management
- **Ruff**: Fast Python linter and formatter
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks

## Design Patterns

### 1. Repository Pattern
Used in the vector database layer to abstract data access:

```python
class VectorRepository(ABC):
    @abstractmethod
    async def store_vectors(self, vectors: List[Vector]) -> bool:
        pass
    
    @abstractmethod
    async def search_vectors(self, query: Vector, limit: int) -> List[Vector]:
        pass
```

### 2. Strategy Pattern
Used in the chunking system for different chunking strategies:

```python
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, content: str) -> List[Chunk]:
        pass

class FixedSizeChunker(ChunkingStrategy):
    def chunk(self, content: str) -> List[Chunk]:
        # Fixed-size chunking implementation
        pass

class SemanticChunker(ChunkingStrategy):
    def chunk(self, content: str) -> List[Chunk]:
        # Semantic chunking implementation
        pass
```

### 3. Factory Pattern
Used for creating instances of different components:

```python
class ModelFactory:
    @staticmethod
    def create_model(model_type: str, config: ModelConfig) -> EmbeddingModel:
        if model_type == "local":
            return LocalEmbeddingModel(config)
        elif model_type == "openai":
            return OpenAIEmbeddingModel(config)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
```

### 4. Observer Pattern
Used for event handling and metrics collection:

```python
class MetricsObserver(ABC):
    @abstractmethod
    def update(self, event: str, data: Dict[str, Any]):
        pass

class PrometheusMetrics(MetricsObserver):
    def update(self, event: str, data: Dict[str, Any]):
        # Update Prometheus metrics
        pass
```

### 5. Pipeline Pattern
Used in content processing:

```python
class ContentPipeline:
    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages
    
    def process(self, content: str) -> ProcessedContent:
        result = content
        for stage in self.stages:
            result = stage.process(result)
        return result
```

## Security Architecture

### 1. Authentication & Authorization
- **API Key Authentication**: For external API access
- **Webhook Signature Verification**: For GitHub/Slack webhooks
- **Rate Limiting**: Per-client request limiting
- **CORS Configuration**: Cross-origin resource sharing

### 2. Data Security
- **Encryption at Rest**: Sensitive data encryption
- **Encryption in Transit**: TLS/SSL for all communications
- **Secrets Management**: Environment-based secrets
- **Input Validation**: Comprehensive input sanitization

### 3. Network Security
- **Firewall Configuration**: Network access control
- **Reverse Proxy**: SSL termination and security headers
- **DDoS Protection**: Rate limiting and request filtering
- **Security Headers**: HTTP security headers

### 4. Container Security
- **Non-root Users**: Containers run as non-root
- **Read-only Filesystems**: Immutable container images
- **Resource Limits**: CPU and memory constraints
- **Security Scanning**: Container vulnerability scanning

## Scalability Considerations

### 1. Horizontal Scaling
- **Stateless Design**: No session state in application
- **Load Balancing**: Multiple API instances
- **Database Sharding**: Vector database clustering
- **Cache Distribution**: Distributed caching

### 2. Vertical Scaling
- **Resource Optimization**: Efficient resource usage
- **Connection Pooling**: Database connection management
- **Memory Management**: Optimized memory usage
- **CPU Optimization**: Parallel processing

### 3. Performance Optimization
- **Caching Strategy**: Multi-level caching
- **Batch Processing**: Bulk operations
- **Async Processing**: Non-blocking operations
- **CDN Integration**: Content delivery optimization

## Performance Characteristics

### 1. Response Times
- **Health Checks**: < 100ms
- **API Endpoints**: < 500ms (95th percentile)
- **Vector Search**: < 1s (95th percentile)
- **Content Processing**: < 5s (95th percentile)

### 2. Throughput
- **API Requests**: 1000+ requests/second
- **Vector Operations**: 100+ operations/second
- **Content Processing**: 50+ documents/minute
- **Concurrent Users**: 100+ simultaneous users

### 3. Resource Usage
- **Memory**: 2-4GB per API instance
- **CPU**: 2-4 cores per API instance
- **Storage**: 50-100GB for vector database
- **Network**: 100Mbps+ bandwidth

## Monitoring & Observability

### 1. Metrics Collection
- **Application Metrics**: Request rates, response times, error rates
- **System Metrics**: CPU, memory, disk, network usage
- **Business Metrics**: Content processed, searches performed
- **Custom Metrics**: Domain-specific measurements

### 2. Logging Strategy
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Correlation IDs**: Request tracing across services
- **Log Aggregation**: Centralized log collection

### 3. Distributed Tracing
- **Request Tracing**: End-to-end request tracking
- **Service Dependencies**: Service interaction mapping
- **Performance Analysis**: Bottleneck identification
- **Error Tracking**: Error propagation analysis

### 4. Alerting
- **Health Checks**: Service availability monitoring
- **Performance Alerts**: Response time thresholds
- **Error Alerts**: Error rate monitoring
- **Resource Alerts**: Resource usage thresholds

## Deployment Architecture

### 1. Container Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                       │
├─────────────────────────────────────────────────────────┤
│  Nginx Container  │  API Container  │  Qdrant Container │
│  (Port 80/443)    │  (Port 8000)    │  (Port 6333)      │
└─────────────────────────────────────────────────────────┘
                                │
                    ┌─────────────────────────┐
                    │   Monitoring Stack      │
                    │ (Prometheus + Grafana)  │
                    └─────────────────────────┘
```

### 2. Service Discovery
- **Docker Compose**: Service name resolution
- **Environment Variables**: Configuration injection
- **Health Checks**: Service availability verification
- **Dependency Management**: Service startup ordering

### 3. Configuration Management
- **Environment Files**: Per-environment configuration
- **Secrets Management**: Secure secret handling
- **Configuration Validation**: Runtime configuration checks
- **Hot Reloading**: Configuration updates without restart

This architecture documentation provides a comprehensive overview of the Saathy system design, helping developers understand the system structure, make informed decisions, and contribute effectively to the project.