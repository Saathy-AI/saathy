# API Reference

## Overview

The Saathy API provides a comprehensive set of endpoints for managing AI-powered content processing, vector storage, and connector integrations. All endpoints return JSON responses and use standard HTTP status codes.

**Base URL**: `http://localhost:8000` (development) or your production domain

## Authentication

Currently, the API does not require authentication for most endpoints. Production deployments should implement proper authentication mechanisms.

## Common Response Format

All API responses follow this structure:

```json
{
  "status": "success|error",
  "message": "Human-readable message",
  "data": {}, // Response data (varies by endpoint)
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

## Health & Monitoring Endpoints

### Health Check

**GET** `/healthz`

Performs a comprehensive health check including Qdrant connectivity verification.

**Response:**
```json
{
  "status": "success",
  "message": "Service is healthy",
  "data": {
    "service": "Saathy",
    "version": "0.1.0",
    "environment": "development",
    "qdrant_connected": true,
    "qdrant_collections": ["documents", "embeddings"],
    "uptime_seconds": 3600,
    "memory_usage_mb": 128.5,
    "cpu_usage_percent": 2.3
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is unhealthy

### Readiness Check

**GET** `/readyz`

Checks if the service is ready to accept requests.

**Response:**
```json
{
  "status": "success",
  "message": "Service is ready",
  "data": {
    "ready": true,
    "dependencies": {
      "qdrant": "connected",
      "scheduler": "running",
      "connectors": "active"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Configuration Display

**GET** `/config`

Returns non-sensitive configuration information.

**Response:**
```json
{
  "status": "success",
  "message": "Configuration retrieved",
  "data": {
    "app_name": "Saathy",
    "environment": "development",
    "debug": false,
    "log_level": "INFO",
    "qdrant_url": "http://localhost:6333",
    "default_embedding_model": "all-MiniLM-L6-v2",
    "embedding_cache_size": 1000,
    "embedding_batch_size": 32,
    "enable_gpu_embeddings": true,
    "enable_tracing": false
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

## GitHub Connector Endpoints

### GitHub Webhook

**POST** `/webhooks/github`

Processes GitHub webhook events for repository monitoring.

**Headers:**
```
Content-Type: application/json
X-GitHub-Event: push|pull_request|issues|...
X-Hub-Signature-256: sha256=...
```

**Request Body:**
```json
{
  "ref": "refs/heads/main",
  "repository": {
    "name": "my-repo",
    "full_name": "username/my-repo",
    "clone_url": "https://github.com/username/my-repo.git"
  },
  "commits": [
    {
      "id": "abc123",
      "message": "Update documentation",
      "added": ["docs/new-file.md"],
      "modified": ["README.md"],
      "removed": []
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Webhook processed successfully",
  "data": {
    "event_type": "push",
    "repository": "username/my-repo",
    "commits_processed": 1,
    "files_processed": 2,
    "chunks_created": 15
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### GitHub Connector Status

**GET** `/connectors/github/status`

Returns the current status and metrics for the GitHub connector.

**Response:**
```json
{
  "status": "success",
  "message": "GitHub connector status retrieved",
  "data": {
    "active": true,
    "last_sync": "2024-01-01T00:00:00Z",
    "repositories": [
      {
        "name": "username/my-repo",
        "url": "https://github.com/username/my-repo",
        "last_updated": "2024-01-01T00:00:00Z",
        "files_processed": 150,
        "commits_processed": 25
      }
    ],
    "metrics": {
      "total_events_processed": 1000,
      "total_files_processed": 5000,
      "total_chunks_created": 25000,
      "error_count": 5,
      "last_error": "2024-01-01T00:00:00Z"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Manual GitHub Sync

**POST** `/connectors/github/sync`

Manually triggers synchronization of GitHub repositories.

**Request Body:**
```json
{
  "repository": "username/my-repo", // Optional: specific repo
  "force": false,                   // Force full sync
  "since": "2024-01-01T00:00:00Z"  // Optional: sync since date
}
```

**Response:**
```json
{
  "status": "success",
  "message": "GitHub sync initiated",
  "data": {
    "sync_id": "uuid-string",
    "repository": "username/my-repo",
    "status": "running",
    "estimated_duration": "5 minutes"
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

## Slack Connector Endpoints

### Slack Connector Status

**GET** `/connectors/slack/status`

Returns the current status and metrics for the Slack connector.

**Response:**
```json
{
  "status": "success",
  "message": "Slack connector status retrieved",
  "data": {
    "active": true,
    "connected": true,
    "channels": [
      {
        "id": "C1234567890",
        "name": "general",
        "messages_processed": 1000,
        "last_message": "2024-01-01T00:00:00Z"
      }
    ],
    "metrics": {
      "total_messages_processed": 5000,
      "total_chunks_created": 15000,
      "error_count": 2,
      "last_error": "2024-01-01T00:00:00Z"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Start Slack Connector

**POST** `/connectors/slack/start`

Starts the Slack connector and begins processing messages.

**Request Body:**
```json
{
  "channels": ["C1234567890", "C0987654321"], // Optional: specific channels
  "auto_reconnect": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Slack connector started",
  "data": {
    "active": true,
    "channels_connected": 2,
    "start_time": "2024-01-01T00:00:00Z"
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Stop Slack Connector

**POST** `/connectors/slack/stop`

Stops the Slack connector.

**Response:**
```json
{
  "status": "success",
  "message": "Slack connector stopped",
  "data": {
    "active": false,
    "stop_time": "2024-01-01T00:00:00Z",
    "total_messages_processed": 5000
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### List Slack Channels

**GET** `/connectors/slack/channels`

Returns available Slack channels.

**Response:**
```json
{
  "status": "success",
  "message": "Slack channels retrieved",
  "data": {
    "channels": [
      {
        "id": "C1234567890",
        "name": "general",
        "is_private": false,
        "member_count": 100,
        "topic": "General discussion"
      },
      {
        "id": "C0987654321",
        "name": "random",
        "is_private": false,
        "member_count": 50,
        "topic": "Random stuff"
      }
    ]
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Process Slack Content

**POST** `/connectors/slack/process`

Manually processes Slack content for a specific channel or time range.

**Request Body:**
```json
{
  "channel_id": "C1234567890",     // Optional: specific channel
  "since": "2024-01-01T00:00:00Z", // Optional: process since date
  "limit": 100                     // Optional: max messages to process
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Slack content processing completed",
  "data": {
    "channel_id": "C1234567890",
    "messages_processed": 100,
    "chunks_created": 300,
    "processing_time_seconds": 5.2
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

## Embedding Service Endpoints

### Get Available Models

**GET** `/embed/models`

Returns available embedding models and their capabilities.

**Response:**
```json
{
  "status": "success",
  "message": "Embedding models retrieved",
  "data": {
    "models": [
      {
        "name": "all-MiniLM-L6-v2",
        "type": "local",
        "dimensions": 384,
        "max_length": 256,
        "supported_languages": ["en"],
        "performance": "fast"
      },
      {
        "name": "text-embedding-ada-002",
        "type": "openai",
        "dimensions": 1536,
        "max_length": 8191,
        "supported_languages": ["en"],
        "performance": "high"
      }
    ],
    "default_model": "all-MiniLM-L6-v2"
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Get Embedding Service Metrics

**GET** `/embed/metrics`

Returns performance metrics for the embedding service.

**Response:**
```json
{
  "status": "success",
  "message": "Embedding metrics retrieved",
  "data": {
    "total_embeddings_generated": 10000,
    "cache_hit_rate": 0.85,
    "average_processing_time_ms": 45.2,
    "error_rate": 0.01,
    "models_used": {
      "all-MiniLM-L6-v2": 8000,
      "text-embedding-ada-002": 2000
    },
    "content_types_processed": {
      "text": 6000,
      "code": 3000,
      "document": 1000
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

## Error Responses

All endpoints may return error responses with the following structure:

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": "Additional error details",
    "field": "field_name" // Optional: specific field causing error
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-string"
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Invalid request data
- `NOT_FOUND`: Resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `INTERNAL_ERROR`: Server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `RATE_LIMITED`: Too many requests

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Health endpoints**: 100 requests/minute
- **Connector endpoints**: 60 requests/minute
- **Embedding endpoints**: 30 requests/minute
- **Webhook endpoints**: 1000 requests/minute

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Items per page (default: 20, max: 100)

**Response Headers:**
```
X-Total-Count: 150
X-Page-Count: 8
X-Current-Page: 1
X-Page-Size: 20
```

## WebSocket Endpoints

### Real-time Updates

**WebSocket** `/ws/updates`

Provides real-time updates for connector events and processing status.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/updates');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Message Types:**
- `connector_status`: Connector status changes
- `processing_update`: Content processing progress
- `error`: Error notifications
- `health_check`: Periodic health updates

## SDK Examples

### Python Client

```python
import requests

class SaathyClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        response = self.session.get(f"{self.base_url}/healthz")
        return response.json()
    
    def get_github_status(self):
        response = self.session.get(f"{self.base_url}/connectors/github/status")
        return response.json()
    
    def start_slack_connector(self, channels=None):
        data = {"channels": channels} if channels else {}
        response = self.session.post(f"{self.base_url}/connectors/slack/start", json=data)
        return response.json()

# Usage
client = SaathyClient()
health = client.health_check()
print(f"Service health: {health['data']['qdrant_connected']}")
```

### JavaScript Client

```javascript
class SaathyClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/healthz`);
    return response.json();
  }

  async getGitHubStatus() {
    const response = await fetch(`${this.baseUrl}/connectors/github/status`);
    return response.json();
  }

  async startSlackConnector(channels = null) {
    const data = channels ? { channels } : {};
    const response = await fetch(`${this.baseUrl}/connectors/slack/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }
}

// Usage
const client = new SaathyClient();
client.healthCheck().then(health => {
  console.log('Service health:', health.data.qdrant_connected);
});
```

## Testing

### Using curl

```bash
# Health check
curl -X GET "http://localhost:8000/healthz"

# GitHub connector status
curl -X GET "http://localhost:8000/connectors/github/status"

# Start Slack connector
curl -X POST "http://localhost:8000/connectors/slack/start" \
  -H "Content-Type: application/json" \
  -d '{"channels": ["C1234567890"]}'

# Get embedding models
curl -X GET "http://localhost:8000/embed/models"
```

### Using Postman

Import the following collection structure:

```json
{
  "info": {
    "name": "Saathy API",
    "description": "Saathy API endpoints"
  },
  "item": [
    {
      "name": "Health",
      "item": [
        {
          "name": "Health Check",
          "request": {
            "method": "GET",
            "url": "{{base_url}}/healthz"
          }
        }
      ]
    },
    {
      "name": "GitHub Connector",
      "item": [
        {
          "name": "Get Status",
          "request": {
            "method": "GET",
            "url": "{{base_url}}/connectors/github/status"
          }
        }
      ]
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    }
  ]
}
```