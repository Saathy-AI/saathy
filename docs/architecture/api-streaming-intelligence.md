# Streaming Intelligence API Documentation

## Overview

The Streaming Intelligence API provides endpoints for accessing proactive action recommendations, event correlations, and user activity across platforms. These endpoints are designed for integration with frontend applications and notification systems.

## Authentication

All endpoints require appropriate authentication. The system uses the existing Saathy authentication mechanism.

## Endpoints

### 🧠 Intelligence & Actions

#### Get User Actions
```http
GET /actions/user/{user_id}
```

**Description**: Retrieve proactive action recommendations for a specific user.

**Parameters:**
- `user_id` (path, required): The user identifier
- `limit` (query, optional): Maximum number of actions to return (default: 20, max: 50)
- `priority` (query, optional): Filter by priority (urgent, high, medium, low, fyi)
- `status` (query, optional): Filter by status (pending, completed, dismissed)

**Response:**
```json
{
  "actions": [
    {
      "action_id": "action_user123_1701234567",
      "title": "Review PR #456 for security vulnerability in auth module",
      "description": "Review the pull request that addresses a critical security vulnerability in the authentication module, triggered by urgent discussion in #eng-alerts.",
      "priority": "urgent",
      "action_type": "review",
      "reasoning": "Security vulnerability requires immediate attention based on Slack discussion and GitHub PR activity",
      "estimated_time_minutes": 20,
      "action_links": [
        {
          "platform": "github",
          "url": "https://github.com/company/saathy-core/pull/456",
          "label": "View PR #456",
          "action_type": "view"
        }
      ],
      "related_people": ["alice", "bob"],
      "user_id": "user123",
      "correlation_id": "corr_user123_1701234560",
      "generated_at": "2023-11-29T10:30:00Z",
      "expires_at": "2023-11-29T14:30:00Z",
      "status": "pending"
    }
  ],
  "total_count": 5,
  "has_more": false
}
```

**Error Responses:**
- `404`: User not found
- `429`: Rate limit exceeded

---

#### Complete Action
```http
POST /actions/{action_id}/complete
```

**Description**: Mark an action as completed and optionally provide completion notes.

**Parameters:**
- `action_id` (path, required): The action identifier

**Request Body:**
```json
{
  "completion_notes": "Reviewed PR and approved with minor suggestions",
  "actual_time_minutes": 25
}
```

**Response:**
```json
{
  "message": "Action marked as completed",
  "action_id": "action_user123_1701234567",
  "completed_at": "2023-11-29T11:00:00Z"
}
```

**Error Responses:**
- `404`: Action not found
- `400`: Action already completed or expired

---

#### Provide Action Feedback
```http
POST /actions/{action_id}/feedback
```

**Description**: Provide feedback on the usefulness and accuracy of an action.

**Parameters:**
- `action_id` (path, required): The action identifier

**Request Body:**
```json
{
  "feedback_score": 4,
  "feedback_text": "Very helpful, the links took me directly to what I needed to review",
  "improvement_suggestions": "Could include more context about the specific vulnerability"
}
```

**Response:**
```json
{
  "message": "Feedback recorded successfully",
  "action_id": "action_user123_1701234567"
}
```

**Error Responses:**
- `404`: Action not found
- `400`: Invalid feedback score (must be 1-5)

---

#### Get User Action Statistics
```http
GET /actions/user/{user_id}/stats
```

**Description**: Get statistics about actions generated for a user.

**Parameters:**
- `user_id` (path, required): The user identifier
- `days` (query, optional): Number of days to include in statistics (default: 7, max: 30)

**Response:**
```json
{
  "user_id": "user123",
  "period_days": 7,
  "total_actions_generated": 15,
  "actions_completed": 8,
  "actions_dismissed": 2,
  "actions_pending": 5,
  "completion_rate": 0.53,
  "average_feedback_score": 4.2,
  "daily_breakdown": [
    {
      "date": "2023-11-29",
      "actions_generated": 3,
      "actions_completed": 2
    }
  ],
  "priority_breakdown": {
    "urgent": 3,
    "high": 5,
    "medium": 4,
    "low": 2,
    "fyi": 1
  },
  "avg_completion_time_minutes": 18.5
}
```

---

### 📊 Event Correlations

#### Get User Correlations
```http
GET /correlations/user/{user_id}
```

**Description**: Retrieve event correlations for a user to understand how activities are linked.

**Parameters:**
- `user_id` (path, required): The user identifier
- `hours` (query, optional): Hours of history to include (default: 24, max: 168)
- `min_strength` (query, optional): Minimum correlation strength (default: 0.3)

**Response:**
```json
{
  "correlations": [
    {
      "correlation_id": "corr_user123_1701234560",
      "user_id": "user123",
      "created_at": "2023-11-29T10:15:00Z",
      "correlation_strength": 0.85,
      "primary_event": {
        "event_id": "slack_urgent_123",
        "platform": "slack",
        "event_type": "slack_message",
        "timestamp": "2023-11-29T10:25:00Z",
        "summary": "Urgent message in #eng-alerts about PR review"
      },
      "related_events": [
        {
          "event_id": "github_pr_456",
          "platform": "github",
          "event_type": "github_pr",
          "timestamp": "2023-11-29T10:20:00Z",
          "summary": "PR #456 opened in saathy-core repository",
          "similarity_score": 0.8
        }
      ],
      "key_insights": [
        "Cross-platform activity spanning slack, github",
        "Security-focused discussion and development"
      ],
      "actions_generated": 1,
      "status": "actions_generated"
    }
  ],
  "total_count": 12,
  "has_more": true
}
```

---

#### Get Correlation Details
```http
GET /correlations/{correlation_id}
```

**Description**: Get detailed information about a specific correlation.

**Response:**
```json
{
  "correlation_id": "corr_user123_1701234560",
  "user_id": "user123",
  "created_at": "2023-11-29T10:15:00Z",
  "correlation_strength": 0.85,
  "synthesized_context": "Started with a Slack message in #eng-alerts about urgent PR review, followed by related GitHub activity...",
  "primary_event": {
    "event_id": "slack_urgent_123",
    "platform": "slack",
    "full_details": "..."
  },
  "related_events": [...],
  "key_insights": [...],
  "urgency_signals": [...],
  "platform_data": {...},
  "actions_generated": [
    {
      "action_id": "action_user123_1701234567",
      "title": "Review PR #456 for security vulnerability",
      "status": "pending"
    }
  ]
}
```

---

### 📅 User Events

#### Get User Events
```http
GET /events/user/{user_id}
```

**Description**: Retrieve recent events across all platforms for a user.

**Parameters:**
- `user_id` (path, required): The user identifier
- `hours` (query, optional): Hours of history to include (default: 24, max: 168)
- `platforms` (query, optional): Comma-separated list of platforms (slack,github,notion)
- `limit` (query, optional): Maximum number of events (default: 50, max: 200)

**Response:**
```json
{
  "events": [
    {
      "event_id": "slack_msg_789",
      "platform": "slack",
      "event_type": "slack_message",
      "timestamp": "2023-11-29T10:25:00Z",
      "urgency_score": 0.8,
      "keywords": ["urgent", "review"],
      "project_context": "saathy-core",
      "summary": "Message in #eng-alerts about urgent PR review",
      "platform_specific": {
        "channel_name": "eng-alerts",
        "message_preview": "Need urgent review of PR #456..."
      }
    },
    {
      "event_id": "github_pr_456",
      "platform": "github", 
      "event_type": "github_pr",
      "timestamp": "2023-11-29T10:20:00Z",
      "urgency_score": 0.7,
      "keywords": ["security", "auth"],
      "project_context": "saathy-core",
      "summary": "PR #456 opened in saathy-core",
      "platform_specific": {
        "repository": "company/saathy-core",
        "pr_number": 456,
        "action": "opened"
      }
    }
  ],
  "total_count": 25,
  "has_more": true,
  "platform_breakdown": {
    "slack": 12,
    "github": 8,
    "notion": 5
  }
}
```

---

#### Get Event Details
```http
GET /events/{event_id}
```

**Description**: Get full details of a specific event.

**Response:**
```json
{
  "event_id": "slack_msg_789",
  "platform": "slack",
  "event_type": "slack_message",
  "timestamp": "2023-11-29T10:25:00Z",
  "user_id": "user123",
  "urgency_score": 0.8,
  "keywords": ["urgent", "review", "security"],
  "project_context": "saathy-core",
  "mentioned_users": ["alice", "bob"],
  "raw_data": {...},
  "platform_specific": {
    "channel_id": "C123456",
    "channel_name": "eng-alerts",
    "message_text": "Need urgent review of PR #456 - security vulnerability in auth module!",
    "thread_ts": null,
    "is_thread_reply": false,
    "reactions": ["👍", "⚡"]
  },
  "correlations": [
    {
      "correlation_id": "corr_user123_1701234560",
      "similarity_score": 0.85
    }
  ]
}
```

---

### 🔧 System Management

#### Trigger Manual Correlation
```http
POST /system/correlations/trigger
```

**Description**: Manually trigger correlation processing for testing or recovery.

**Request Body:**
```json
{
  "user_id": "user123",
  "hours_back": 2,
  "force_reprocess": false
}
```

**Response:**
```json
{
  "message": "Correlation processing triggered",
  "events_queued": 15,
  "estimated_processing_time_seconds": 30
}
```

---

#### Get System Health
```http
GET /system/streaming/health
```

**Description**: Check the health of the streaming intelligence system.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "redis": {
      "status": "connected",
      "latency_ms": 2.3
    },
    "event_manager": {
      "status": "running",
      "events_processed_last_hour": 145
    },
    "correlation_processor": {
      "status": "running",
      "queue_length": 3,
      "correlations_created_last_hour": 28
    },
    "action_generator": {
      "status": "running",
      "queue_length": 1,
      "actions_generated_last_hour": 12,
      "openai_api_status": "connected"
    }
  },
  "metrics": {
    "total_events_stored": 15420,
    "total_correlations_created": 3242,
    "total_actions_generated": 1876,
    "average_correlation_strength": 0.68,
    "average_action_completion_rate": 0.72
  }
}
```

---

#### Get Processing Statistics
```http
GET /system/streaming/stats
```

**Description**: Get detailed processing statistics for monitoring and debugging.

**Parameters:**
- `hours` (query, optional): Hours of statistics to include (default: 24)

**Response:**
```json
{
  "period_hours": 24,
  "event_processing": {
    "total_events": 1456,
    "events_by_platform": {
      "slack": 687,
      "github": 523,
      "notion": 246
    },
    "events_per_hour": 60.7,
    "processing_latency_ms": {
      "p50": 12.5,
      "p95": 45.2,
      "p99": 89.1
    }
  },
  "correlation_processing": {
    "total_correlations": 142,
    "correlation_success_rate": 0.89,
    "average_correlation_strength": 0.68,
    "correlation_latency_ms": {
      "p50": 125.3,
      "p95": 456.7
    }
  },
  "action_generation": {
    "total_actions": 89,
    "action_success_rate": 0.94,
    "actions_by_priority": {
      "urgent": 12,
      "high": 23,
      "medium": 31,
      "low": 18,
      "fyi": 5
    },
    "openai_api_calls": 156,
    "openai_api_cost_usd": 2.34,
    "generation_latency_ms": {
      "p50": 2340.1,
      "p95": 4567.8
    }
  }
}
```

## Rate Limiting

All endpoints are subject to rate limiting:
- **User Action Endpoints**: 100 requests per minute per user
- **System Management**: 10 requests per minute per API key
- **Statistics/Health**: 20 requests per minute per API key

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1701234567
```

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": {
      "field": "user_id",
      "issue": "User ID must be a valid identifier"
    },
    "correlation_id": "corr_12345678",
    "timestamp": "2023-11-29T10:30:00Z"
  }
}
```

**Common Error Codes:**
- `INVALID_REQUEST`: Request parameters are invalid
- `NOT_FOUND`: Resource not found
- `RATE_LIMITED`: Rate limit exceeded
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Access denied
- `INTERNAL_ERROR`: Server error
- `SERVICE_UNAVAILABLE`: Dependent service unavailable

## Webhooks

The system can send webhooks for real-time notifications:

### Action Generated Webhook
```http
POST {webhook_url}
```

**Payload:**
```json
{
  "event_type": "action_generated",
  "timestamp": "2023-11-29T10:30:00Z",
  "user_id": "user123",
  "action": {
    "action_id": "action_user123_1701234567",
    "title": "Review PR #456 for security vulnerability",
    "priority": "urgent",
    "correlation_id": "corr_user123_1701234560"
  }
}
```

### Correlation Created Webhook
```http
POST {webhook_url}
```

**Payload:**
```json
{
  "event_type": "correlation_created",
  "timestamp": "2023-11-29T10:15:00Z",
  "user_id": "user123",
  "correlation": {
    "correlation_id": "corr_user123_1701234560",
    "correlation_strength": 0.85,
    "platforms": ["slack", "github"],
    "insights_count": 3
  }
}
```

## SDK Integration

Example usage with JavaScript/TypeScript:

```typescript
import { SaathyClient } from '@saathy/client';

const client = new SaathyClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.saathy.com'
});

// Get user actions
const actions = await client.actions.getUserActions('user123', {
  limit: 10,
  priority: 'urgent'
});

// Complete an action
await client.actions.complete('action_123', {
  completion_notes: 'Task completed successfully',
  actual_time_minutes: 15
});

// Provide feedback
await client.actions.feedback('action_123', {
  feedback_score: 5,
  feedback_text: 'Very helpful and accurate'
});

// Get correlations
const correlations = await client.correlations.getUserCorrelations('user123', {
  hours: 24,
  min_strength: 0.5
});
```

## Testing

Use the provided test endpoints in development:

```bash
# Generate test events
curl -X POST "/system/test/generate-events" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "event_count": 5}'

# Force correlation processing
curl -X POST "/system/test/force-correlation" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'

# Generate test actions
curl -X POST "/system/test/generate-actions" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "correlation_id": "test_corr"}'
```