# Saathy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com/)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://docs.saathy.ai)

An AI copilot that proactively shadows your work across platforms and suggests actionable next steps with full context. While others make you ask questions, Saathy tells you what to do next.

## ✨ Core Value Proposition

**Proactive Action Intelligence**: Saathy's V1 core differentiator is its ability to:
- **Shadow** your activity across Slack, GitHub, and Notion in real-time 
- **Correlate** related events across platforms using advanced similarity algorithms
- **Synthesize** context from multi-platform activity into coherent insights
- **Generate** specific, actionable recommendations using GPT-4
- **Deliver** timely suggestions when you need them most

## 🏗️ Repository Structure

Saathy follows a monorepo architecture with clear service boundaries:

```
saathy/
├── apps/                       # Application services
│   ├── core-api/              # Core knowledge layer & connectors
│   ├── conversational-ai/     # Chat interface & intelligence
│   └── enterprise/            # Enterprise features (private)
├── packages/                   # Shared libraries
│   ├── saathy-core/          # Core models & interfaces
│   ├── saathy-connectors/    # Connector framework
│   ├── saathy-chunking/      # Text chunking strategies
│   ├── saathy-embedding/     # Embedding services
│   └── saathy-intelligence/  # AI/ML components
├── infrastructure/            # Infrastructure as Code
├── docs/                      # Documentation portal
├── tools/                     # Development tools
└── tests/                     # Cross-cutting tests
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Node.js 18+ (for frontend)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/saathy/saathy.git
   cd saathy
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the development environment**
   ```bash
   make dev
   ```

4. **Access the services**
   - Core API: http://localhost:8000
   - Conversational AI: http://localhost:8001
   - Frontend: http://localhost:3001
   - API Documentation: http://localhost:8000/api/docs

### Using Make Commands

```bash
make help         # Show all available commands
make dev          # Start development environment
make test         # Run all tests
make lint         # Run code linters
make docs-serve   # Serve documentation locally
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run with coverage
make test-cov

# Run specific service tests
pytest apps/core-api/tests/
pytest apps/conversational-ai/backend/tests/
```

## 📚 Documentation

Full documentation is available at [docs.saathy.ai](https://docs.saathy.ai) or run locally:

```bash
make docs-serve
# Visit http://localhost:8001
```

### Key Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [API Reference](docs/api/core-api.md)
- [Deployment Guide](docs/deployment/docker.md)
- [Contributing Guide](docs/development/contributing.md)

## 🔧 Configuration

Saathy uses environment variables for configuration. See [.env.example](.env.example) for all available options.

### Essential Configuration

- **OpenAI**: Set `OPENAI_API_KEY` for AI features
- **Connectors**: Configure tokens for GitHub, Slack, and Notion
- **Databases**: Configure Qdrant and PostgreSQL connections

## 🚢 Deployment

### Docker Deployment

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Or use the deployment script
./deploy.sh
```

### Kubernetes (Coming Soon)

Helm charts and Kubernetes manifests will be available in `infrastructure/kubernetes/`.

## 🏢 Enterprise Features

Saathy offers enterprise features including:

- Advanced connectors (Salesforce, Jira, etc.)
- SSO/SAML authentication
- Advanced analytics and reporting
- Compliance features (HIPAA, SOC2)
- Priority support

Contact sales@saathy.ai for enterprise licensing.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/development/contributing.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

Saathy is licensed under the MIT License. See [LICENSE](LICENSE) for details.

Enterprise features require a commercial license.

## 🆘 Support

- **Documentation**: [docs.saathy.ai](https://docs.saathy.ai)
- **Issues**: [GitHub Issues](https://github.com/saathy/saathy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/saathy/saathy/discussions)
- **Email**: support@saathy.ai

## 🔮 Roadmap

- [ ] Kubernetes deployment support
- [ ] Additional connectors (Microsoft Teams, Confluence)
- [ ] Mobile applications
- [ ] Self-hosted enterprise edition
- [ ] Advanced workflow automation

---

Built with ❤️ by the Saathy team
