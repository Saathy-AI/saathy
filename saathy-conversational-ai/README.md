# Saathy Conversational Intelligence Layer

An intelligent conversational AI system that transforms Saathy from a "push-only" proactive system into a true AI copilot. Users can interact with Saathy's cross-platform intelligence through natural conversation.

## 🚀 Features

### Phase 1: Foundation Layer ✅
- **Chat Session Architecture**: Complete session management with PostgreSQL and Redis
- **Information Needs Analysis**: Pattern-based intent classification with GPT-4 enhancement
- **Hybrid Retrieval Engine**: Combines vector search (Qdrant), structured search (Redis), and action retrieval
- **Real-time Chat Interface**: React frontend with WebSocket support

### Phase 2: Agentic Intelligence (In Progress)
- **LangGraph Multi-Agent System**: Orchestrates intelligent context retrieval
- **Context Sufficiency Evaluation**: Determines if retrieved context is complete
- **Reciprocal Rank Fusion**: Advanced result ranking algorithm
- **Dynamic Context Expansion**: Intelligently expands context when needed

### Phase 3: Intelligence Optimization (Planned)
- **COMEDY Memory Framework**: Conversation memory compression
- **Temporal Relevance Weighting**: Time-based context scoring
- **Performance Optimization**: Caching, parallel execution, result streaming
- **Quality Metrics & Learning**: Continuous improvement based on user feedback

## 🏗️ Architecture

```
saathy-conversational-ai/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── models/            # Data models
│   │   ├── services/          # Business logic
│   │   ├── retrieval/         # Retrieval engines
│   │   ├── agents/            # LangGraph agents
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

### Frontend Configuration

Environment variables:
- `REACT_APP_API_URL`: Backend API URL (default: http://localhost:8000)

## 📚 API Endpoints

### Chat Endpoints

- `POST /api/chat/sessions` - Create new chat session
- `POST /api/chat/sessions/{id}/messages` - Send message
- `GET /api/chat/sessions/{id}/history` - Get conversation history
- `DELETE /api/chat/sessions/{id}` - End session
- `WS /api/chat/ws/{session_id}` - WebSocket for real-time chat

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