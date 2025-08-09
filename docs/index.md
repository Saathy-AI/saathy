# Saathy Documentation

Welcome to the Saathy documentation portal. Saathy is an AI copilot that proactively shadows your work across platforms and suggests actionable next steps with full context.

## Quick Links

- [Getting Started](getting-started/installation.md)
- [Architecture Overview](architecture/overview.md)
- [API Reference](api/core-api.md)
- [Deployment Guide](deployment/docker.md)

## Documentation Structure

### Getting Started
- [Installation](getting-started/installation.md) - How to install and set up Saathy
- [Quick Start](getting-started/quickstart.md) - Get up and running in 5 minutes
- [Configuration](getting-started/configuration.md) - Configure Saathy for your needs

### Architecture
- [System Overview](architecture/overview.md) - High-level architecture
- [Service Architecture](architecture/services.md) - Microservices design
- [Data Flow](architecture/data-flow.md) - How data moves through the system
- [Architecture Decisions](architecture/decisions/) - ADRs and design rationale

### API Reference
- [Core API](api/core-api.md) - Knowledge layer and connectors API
- [Conversational AI API](api/conversational-ai.md) - Chat and intelligence API
- [WebSocket Events](api/websocket.md) - Real-time event streaming

### User Guides
- [Connector Setup](user-guides/connectors/) - Setting up GitHub, Slack, Notion
- [Intelligence Features](user-guides/intelligence.md) - Using AI features
- [Troubleshooting](user-guides/troubleshooting.md) - Common issues and solutions

### Development
- [Development Setup](development/setup.md) - Setting up development environment
- [Testing Guide](development/testing.md) - Writing and running tests
- [Contributing](development/contributing.md) - How to contribute to Saathy

### Deployment
- [Docker Deployment](deployment/docker.md) - Deploy with Docker
- [Production Setup](deployment/PRODUCTION_SETUP.md) - Production best practices
- [Monitoring Setup](deployment/monitoring.md) - Set up monitoring
- [Migration Guide](deployment/MIGRATION_GUIDE.md) - Migrate between versions

## Key Features

### 🧠 Proactive Intelligence
- Real-time event streaming from multiple platforms
- Cross-platform event correlation
- AI-powered action recommendations
- Smart timing for notifications

### 🔗 Platform Integrations
- **GitHub** - Track commits, PRs, issues
- **Slack** - Monitor conversations and mentions
- **Notion** - Sync documents and databases

### 🏗️ Technical Capabilities
- Vector-based content storage
- Advanced text chunking strategies
- Real-time WebSocket streaming
- OpenTelemetry observability

## Architecture Highlights

Saathy follows a microservices architecture with clear separation of concerns:

1. **Core API** - Handles connectors, embeddings, and vector storage
2. **Conversational AI** - Provides chat interface and intelligence
3. **Shared Packages** - Reusable components across services

## Getting Help

- [GitHub Issues](https://github.com/saathy/saathy/issues) - Report bugs or request features
- [Discussions](https://github.com/saathy/saathy/discussions) - Ask questions and share ideas
- [Contributing Guide](development/contributing.md) - Learn how to contribute

## License

Saathy is licensed under the MIT License. Enterprise features require a commercial license.