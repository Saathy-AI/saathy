# Saathy Conversational AI - API Documentation

## Overview

The Saathy Conversational AI provides two API versions:
- **v1**: Basic chat functionality with simple retrieval
- **v2**: Advanced agentic system with multi-agent processing and learning

## Authentication

All endpoints require authentication via Bearer token:
```
Authorization: Bearer <your-token>
```

## v2 API Endpoints (Recommended)

### Create Session

```http
POST /api/v2/chat/sessions
Content-Type: application/json

{
  "metadata": {
    "client": "web",
    "version": "2.0"
  }
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "status": "active",
  "created_at": "2024-01-10T10:00:00Z"
}
```

### Send Message

```http
POST /api/v2/chat/sessions/{session_id}/messages
Content-Type: application/json

{
  "content": "What happened with the auth bug yesterday?"
}
```

**Response:**
```json
{
  "response": "Based on the GitHub activity and Slack discussions, the auth bug was identified yesterday...",
  "context_used": [
    {
      "platform": "github",
      "timestamp": "2024-01-09T15:30:00Z",
      "relevance": "high",
      "preview": "Fix authentication token validation..."
    }
  ],
  "metadata": {
    "processing_time": 1.23,
    "confidence_level": "high",
    "cache_hit": false
  }
}
```

### Submit Feedback

```http
POST /api/v2/chat/sessions/{session_id}/feedback
Content-Type: application/json

{
  "relevance_score": 0.9,
  "completeness_score": 0.8,
  "helpful": true,
  "feedback_text": "Very helpful response!"
}
```

**Response:**
```json
{
  "status": "feedback_received"
}
```

### Get Session Metrics

```http
GET /api/v2/chat/sessions/{session_id}/metrics
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_count": 5,
  "total_response_time": 8.5,
  "avg_response_time": 1.7,
  "avg_sufficiency_score": 0.82,
  "total_expansion_attempts": 2,
  "expansion_rate": 0.4,
  "error_rate": 0.0,
  "intents": ["query_events", "get_context", "query_actions"],
  "satisfaction_scores": [0.85, 0.9, 0.78]
}
```

### Get System Metrics

```http
GET /api/v2/chat/metrics/system
```

**Response:**
```json
{
  "quality": {
    "total_conversations": 150,
    "total_turns": 823,
    "avg_response_time": 1.45,
    "p95_response_time": 2.8,
    "avg_sufficiency_score": 0.79,
    "expansion_rate": 0.35,
    "error_rate": 0.02,
    "intent_distribution": {
      "query_events": 45,
      "get_context": 38,
      "query_actions": 17
    },
    "active_users": 42
  },
  "cache": {
    "hits": 245,
    "misses": 578,
    "hit_rate": 0.298,
    "query_cache_size": 156,
    "context_cache_size": 89
  },
  "learning": {
    "response_time": {
      "current": 1.45,
      "average": 1.62,
      "trend": "decreasing",
      "improvement": -0.17
    }
  },
  "current_parameters": {
    "sufficiency_threshold": 0.72,
    "retrieval_weights": {
      "vector": 0.42,
      "structured": 0.33,
      "action": 0.25
    },
    "rrf_k": 58
  }
}
```

### Export Analytics

```http
GET /api/v2/chat/analytics/export
```

**Response:**
```json
{
  "metrics": {
    "export_timestamp": "2024-01-10T12:00:00Z",
    "system_metrics": {...},
    "problematic_conversations": [...],
    "learning_queue": [...],
    "user_metrics_summary": {...}
  },
  "learning": {
    "current_parameters": {...},
    "optimization_history": [...],
    "performance_trends": {...}
  },
  "system_state": {
    "cache_stats": {...},
    "active_sessions": 23
  }
}
```

### WebSocket Chat

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/chat/sessions/{session_id}/ws');

// Send message
ws.send(JSON.stringify({
  content: "What's the status of the Dashboard project?"
}));

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'typing':
      // Show typing indicator
      break;
    case 'message':
      // Display response
      console.log(data.response);
      break;
    case 'error':
      // Handle error
      console.error(data.error);
      break;
  }
};
```

## Response Codes

- `200 OK`: Successful request
- `201 Created`: Session created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `404 Not Found`: Session or resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

- **Standard tier**: 60 requests per minute
- **Premium tier**: 300 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704884400
```

## Multi-Agent Processing Flow

When you send a message to v2 endpoints, it goes through:

1. **Information Analyzer Agent**: Extracts intent, entities, time references
2. **Context Retriever Agent**: Performs hybrid search with RRF
3. **Sufficiency Evaluator Agent**: Checks if context is complete
4. **Context Expander Agent**: (If needed) Plans expansion strategy
5. **Response Generator Agent**: Creates natural language response

## Metrics & Learning

The system continuously learns from:
- User feedback scores
- Response times
- Sufficiency scores
- Error patterns

Parameters that adapt over time:
- Sufficiency thresholds
- Retrieval weights
- Cache policies
- Expansion strategies

## Best Practices

1. **Use v2 endpoints** for production - they provide better quality and performance
2. **Submit feedback** to help the system learn and improve
3. **Monitor metrics** to track conversation quality
4. **Leverage caching** - similar queries benefit from cache hits
5. **Handle WebSocket disconnections** gracefully with reconnection logic

## Migration from v1 to v2

Key differences:
- v2 uses multi-agent processing (better quality)
- v2 supports user feedback
- v2 provides detailed metrics
- v2 has intelligent caching
- v2 responses include confidence levels

Migration is straightforward:
```diff
- POST /api/chat/sessions/{id}/messages
+ POST /api/v2/chat/sessions/{id}/messages

# Response format is backward compatible
```