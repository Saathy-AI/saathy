# Saathy Testing Guide

## Current Status

After reviewing and fixing the codebase, here's what works and what doesn't:

### ✅ What Works

1. **Notion Connector**
   - Automatic polling every 5 minutes (configurable)
   - Manual sync via API endpoint
   - Processes and stores content in Qdrant

2. **Slack Connector** 
   - Real-time message processing (if Socket Mode is configured)
   - Manual sync endpoint for fetching recent messages
   - Scheduled sync every 15 minutes

3. **GitHub Connector**
   - Webhook-based real-time processing
   - Content processor integration fixed
   - Stores processed events in Qdrant

4. **Core Pipeline**
   - Embedding generation
   - Vector storage in Qdrant
   - Content processing

### ⚠️ Limitations

1. **GitHub**: No API polling (only webhooks)
2. **Slack**: Requires proper bot setup with Socket Mode
3. **Event Manager**: Not integrated (cross-platform correlation not working)

## Quick Start Testing

### 1. Start Dependencies

```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Start Redis (optional, for event streaming)
docker run -p 6379:6379 redis
```

### 2. Set Environment Variables

Create a `.env` file:

```bash
# Core
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-key-here

# GitHub (optional)
GITHUB_WEBHOOK_SECRET=your-secret
GITHUB_TOKEN=ghp_your-token
GITHUB_REPOSITORIES=owner/repo1,owner/repo2

# Slack (optional)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNELS=C1234567890

# Notion (optional)
NOTION_TOKEN=secret_your-token
NOTION_DATABASES=database-id-1
NOTION_PAGES=page-id-1
```

### 3. Run the Application

```bash
cd D:\saathy\saathy
python -m saathy
```

### 4. Test Endpoints

#### Test Pipeline Health
```bash
# Test if the pipeline works
curl http://localhost:8000/test-pipeline
```

#### Debug Connectors Status
```bash
# See detailed connector status
curl http://localhost:8000/debug/connectors
```

#### Manual Sync Operations

**Slack** (if configured):
```bash
# Sync last hour of messages from all channels
curl -X POST http://localhost:8000/manual-sync/slack?minutes=60

# Sync specific channel
curl -X POST "http://localhost:8000/manual-sync/slack?minutes=60&channel_id=C1234567890"
```

**GitHub** (if configured):
```bash
# Sync last 7 days of all activity
curl -X POST "http://localhost:8000/connectors/github/sync?repository=owner/repo-name"

# Sync specific event types
curl -X POST "http://localhost:8000/connectors/github/sync?repository=owner/repo-name&event_types=commits,issues"

# Sync last 30 days
curl -X POST "http://localhost:8000/connectors/github/sync?repository=owner/repo-name&days_back=30"
```

**Notion** (if configured):
```bash
# Full sync
curl -X POST http://localhost:8000/connectors/notion/sync

# Sync specific database
curl -X POST "http://localhost:8000/connectors/notion/sync?database_id=your-db-id"
```

#### Check Connector Status
```bash
# GitHub
curl http://localhost:8000/connectors/github/status

# Slack  
curl http://localhost:8000/connectors/slack/status

# Notion
curl http://localhost:8000/connectors/notion/status
```

### 5. Verify Data Storage

```bash
# Search stored content
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 10}'
```

## Troubleshooting

### Nothing is being stored in Qdrant

1. Check `/debug/connectors` - are connectors initialized?
2. Check `/test-pipeline` - does the pipeline work?
3. Check logs for errors
4. Ensure environment variables are set correctly

### Connectors show as not initialized

1. Check environment variables
2. Look at application logs during startup
3. Ensure all required tokens/secrets are provided

### Manual sync returns no data

1. For Slack: Ensure bot is in the channels
2. For Notion: Ensure integration has access to databases/pages
3. Check connector status endpoints first

## What to Expect

When everything is configured correctly:

1. **On startup**: Connectors initialize and show "ACTIVE" status
2. **Notion**: Automatically syncs every 5 minutes
3. **Slack**: Processes messages in real-time + syncs every 15 minutes  
4. **GitHub**: Processes webhooks when events occur
5. **Data**: All content is embedded and stored in Qdrant with metadata

## Next Steps

If basic testing works:

1. Configure actual data sources (real Slack workspace, Notion workspace, GitHub repos)
2. Set up GitHub webhooks pointing to your server
3. Ensure Slack bot has proper permissions
4. Monitor logs for any errors
5. Use search endpoints to query stored data
