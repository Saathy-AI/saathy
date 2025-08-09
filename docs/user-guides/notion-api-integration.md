# Notion Connector API Integration

This document describes the comprehensive Notion connector integration in Saathy, including all available API endpoints for managing and monitoring Notion content synchronization.

## Overview

The Notion connector provides a complete integration with Notion workspaces, allowing you to:
- Automatically sync and monitor Notion databases and pages
- Manually trigger syncs for specific resources
- Search and browse Notion content
- Monitor connector health and performance
- Control connector lifecycle (start/stop)

## Configuration

### Environment Variables

The Notion connector is configured through the following environment variables:

```bash
# Required: Notion integration token
NOTION_TOKEN=your_notion_integration_token

# Optional: Comma-separated list of database IDs to monitor
NOTION_DATABASES=db1,db2,db3

# Optional: Comma-separated list of page IDs to monitor  
NOTION_PAGES=page1,page2,page3

# Optional: Polling interval in seconds (default: 300)
NOTION_POLL_INTERVAL=300
```

### Auto-Discovery

If no databases or pages are explicitly configured, the connector will automatically discover and sync up to 5 databases from your workspace.

## API Endpoints

### 1. Get Connector Status

**Endpoint:** `GET /connectors/notion/status`

**Description:** Get comprehensive status information about the Notion connector.

**Response:**
```json
{
  "status": "active",
  "name": "notion",
  "uptime": "2h 30m",
  "last_sync": "2025-01-01T12:00:00Z",
  "total_pages_processed": 150,
  "databases_monitored": ["db1", "db2"],
  "pages_monitored": ["page1", "page2"],
  "sync_statistics": {
    "total_syncs": 25,
    "successful_syncs": 24,
    "failed_syncs": 1,
    "last_error": null,
    "average_sync_time": 12.5,
    "items_per_sync": 8.2
  },
  "configuration": {
    "poll_interval": 300,
    "auto_discover": true,
    "databases_count": 2,
    "pages_count": 3
  }
}
```

### 2. Start Connector

**Endpoint:** `POST /connectors/notion/start`

**Description:** Start the Notion connector if it's not already running.

**Response:**
```json
{
  "message": "Notion connector started successfully."
}
```

### 3. Stop Connector

**Endpoint:** `POST /connectors/notion/stop`

**Description:** Stop the Notion connector if it's running.

**Response:**
```json
{
  "message": "Notion connector stopped successfully."
}
```

### 4. Trigger Manual Sync

**Endpoint:** `POST /connectors/notion/sync`

**Description:** Manually trigger a sync operation.

**Query Parameters:**
- `full_sync` (boolean, optional): Whether to perform a full sync (default: false)
- `database_id` (string, optional): Specific database ID to sync
- `page_id` (string, optional): Specific page ID to sync

**Examples:**

Sync a specific database:
```bash
POST /connectors/notion/sync?database_id=db1&full_sync=true
```

Sync a specific page:
```bash
POST /connectors/notion/sync?page_id=page1&full_sync=false
```

Sync all configured resources:
```bash
POST /connectors/notion/sync?full_sync=true
```

**Response:**
```json
{
  "message": "Database db1 synced successfully.",
  "sync_type": "full",
  "resource_type": "database",
  "resource_id": "db1"
}
```

### 5. List Databases

**Endpoint:** `GET /connectors/notion/databases`

**Description:** List all available databases in the Notion workspace.

**Response:**
```json
{
  "databases": [
    {
      "id": "db1",
      "title": "Project Database",
      "url": "https://notion.so/db1",
      "created_time": "2023-01-01T00:00:00Z",
      "last_edited_time": "2023-01-02T00:00:00Z",
      "is_monitored": true
    }
  ],
  "total_count": 1,
  "monitored_count": 1
}
```

### 6. Search Content

**Endpoint:** `GET /connectors/notion/search`

**Description:** Search for content in the Notion workspace.

**Query Parameters:**
- `query` (string, required): Search query
- `limit` (integer, optional): Maximum number of results (default: 10, max: 100)

**Example:**
```bash
GET /connectors/notion/search?query=project&limit=20
```

**Response:**
```json
{
  "results": [
    {
      "id": "page1",
      "type": "page",
      "title": "Project Overview",
      "url": "https://notion.so/page1",
      "last_edited_time": "2023-01-02T00:00:00Z"
    },
    {
      "id": "db1",
      "type": "database",
      "title": "Project Database",
      "url": "https://notion.so/db1",
      "last_edited_time": "2023-01-02T00:00:00Z"
    }
  ],
  "query": "project",
  "total_count": 2
}
```

### 7. Process Content

**Endpoint:** `POST /connectors/notion/process`

**Description:** Manually process Notion page data for content extraction.

**Request Body:**
```json
{
  "id": "page_id",
  "properties": {
    "title": {
      "title": [{"plain_text": "Page Title"}]
    }
  },
  "url": "https://notion.so/page_id",
  "created_time": "2023-01-01T00:00:00Z",
  "last_edited_time": "2023-01-02T00:00:00Z"
}
```

**Response:**
```json
{
  "processed_items": 1,
  "embeddings_created": 1,
  "vectors_stored": 1
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Operation completed successfully
- `400 Bad Request`: Invalid request parameters
- `503 Service Unavailable`: Notion connector not configured or available
- `500 Internal Server Error`: Unexpected error occurred

Error responses include a `detail` field with a human-readable error message:

```json
{
  "detail": "Notion connector is not configured or available."
}
```

## Monitoring and Observability

### Health Checks

The connector status endpoint provides comprehensive health information:
- Current status (active/inactive/error)
- Uptime since last start
- Last sync timestamp
- Processing statistics
- Configuration summary

### Sync Statistics

The connector tracks:
- Total number of syncs performed
- Success/failure rates
- Average sync duration
- Items processed per sync
- Last error encountered

### Logging

The connector logs important events:
- Startup and shutdown
- Sync operations
- Error conditions
- Performance metrics

## Integration Patterns

### Dependency Injection

The connector is available through FastAPI's dependency injection system:

```python
from fastapi import Depends
from saathy.api import get_notion_connector

@app.get("/my-endpoint")
async def my_endpoint(
    notion_connector: NotionConnector = Depends(get_notion_connector)
):
    # Use the connector
    status = notion_connector.get_status()
    return status
```

### Lifecycle Management

The connector is automatically initialized during application startup if configured:

1. **Startup**: Connector is created and started if `NOTION_TOKEN` is provided
2. **Runtime**: Connector runs background polling and responds to API requests
3. **Shutdown**: Connector is gracefully stopped during application shutdown

### Error Recovery

The connector implements automatic error recovery:
- Failed API calls are retried with exponential backoff
- Connection errors trigger reconnection attempts
- Rate limiting is handled gracefully
- Invalid responses are logged and skipped

## Security Considerations

### Token Management

- Notion tokens are stored as `SecretStr` in configuration
- Tokens can be provided via environment variables or secret files
- Tokens are never logged or exposed in error messages

### Access Control

- The connector only accesses resources it has been explicitly granted access to
- Database and page IDs must be explicitly configured or discovered
- No automatic access to private content

### Rate Limiting

- The connector respects Notion API rate limits
- Requests are throttled to avoid hitting limits
- Failed requests due to rate limiting are retried with backoff

## Troubleshooting

### Common Issues

1. **Connector not starting**
   - Check that `NOTION_TOKEN` is properly configured
   - Verify the token has the necessary permissions
   - Check application logs for detailed error messages

2. **Sync failures**
   - Verify database/page IDs are correct
   - Check that the integration has access to the resources
   - Review sync statistics for error patterns

3. **Performance issues**
   - Adjust `NOTION_POLL_INTERVAL` for less frequent polling
   - Limit the number of monitored databases/pages
   - Monitor sync statistics for bottlenecks

### Debugging

Enable debug logging to get detailed information:

```bash
LOG_LEVEL=DEBUG
```

### Support

For issues not covered in this documentation:
1. Check the application logs for detailed error messages
2. Review the Notion API documentation for integration-specific issues
3. Verify your Notion integration settings and permissions 