# Notion Connector Setup Guide

This guide explains how to set up and configure the Notion connector for Saathy to extract and monitor your Notion knowledge base.

## Overview

The Notion connector provides comprehensive content extraction from your Notion workspace, including:

- **Pages**: Individual pages with all their content blocks
- **Databases**: Database pages with properties and content
- **Blocks**: Individual content blocks (paragraphs, headings, code, etc.)
- **Properties**: Page properties like titles, dates, select fields, etc.

## Prerequisites

1. A Notion workspace with content you want to monitor
2. Notion integration token (Internal Integration)
3. Access to the pages/databases you want to sync

## Setup Steps

### 1. Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Fill in the details:
   - **Name**: `Saathy Knowledge Base`
   - **Associated workspace**: Select your workspace
   - **Capabilities**: 
     - Read content
     - Read user information without email
4. Click "Submit"
5. Copy the **Internal Integration Token** (starts with `secret_`)

### 2. Share Pages/Databases with Integration

For each page or database you want to monitor:

1. Open the page/database in Notion
2. Click "Share" in the top right
3. Click "Invite" and search for your integration name
4. Select the integration and click "Invite"
5. Note the page/database ID from the URL:
   - Page URL: `https://notion.so/workspace/page-id`
   - Database URL: `https://notion.so/workspace/database-id`

### 3. Configure Environment Variables

Add these to your `.env` file:

```bash
# Notion Integration Token
NOTION_TOKEN=secret_your_integration_token_here

# Optional: Specific databases to monitor (comma-separated)
NOTION_DATABASES=db1_id,db2_id,db3_id

# Optional: Specific pages to monitor (comma-separated)
NOTION_PAGES=page1_id,page2_id,page3_id

# Optional: Polling interval in seconds (default: 300)
NOTION_POLL_INTERVAL=300
```

### 4. Alternative: File-based Token Storage

For enhanced security, you can store the token in a file:

```bash
# Create a file with your token
echo "secret_your_integration_token_here" > secrets/notion_token

# Set the environment variable to point to the file
NOTION_TOKEN_FILE=secrets/notion_token
```

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NOTION_TOKEN` | Integration token | None | Yes |
| `NOTION_DATABASES` | Comma-separated database IDs | Empty | No |
| `NOTION_PAGES` | Comma-separated page IDs | Empty | No |
| `NOTION_POLL_INTERVAL` | Polling interval in seconds | 300 | No |

### Auto-Discovery

If no databases or pages are specified, the connector will:

1. Search for all databases in your workspace
2. Automatically sync the first 5 databases found
3. Log discovered databases for manual configuration

## Content Extraction Features

### Page Content

The connector extracts:

- **Page title** and metadata
- **All content blocks** (paragraphs, headings, lists, etc.)
- **Page properties** (dates, select fields, people, etc.)
- **Individual blocks** as separate searchable items

### Supported Block Types

- **Text blocks**: Paragraphs, headings, quotes, callouts
- **List blocks**: Bulleted lists, numbered lists, to-do items
- **Code blocks**: With language detection
- **Media blocks**: Images, videos, files, embeds
- **Table blocks**: Table data as structured text
- **Layout blocks**: Columns, dividers, breadcrumbs

### Content Types

- **TEXT**: General content (lists, properties, etc.)
- **MARKDOWN**: Formatted text (paragraphs, headings, quotes)
- **CODE**: Code blocks with syntax highlighting

## API Endpoints

Once configured, the connector provides these endpoints:

### Get Connector Status

```bash
GET /connectors/notion/status
```

Returns:
```json
{
  "connector": "notion",
  "status": {
    "name": "notion",
    "status": "active",
    "config": {...}
  },
  "last_sync": {...},
  "processed_items_count": 42
}
```

### Manual Sync

```bash
POST /connectors/notion/sync
```

Parameters:
- `database_id` (optional): Sync specific database
- `page_id` (optional): Sync specific page
- No parameters: Full sync

### Process Content

```bash
POST /connectors/notion/process
```

Body:
```json
{
  "page_data": {
    "id": "page_id",
    "properties": {...},
    "content": {...}
  }
}
```

## Monitoring and Logging

### Log Levels

- **INFO**: General operations, sync status
- **DEBUG**: Detailed API calls, content processing
- **WARNING**: Auto-discovery issues, rate limits
- **ERROR**: Connection failures, processing errors

### Key Metrics

- **Last sync time**: Per database/page
- **Processed items**: Count of extracted content
- **Sync frequency**: Based on poll interval
- **Error rates**: Failed operations

## Troubleshooting

### Common Issues

1. **"Notion API connection failed"**
   - Check your integration token
   - Verify the integration has access to pages/databases
   - Ensure the integration is active

2. **"No content extracted"**
   - Verify pages/databases are shared with integration
   - Check page/database IDs are correct
   - Ensure pages have content (not empty)

3. **"Rate limit exceeded"**
   - Increase polling interval
   - Reduce number of monitored items
   - Check Notion API limits

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG
```

### Testing

Use the demo script to test your configuration:

```bash
python demo_notion_connector.py
```

## Security Considerations

1. **Token Security**: Store tokens securely, use file-based storage in production
2. **Access Control**: Only share necessary pages/databases with integration
3. **Rate Limiting**: Respect Notion API limits
4. **Data Privacy**: Review extracted content for sensitive information

## Integration with Saathy

The Notion connector integrates with Saathy's content processing pipeline:

1. **Content Extraction**: Raw Notion data → ProcessedContent objects
2. **Embedding**: Text content → Vector embeddings
3. **Storage**: Vectors stored in Qdrant for search
4. **Search**: Query across all extracted Notion content

## Advanced Configuration

### Custom Polling Intervals

```bash
# Poll every 5 minutes
NOTION_POLL_INTERVAL=300

# Poll every hour
NOTION_POLL_INTERVAL=3600
```

### Selective Monitoring

```bash
# Monitor specific databases only
NOTION_DATABASES=db1,db2,db3

# Monitor specific pages only
NOTION_PAGES=page1,page2,page3

# Monitor both
NOTION_DATABASES=db1,db2
NOTION_PAGES=page1,page2
```

### Content Filtering

The connector automatically:
- Skips archived pages
- Handles pagination for large databases
- Deduplicates processed content
- Tracks last sync times for incremental updates 