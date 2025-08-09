# Quick Start Guide

Welcome to Saathy! This guide will help you get up and running quickly.

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Git
- Make (optional but recommended)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/saathy.git
cd saathy
```

### 2. Set Up Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required for core functionality
QDRANT_URL=http://localhost:6333
REDIS_HOST=localhost
REDIS_PORT=6379

# Configure at least one connector
GITHUB_TOKEN=your_github_token
SLACK_BOT_TOKEN=your_slack_bot_token
NOTION_TOKEN=your_notion_token

# Optional: AI features
OPENAI_API_KEY=your_openai_key
```

### 3. Start Services

Using Make (recommended):

```bash
make setup
make dev
```

Or using Docker Compose directly:

```bash
docker-compose up -d
```

### 4. Verify Installation

Check service health:

```bash
curl http://localhost:8000/health
```

## First Steps

### 1. Configure a Connector

#### GitHub
```bash
curl -X POST http://localhost:8000/api/v1/github/sync \
  -H "Content-Type: application/json" \
  -d '{"full_sync": true}'
```

#### Slack
```bash
curl -X POST http://localhost:8000/api/v1/slack/start
```

#### Notion
```bash
curl -X POST http://localhost:8000/api/v1/notion/start
```

### 2. View AI Recommendations

Get personalized action items:

```bash
curl http://localhost:8000/api/v1/intelligence/actions/user/your-user-id
```

### 3. Stream Real-time Events

Connect to the event stream:

```bash
curl http://localhost:8000/api/v1/streaming/events/user/your-user-id
```

## Next Steps

- Read the [Architecture Overview](../architecture/overview.md)
- Set up [GitHub Integration](../user-guides/github-setup.md)
- Configure [Slack Integration](../user-guides/slack-setup.md)
- Explore [API Documentation](../api/reference.md)

## Troubleshooting

### Services Won't Start

Check Docker logs:

```bash
docker-compose logs -f
```

### Connection Errors

Ensure all services are running:

```bash
docker-compose ps
```

### Missing Dependencies

Install Python dependencies:

```bash
make setup
```

## Getting Help

- Check our [FAQ](../user-guides/faq.md)
- Join our [Community Discord](#)
- Open an [Issue on GitHub](#)