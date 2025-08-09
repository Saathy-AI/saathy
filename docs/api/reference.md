# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API uses basic authentication for admin endpoints. Regular endpoints don't require authentication in the open-source version.

For enterprise features, a license key is required.

## Endpoints

### Health & Status

#### GET /health
Check service health and dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "saathy-core-api",
  "version": "0.1.0",
  "checks": {
    "vector_store": {"status": "healthy"},
    "cache": {"status": "healthy"},
    "openai": {"status": "configured"}
  }
}
```

#### GET /ready
Check if service is ready to accept requests.

#### GET /live
Simple liveness check.

### Connectors

#### GitHub

##### GET /github/status
Get GitHub connector status.

##### POST /github/sync
Manually trigger repository synchronization.

**Request Body:**
```json
{
  "full_sync": false,
  "since": "2024-01-01T00:00:00Z",
  "limit": 100
}
```

#### Slack

##### GET /slack/status
Get Slack connector status.

##### POST /slack/start
Start the Slack connector.

##### POST /slack/stop
Stop the Slack connector.

##### GET /slack/channels
Get list of available Slack channels.

**Query Parameters:**
- `include_private` (boolean): Include private channels

#### Notion

##### GET /notion/status
Get Notion connector status.

##### POST /notion/start
Start Notion polling.

##### POST /notion/stop
Stop Notion polling.

##### POST /notion/sync
Manually trigger Notion synchronization.

### Webhooks

#### POST /webhooks/github
GitHub webhook endpoint.

**Headers:**
- `X-Hub-Signature-256`: GitHub signature
- `X-GitHub-Event`: Event type
- `X-GitHub-Delivery`: Delivery ID

#### POST /webhooks/slack
Slack webhook endpoint for events and slash commands.

**Headers:**
- `X-Slack-Request-Timestamp`: Request timestamp
- `X-Slack-Signature`: Request signature

#### POST /webhooks/notion
Notion webhook endpoint (for future compatibility).

### Intelligence (Pro/Enterprise)

#### GET /intelligence/actions/user/{user_id}
Get AI-generated action recommendations.

**Query Parameters:**
- `limit` (integer): Number of actions to return
- `include_completed` (boolean): Include completed actions
- `priority` (string): Filter by priority (high/medium/low)

**Response:**
```json
[
  {
    "id": "uuid",
    "user_id": "user123",
    "title": "Review open pull requests",
    "description": "You have 3 PRs waiting for review",
    "priority": "high",
    "action_type": "review",
    "platform_links": {
      "github": "https://github.com/org/repo/pulls"
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /intelligence/actions/{action_id}/complete
Mark an action as completed.

#### POST /intelligence/actions/{action_id}/feedback
Provide feedback on an action.

**Request Body:**
```json
{
  "useful": true,
  "feedback_text": "This was very helpful",
  "completed": true
}
```

#### GET /intelligence/correlations/user/{user_id}
Get event correlations across platforms.

**Query Parameters:**
- `hours` (integer): Time window in hours
- `min_score` (float): Minimum correlation score

#### GET /intelligence/events/user/{user_id}
Get user events timeline.

**Query Parameters:**
- `hours` (integer): Time window
- `platform` (string): Filter by platform
- `event_type` (string): Filter by event type
- `limit` (integer): Maximum events to return

### Streaming

#### GET /streaming/events/user/{user_id}
Server-Sent Events stream for real-time updates.

**Query Parameters:**
- `include_actions` (boolean): Include action updates
- `include_events` (boolean): Include platform events
- `include_correlations` (boolean): Include correlations

**Event Types:**
- `connected`: Initial connection
- `platform_event`: New platform event
- `action_update`: Action recommendation update
- `heartbeat`: Keep-alive signal
- `error`: Error occurred
- `close`: Stream closing

#### WebSocket /streaming/ws/user/{user_id}
WebSocket connection for bidirectional communication.

**Message Types:**

Client → Server:
```json
{
  "type": "get_actions",
  "limit": 10
}
```

Server → Client:
```json
{
  "type": "actions",
  "actions": [...]
}
```

### Admin (Requires Authentication)

#### GET /admin/system/info
Get system information and metrics.

#### GET /admin/connectors/all
Get detailed information about all connectors.

#### POST /admin/connectors/{name}/restart
Restart a specific connector.

#### GET /admin/vector-store/stats
Get vector store statistics.

#### POST /admin/cache/flush
Flush cache keys.

**Query Parameters:**
- `pattern` (string): Key pattern to flush
- `confirm` (boolean): Confirm operation

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid credentials"
}
```

### 402 Payment Required
```json
{
  "error": "Feature not available",
  "message": "This feature requires an enterprise license",
  "required_tier": "professional"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

The API implements rate limiting:
- Basic tier: 60 requests/minute
- Professional: 300 requests/minute  
- Enterprise: Unlimited

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp