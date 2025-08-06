# Quick Setup Guide: Streaming Intelligence System

## Prerequisites

Before setting up the Streaming Intelligence system, ensure you have:

- **Redis server** running (local or cloud)
- **OpenAI API key** with access to GPT-4o
- **Platform tokens** for Slack, GitHub, and Notion
- **Python 3.9+** with Poetry installed

## Step 1: Dependencies

The streaming intelligence system requires additional dependencies. These are already included in `pyproject.toml`:

```toml
[tool.poetry.dependencies]
redis = "^5.0.0"
openai = "^1.0.0"
slack-sdk = "^3.27.0"
notion-client = "^2.2.0"
```

Install them:
```bash
poetry install
```

## Step 2: Configuration

Update your `.env` file with the following configuration:

```bash
# Redis Configuration
REDIS_URL="redis://localhost:6379"
REDIS_PASSWORD=""  # Optional, leave empty for local Redis

# OpenAI Configuration
OPENAI_API_KEY="sk-your-openai-api-key"

# Slack Configuration (Socket Mode)
SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
SLACK_APP_TOKEN="xapp-your-slack-app-token"

# GitHub Configuration
GITHUB_TOKEN="ghp_your-github-token"
GITHUB_WEBHOOK_SECRET="your-webhook-secret"

# Notion Configuration
NOTION_TOKEN="secret_your-notion-integration-token"

# Event Processing Settings
EVENT_CORRELATION_WINDOW_MINUTES=30
EVENT_RETENTION_DAYS=30
ACTION_GENERATION_ENABLED=true
MAX_ACTIONS_PER_USER_PER_DAY=20
```

## Step 3: Platform Setup

### Slack Setup

1. **Create a Slack App**:
   - Go to https://api.slack.com/apps
   - Create a new app "from scratch"
   - Choose your workspace

2. **Enable Socket Mode**:
   - Go to "Socket Mode" in your app settings
   - Enable Socket Mode
   - Generate an App-Level Token with `connections:write` scope
   - Save this as `SLACK_APP_TOKEN`

3. **Configure Bot Token**:
   - Go to "OAuth & Permissions"
   - Add these Bot Token Scopes:
     - `channels:read`
     - `chat:write`
     - `users:read`
     - `reactions:read`
   - Install the app to your workspace
   - Save the Bot User OAuth Token as `SLACK_BOT_TOKEN`

4. **Subscribe to Events**:
   - Go to "Event Subscriptions"
   - Enable events
   - Subscribe to these bot events:
     - `message.channels`
     - `reaction_added`
     - `reaction_removed`

### GitHub Setup

1. **Create a Personal Access Token**:
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Generate a token with these scopes:
     - `repo` (if accessing private repos)
     - `read:org`
     - `read:user`
   - Save as `GITHUB_TOKEN`

2. **Configure Webhooks** (for each repository):
   - Go to Repository Settings > Webhooks
   - Add webhook with:
     - Payload URL: `https://your-domain.com/webhooks/github`
     - Content type: `application/json`
     - Secret: Generate a secret and save as `GITHUB_WEBHOOK_SECRET`
     - Events: Select individual events
       - `Push`
       - `Pull requests`
       - `Issues`
       - `Issue comments`
       - `Pull request reviews`

### Notion Setup

1. **Create a Notion Integration**:
   - Go to https://www.notion.so/my-integrations
   - Create a new integration
   - Save the Internal Integration Token as `NOTION_TOKEN`

2. **Grant Access to Pages/Databases**:
   - For each page/database you want to monitor:
   - Click "..." menu > "Add connections"
   - Select your integration

## Step 4: Start Redis

If running Redis locally:

```bash
# Install Redis (macOS)
brew install redis
brew services start redis

# Install Redis (Ubuntu)
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

For production, consider using Redis Cloud or AWS ElastiCache.

## Step 5: Initialize the System

Create an initialization script or add to your startup:

```python
# startup.py
import asyncio
from src.saathy.config import get_settings
from src.saathy.streaming import EventManager, SlackStreamProcessor, ActionGenerator
from src.saathy.streaming.github_webhook import GitHubWebhookProcessor
from src.saathy.streaming.notion_poller import NotionPollingService

async def start_streaming_system():
    settings = get_settings()
    
    # Initialize core components
    event_manager = EventManager(
        redis_url=settings.redis_url,
        redis_password=settings.redis_password_str
    )
    
    # Initialize platform processors
    slack_processor = SlackStreamProcessor(
        bot_token=settings.slack_bot_token_str,
        app_token=settings.slack_app_token_str,
        event_manager=event_manager
    )
    
    github_processor = GitHubWebhookProcessor(
        webhook_secret=settings.github_webhook_secret_str,
        event_manager=event_manager
    )
    
    notion_poller = NotionPollingService(
        notion_token=settings.notion_token_str,
        event_manager=event_manager
    )
    
    # Initialize AI components
    action_generator = ActionGenerator(
        openai_api_key=settings.openai_api_key_str,
        redis_url=settings.redis_url,
        redis_password=settings.redis_password_str
    )
    
    # Start all services
    await event_manager.initialize()
    await slack_processor.start()
    await notion_poller.start_polling()
    await action_generator.initialize()
    
    # Start background processors
    await asyncio.gather(
        event_manager.start_correlation_processor(),
        action_generator.start_action_generation_processor()
    )

if __name__ == "__main__":
    asyncio.run(start_streaming_system())
```

## Step 6: Test the System

### 1. Test Event Processing

Create a test script:

```python
# test_events.py
import asyncio
from datetime import datetime
from src.saathy.streaming.models.events import SlackEvent, EventType
from src.saathy.streaming.event_manager import EventManager

async def test_event_processing():
    event_manager = EventManager()
    await event_manager.initialize()
    
    # Create a test event
    test_event = SlackEvent(
        event_id="test_slack_123",
        event_type=EventType.SLACK_MESSAGE,
        timestamp=datetime.now(),
        user_id="test_user",
        platform="slack",
        raw_data={"test": True},
        channel_id="C123456",
        channel_name="test-channel",
        message_text="Test message for urgent review",
        keywords=["urgent", "review"],
        urgency_score=0.8
    )
    
    # Process the event
    await event_manager.process_event(test_event)
    print("✅ Event processed successfully!")
    
    # Check if event was stored
    recent_events = await event_manager.get_recent_events("test_user", hours=1)
    print(f"✅ Found {len(recent_events)} recent events")

if __name__ == "__main__":
    asyncio.run(test_event_processing())
```

### 2. Test Platform Connections

```bash
# Test Slack connection
python -c "
from slack_sdk import WebClient
client = WebClient(token='your-slack-bot-token')
response = client.auth_test()
print('Slack connection:', response['ok'])
"

# Test GitHub connection
python -c "
import requests
response = requests.get('https://api.github.com/user', headers={'Authorization': 'token your-github-token'})
print('GitHub connection:', response.status_code == 200)
"

# Test Notion connection
python -c "
from notion_client import Client
client = Client(auth='your-notion-token')
users = client.users.list()
print('Notion connection: OK')
"

# Test OpenAI connection
python -c "
from openai import OpenAI
client = OpenAI(api_key='your-openai-key')
response = client.models.list()
print('OpenAI connection: OK')
"
```

### 3. Test Action Generation

```python
# test_actions.py
import asyncio
from src.saathy.intelligence.action_generator import ActionGenerator

async def test_action_generation():
    generator = ActionGenerator(
        openai_api_key="your-openai-api-key"
    )
    await generator.initialize()
    
    # This would typically be called by the correlation processor
    # For testing, you can create a test correlation
    test_correlation_id = "test_corr_123"
    
    # The correlation would need to exist in Redis for this to work
    # In practice, you'd create test correlation data first
    
    actions = await generator.get_user_actions("test_user", limit=5)
    print(f"✅ Found {len(actions)} actions for user")

if __name__ == "__main__":
    asyncio.run(test_action_generation())
```

## Step 7: Monitor and Debug

### Check System Health

```bash
# Check Redis connection
redis-cli ping

# Check system health via API
curl http://localhost:8000/system/streaming/health

# Check processing statistics
curl http://localhost:8000/system/streaming/stats
```

### View Logs

The system uses structured logging. Key log entries to watch:

```bash
# Event processing
grep "Processing event" logs/saathy.log

# Correlation creation
grep "Created correlation group" logs/saathy.log

# Action generation
grep "Generated.*actions" logs/saathy.log

# Errors
grep "ERROR" logs/saathy.log
```

### Common Issues

**Redis Connection Issues**:
```bash
# Check Redis is running
redis-cli ping

# Check Redis config
grep redis .env
```

**Platform Authentication Issues**:
```bash
# Test tokens individually
python test_platform_connections.py
```

**No Actions Generated**:
- Check daily limits: Events need correlation strength > 0.3
- Verify OpenAI API key has GPT-4 access
- Ensure context validation passes

**Missing Correlations**:
- Events must be within 30-minute window
- Check similarity scoring (project context, keywords)
- Verify event extraction (keywords, urgency scores)

## Step 8: Production Deployment

### Environment Variables

Set production environment variables:

```bash
# Production Redis
REDIS_URL="rediss://prod-redis-cluster:6380"
REDIS_PASSWORD="prod-redis-password"

# Production OpenAI
OPENAI_API_KEY="sk-prod-openai-key"

# Enable production logging
LOG_LEVEL="INFO"
ENVIRONMENT="production"
```

### Monitoring

Set up monitoring for:
- Redis memory usage and connections
- OpenAI API usage and costs
- Event processing latency
- Action generation success rates
- User action completion rates

### Scaling

For high-volume environments:
- Use Redis Cluster for event storage
- Deploy multiple correlation processors
- Implement action generation rate limiting
- Add event preprocessing for keyword extraction

## Next Steps

1. **Integration**: Add API endpoints to your FastAPI app
2. **Frontend**: Build UI for action management
3. **Notifications**: Set up Slack/email notifications for actions
4. **Analytics**: Track action usefulness and user feedback
5. **Optimization**: Tune correlation algorithms based on usage patterns

## Support

For issues:
1. Check the logs for error messages
2. Verify all environment variables are set
3. Test platform connections individually
4. Review Redis storage and queue status
5. Check the comprehensive test suite for examples