# Saathy Conversational Intelligence Layer

An intelligent conversational AI system that transforms Saathy from a "push-only" proactive system into a true AI copilot. Users can interact with Saathy's cross-platform intelligence through natural conversation.

## 🚀 Features

### Phase 1: Foundation Layer ✅
- **Chat Session Architecture**: Complete session management with PostgreSQL and Redis
- **Information Needs Analysis**: Pattern-based intent classification with GPT-4 enhancement
- **Hybrid Retrieval Engine**: Combines vector search (Qdrant), structured search (Redis), and action retrieval
- **Real-time Chat Interface**: React frontend with WebSocket support

### Phase 2: Agentic Intelligence ✅
- **LangGraph Multi-Agent System**: 5 specialized agents working in orchestrated flow
- **Context Sufficiency Evaluation**: Multi-dimensional scoring (entity, temporal, platform, GPT-4)
- **Reciprocal Rank Fusion**: Advanced result merging with configurable k-parameter
- **Dynamic Context Expansion**: Progressive strategies based on identified gaps

### Phase 3: Intelligence Optimization ✅
- **COMEDY Memory Framework**: Sophisticated conversation compression with user profiling
- **Performance Optimization**: Multi-level caching with fuzzy matching
- **Quality Metrics System**: Prometheus-based comprehensive tracking
- **Learning Loops**: Real-time parameter optimization based on feedback

## 🏗️ Architecture

```
saathy-conversational-ai/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints (v1 & v2)
│   │   ├── models/            # Data models
│   │   ├── services/          # Business logic
│   │   ├── retrieval/         # Retrieval engines
│   │   ├── agents/            # LangGraph agents (Phase 2)
│   │   │   ├── context_orchestration.py
│   │   │   ├── information_analyzer.py
│   │   │   ├── context_retriever.py
│   │   │   ├── sufficiency_evaluator.py
│   │   │   ├── context_expander.py
│   │   │   └── response_generator.py
│   │   ├── memory/            # COMEDY framework (Phase 3)
│   │   ├── optimization/      # Caching & performance
│   │   ├── metrics/           # Quality tracking & learning
│   │   └── utils/             # Utilities
│   ├── config/                # Configuration
│   └── requirements.txt       # Python dependencies
│
└── frontend/                  # React frontend
    ├── src/
    │   ├── components/        # UI components
    │   ├── services/          # API services
    │   ├── hooks/             # Custom hooks
    │   └── types/             # TypeScript types
    └── package.json           # Node dependencies
```

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Redis, Qdrant
- **AI/ML**: OpenAI GPT-4, LangChain, LangGraph
- **Frontend**: React, TypeScript, Tailwind CSS, WebSockets
- **Storage**: PostgreSQL, Redis, Qdrant Vector DB

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 14+
- Redis 7+
- Qdrant (optional, can use cloud version)

## 🚀 Quick Start

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd saathy-conversational-ai
   ```

2. **Set up Python environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration:
   # - DATABASE_URL
   # - REDIS_URL
   # - OPENAI_API_KEY
   # - QDRANT connection details
   ```

4. **Start the backend**
   ```bash
   python -m app.main
   ```

   The API will be available at `http://localhost:8000`
   API documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**
   ```bash
   npm start
   ```

   The app will open at `http://localhost:3000`

## 🔧 Configuration

### Backend Configuration

Key settings in `.env`:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `QDRANT_HOST/PORT`: Qdrant vector database
- `SESSION_TTL_HOURS`: Session expiration time
- `MAX_CONTEXT_TOKENS`: Maximum tokens for context

### Agentic System Configuration

Advanced settings for Phase 2 & 3:
- `MAX_EXPANSION_ATTEMPTS`: Maximum context expansion loops (default: 3)
- `SUFFICIENCY_THRESHOLD`: Minimum context sufficiency score (default: 0.7)
- `RRF_K`: Reciprocal Rank Fusion parameter (default: 60)
- `COMPRESSION_THRESHOLD`: Turns before memory compression (default: 5)
- `CACHE_TTL_QUERY`: Query cache TTL in seconds (default: 300)
- `LEARNING_RATE`: Parameter optimization learning rate (default: 0.1)

### Frontend Configuration

Environment variables:
- `REACT_APP_API_URL`: Backend API URL (default: http://localhost:8000)

## 📚 API Endpoints

### v1 Endpoints (Basic Chat)
- `POST /api/chat/sessions` - Create new chat session
- `POST /api/chat/sessions/{id}/messages` - Send message
- `GET /api/chat/sessions/{id}/history` - Get conversation history
- `DELETE /api/chat/sessions/{id}` - End session
- `WS /api/chat/ws/{session_id}` - WebSocket for real-time chat

### v2 Endpoints (Agentic Intelligence)
- `POST /api/v2/chat/sessions` - Create session with agentic system
- `POST /api/v2/chat/sessions/{id}/messages` - Send message (multi-agent processing)
- `POST /api/v2/chat/sessions/{id}/feedback` - Submit user feedback
- `GET /api/v2/chat/sessions/{id}/metrics` - Get session metrics
- `GET /api/v2/chat/metrics/system` - Get system-wide metrics
- `GET /api/v2/chat/analytics/export` - Export analytics data
- `WS /api/v2/chat/sessions/{id}/ws` - WebSocket with typing indicators
- `GET /api/v2/chat/health` - Service health check

## 🧪 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend
black app/
ruff app/
mypy app/

# Frontend
npm run lint
npm run type-check
```

## 💡 Usage Examples

### Basic Chat (v1)
```python
# Simple query processing
response = await chat_service.process_message(
    session_id,
    ChatMessage(content="What's the status of the auth bug?"),
    db
)
```

### Agentic Chat (v2)
```python
# Multi-agent processing with context expansion
response = await agentic_chat_service.process_message(
    session_id,
    ChatMessage(content="What happened with the auth bug yesterday?"),
    db
)

# Submit feedback for learning
await agentic_chat_service.process_user_feedback(
    session_id,
    {
        "relevance_score": 0.9,
        "completeness_score": 0.8,
        "helpful": True
    }
)

# Get session metrics
metrics = await agentic_chat_service.get_session_metrics(session_id)
```

## 📊 Monitoring & Analytics

The system provides comprehensive monitoring through:

1. **Prometheus Metrics**
   - Response times
   - Sufficiency scores
   - Cache hit rates
   - Error rates

2. **Session Analytics**
   - Turn-by-turn metrics
   - Intent distribution
   - Expansion patterns

3. **System Performance**
   - Learning optimization status
   - Parameter trends
   - User satisfaction tracking

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Production Considerations

1. **Security**:
   - Implement proper authentication (JWT tokens)
   - Use HTTPS in production
   - Secure WebSocket connections

2. **Scaling**:
   - Use Redis pub/sub for WebSocket scaling
   - Implement connection pooling
   - Consider using a message queue for async processing

3. **Monitoring**:
   - Add Prometheus metrics
   - Implement structured logging
   - Set up error tracking (Sentry)

## 📊 Performance Targets

- Response time: <2 seconds (p95)
- Context quality: >85% user satisfaction
- Concurrent users: 100+ simultaneous sessions
- Conversation depth: 20+ turns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License.