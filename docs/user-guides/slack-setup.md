# Slack Connector Setup Guide

This guide explains how to set up the Slack connector for Saathy to process Slack messages using the Slack Web API.

## Prerequisites

1. A Slack workspace where you have admin permissions
2. Python 3.9+ with the Saathy application installed
3. Slack bot token

## Creating a Slack App

### 1. Create a New Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter an app name and select your workspace

### 2. Configure App Permissions

Navigate to "OAuth & Permissions" and add the following scopes:

**Bot Token Scopes:**
- `channels:history` - Read messages in public channels
- `channels:read` - View basic information about public channels
- `groups:history` - Read messages in private channels
- `groups:read` - View basic information about private channels
- `im:history` - Read messages in DMs
- `im:read` - View basic information about DMs
- `mpim:history` - Read messages in group DMs
- `mpim:read` - View basic information about group DMs
- `users:read` - View people in the workspace

**User Token Scopes:**
- None required for this connector

### 3. Subscribe to Events (Optional)

If you want to receive real-time events, navigate to "Event Subscriptions" and subscribe to the following bot events:

- `message.channels` - Messages in public channels
- `message.groups` - Messages in private channels
- `message.im` - Direct messages
- `message.mpim` - Group direct messages

### 4. Install the App

1. Go to "Install App" in the left sidebar
2. Click "Install to Workspace"
3. Authorize the app

## Configuration

### Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Slack Bot Token (starts with xoxb-)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Comma-separated list of channel IDs to monitor (optional)
SLACK_CHANNELS=C1234567890,C0987654321
```

### File-based Secrets (Alternative)

For enhanced security, you can store tokens in files:

```bash
# Create secret file
echo "xoxb-your-bot-token-here" > secrets/slack_bot_token

# Set environment variable to point to file
SLACK_BOT_TOKEN_FILE=secrets/slack_bot_token
```

## Usage

### Running the Demo

```bash
# Run the demo script
python demo_slack_connector.py
```

### Integration with Saathy

The Slack connector integrates with the existing Saathy infrastructure:

```python
from saathy.connectors.slack_connector import SlackConnector
from saathy.config import settings

# Create connector configuration
config = {
    "bot_token": settings.slack_bot_token_str,
    "channels": settings.slack_channels.split(",") if settings.slack_channels else []
}

# Create and start connector
connector = SlackConnector(config)
await connector.start()
```

## Features

### Message Processing

- Connects to Slack using the Web API
- Retrieves messages from configured channels
- Extracts message content and metadata
- Converts messages to `ProcessedContent` objects for further processing

### Message Filtering

- Filters out bot messages and message updates
- Only processes messages from configured channels
- Supports both public and private channels

### Rich Metadata

Each processed message includes:

- Channel information (ID and name)
- User information
- Timestamp and thread context
- File and attachment indicators
- Original raw data

### Error Handling

- Graceful handling of connection failures
- Comprehensive logging for debugging
- Automatic reconnection attempts
- Status monitoring and health checks

## Troubleshooting

### Common Issues

1. **"Missing Slack bot token" error**
   - Ensure `SLACK_BOT_TOKEN` is set
   - Verify token starts with `xoxb-`

2. **"Failed to start Slack connector" error**
   - Check token permissions and scopes
   - Verify the app is installed to the workspace

3. **No messages being processed**
   - Check that the bot is invited to the channels you want to monitor
   - Verify channel IDs in `SLACK_CHANNELS` configuration
   - Ensure the app has the required scopes

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("saathy.connector.slack").setLevel(logging.DEBUG)
```

## Security Considerations

- Never commit tokens to version control
- Use file-based secrets in production
- Regularly rotate tokens
- Limit bot permissions to only what's necessary
- Monitor connector logs for suspicious activity

## Next Steps

After setting up the Slack connector:

1. Integrate with the vector database for message storage
2. Set up embedding processing for message content
3. Configure content processing pipelines
4. Add message filtering and routing logic
5. Implement notification systems for processed content 