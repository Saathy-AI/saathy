# Saathy V1: Proactive Action Intelligence System

## Overview

Saathy's core differentiator is its **Proactive Action Intelligence** system that watches user work across platforms and suggests specific, actionable next steps. This system consists of two main components:

1. **Real-Time Event Pipeline** (Streaming) - Captures and correlates events from Slack, GitHub, and Notion
2. **Context Synthesis & Action Generation** (Intelligence) - Uses AI to synthesize context and generate actionable recommendations

## Architecture Flow

```mermaid
graph TD
    A[Slack WebSocket] --> D[Event Manager]
    B[GitHub Webhooks] --> D
    C[Notion Polling] --> D
    
    D --> E[Redis Event Storage]
    D --> F[Event Correlator]
    
    F --> G[Context Synthesizer]
    G --> H[Action Generator]
    H --> I[GPT-4o]
    
    I --> J[Generated Actions]
    J --> K[User Notifications]
```

## Component Details

### 🎯 Event Streaming Pipeline

#### Event Manager (`streaming/event_manager.py`)
**Central coordinator for all incoming events**

- **Responsibilities:**
  - Store events in Redis with 30-day retention
  - Maintain user timelines and platform indexes
  - Queue events for correlation processing
  - Manage background correlation processor

- **Key Methods:**
  ```python
  async def process_event(event: BaseEvent)  # Main entry point
  async def store_event(event: BaseEvent)    # Redis storage
  async def queue_for_correlation(event: BaseEvent)  # Correlation queue
  async def get_recent_events(user_id: str, hours: int = 2)  # User timeline
  ```

#### Event Models (`streaming/models/events.py`)
**Standardized event representation across platforms**

- **BaseEvent**: Common fields (event_id, timestamp, user_id, platform, keywords, urgency_score)
- **SlackEvent**: Slack-specific (channel_id, message_text, thread_ts, reactions)
- **GitHubEvent**: GitHub-specific (repository, pr_number, commit_sha, files_changed)
- **NotionEvent**: Notion-specific (page_id, page_title, database_id, properties_changed)

#### Platform Processors

**Slack Stream Processor (`streaming/slack_stream.py`)**
- Uses Slack Socket Mode for real-time WebSocket events
- Extracts mentions, keywords, and calculates urgency scores
- Infers project context from channel names and content
- Caches user/channel info to reduce API calls

**GitHub Webhook Processor (`streaming/github_webhook.py`)**
- Handles push, PR, issue, and comment events
- Validates webhook signatures for security
- Extracts commit keywords, PR contexts, and urgency indicators
- Supports complex GitHub workflows (PR reviews, issue tracking)

**Notion Polling Service (`streaming/notion_poller.py`)**
- Polls Notion API every 5 minutes for changes
- Tracks page versions to detect updates
- Caches database and user information
- Extracts keywords from page titles and property changes

### 🧠 Intelligence & Action Generation

#### Event Correlator (`streaming/event_correlator.py`)
**Finds and groups related events using similarity algorithms**

- **Similarity Factors:**
  - **Project Context** (0.4 weight): Same repository/workspace/project
  - **Keyword Overlap** (0.3 weight): Shared technical terms and concepts
  - **Cross-Platform Bonus** (0.2 weight): Related Slack ↔ GitHub ↔ Notion activity
  - **Time Proximity** (0.15 weight): Events within 30-minute window
  - **Event Type Correlation** (0.15 weight): Common workflows (Slack → GitHub PR)
  - **Urgency Alignment** (0.1 weight): Similar urgency levels

- **Correlation Groups:**
  - Minimum similarity threshold: 0.3
  - Maximum 5 related events per group
  - Stored in Redis with 24-hour expiration

#### Context Synthesizer (`intelligence/context_synthesizer.py`)
**Combines correlated events into rich context bundles**

- **Platform Organization:**
  - Groups events by platform (Slack, GitHub, Notion)
  - Extracts platform-specific details (channels, repos, pages)
  - Identifies cross-platform patterns

- **Key Insights Extraction:**
  - Cross-platform activity detection
  - Project context identification
  - Keyword concentration analysis
  - Time pattern recognition

- **Urgency Signals:**
  - High urgency score events (>0.5)
  - Urgent keywords (critical, asap, emergency)
  - PR review requests
  - Direct mentions and assignments

#### Action Generator (`intelligence/action_generator.py`)
**GPT-4 powered specific action creation**

- **Process Flow:**
  1. **Daily Limits Check**: Max 20 actions per user per day
  2. **Context Validation**: GPT-4 validates context sufficiency
  3. **Action Generation**: GPT-4o creates specific actions
  4. **Quality Control**: Validates and refines generic suggestions
  5. **Link Enhancement**: Adds platform-specific deep links
  6. **Storage**: Stores with priority-based expiration

- **Action Properties:**
  - **Title**: Specific, actionable (max 60 chars)
  - **Description**: Detailed with full context
  - **Priority**: urgent/high/medium/low/fyi
  - **Type**: review/respond/update/meeting/follow_up/create/fix
  - **Time Estimate**: 5-30 minutes
  - **Direct Links**: Platform-specific URLs for immediate action

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL="redis://localhost:6379"
REDIS_PASSWORD="your_redis_password"

# OpenAI Configuration
OPENAI_API_KEY="your_openai_api_key"

# Slack Configuration
SLACK_BOT_TOKEN="xoxb-your-bot-token"
SLACK_APP_TOKEN="xapp-your-app-token"

# GitHub Configuration
GITHUB_TOKEN="your_github_token"
GITHUB_WEBHOOK_SECRET="your_webhook_secret"

# Notion Configuration
NOTION_TOKEN="your_notion_integration_token"

# Event Processing Settings
EVENT_CORRELATION_WINDOW_MINUTES=30
EVENT_RETENTION_DAYS=30
ACTION_GENERATION_ENABLED=true
MAX_ACTIONS_PER_USER_PER_DAY=20
```

### Redis Configuration (config.py)

```python
class Settings(BaseSettings):
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[SecretStr] = None
    
    # Event processing settings
    event_correlation_window_minutes: int = 30
    event_retention_days: int = 30
    action_generation_enabled: bool = True
    max_actions_per_user_per_day: int = 20
    
    @property
    def redis_password_str(self) -> Optional[str]:
        return self.redis_password.get_secret_value() if self.redis_password else None
```

## Usage Examples

### Starting the Streaming System

```python
from src.saathy.streaming import EventManager, SlackStreamProcessor
from src.saathy.intelligence import ActionGenerator

# Initialize components
event_manager = EventManager()
slack_processor = SlackStreamProcessor(
    bot_token=settings.slack_bot_token_str,
    app_token=settings.slack_app_token_str,
    event_manager=event_manager
)
action_generator = ActionGenerator(
    openai_api_key=settings.openai_api_key_str
)

# Start services
await event_manager.initialize()
await slack_processor.start()
await action_generator.start_action_generation_processor()
```

### Processing Events

```python
# Slack message event
slack_event = SlackEvent(
    event_id="slack_msg_123",
    event_type=EventType.SLACK_MESSAGE,
    timestamp=datetime.now(),
    user_id="U123456",
    platform="slack",
    raw_data={"channel": "C123"},
    channel_id="C123456",
    channel_name="eng-alerts",
    message_text="Need urgent review of PR #456",
    keywords=["urgent", "review"],
    urgency_score=0.8
)

await event_manager.process_event(slack_event)
```

### Retrieving User Actions

```python
# Get recent actions for a user
user_actions = await action_generator.get_user_actions("user123", limit=10)

for action in user_actions:
    print(f"Action: {action.title}")
    print(f"Priority: {action.priority}")
    print(f"Time Estimate: {action.estimated_time_minutes} minutes")
    print(f"Links: {[link.url for link in action.action_links]}")
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run streaming tests only
pytest tests/streaming/

# Run intelligence tests only
pytest tests/intelligence/

# Run integration tests
pytest tests/test_integration.py

# Run with coverage
pytest --cov=src/saathy --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── streaming/
│   ├── test_models.py            # Event model validation
│   ├── test_event_manager.py     # Event storage and queuing
│   └── test_event_correlator.py  # Correlation logic and similarity
├── intelligence/
│   ├── test_context_synthesizer.py  # Context synthesis
│   └── test_action_generator.py     # Action generation and GPT-4
└── test_integration.py           # End-to-end pipeline tests
```

## Example Output

### Generated Action

```json
{
  "action_id": "action_user123_1701234567",
  "title": "Review PR #456 for security vulnerability in auth module",
  "description": "Review the pull request that addresses a critical security vulnerability in the authentication module, triggered by urgent discussion in #eng-alerts. The PR includes changes to user login validation and session management.",
  "priority": "urgent",
  "action_type": "review",
  "reasoning": "Security vulnerability requires immediate attention based on Slack discussion mentioning 'urgent' and 'security' keywords, combined with recent GitHub PR activity in the same project.",
  "estimated_time_minutes": 20,
  "action_links": [
    {
      "platform": "github",
      "url": "https://github.com/company/saathy-core/pull/456",
      "label": "View PR #456",
      "action_type": "view"
    },
    {
      "platform": "slack",
      "url": "slack://channel?team=T123456&id=C123456",
      "label": "View discussion in #eng-alerts",
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
```

### Context Bundle

```json
{
  "correlation_id": "corr_user123_1701234560",
  "user_id": "user123",
  "synthesized_context": "Started with a Slack message in #eng-alerts about urgent PR review, followed by related GitHub and Notion activity. Key context: Cross-platform activity spanning multiple platforms; Related to project saathy-core; Key themes: urgent, review, security.",
  "key_insights": [
    "Activity spans multiple platforms: slack, github, notion",
    "Related to project(s): saathy-core",
    "Key themes: urgent, review, security",
    "Time-sensitive activity within 15 minutes"
  ],
  "urgency_signals": [
    "2 high-urgency events detected",
    "Urgent indicators: urgent, security",
    "Pull request activity requires attention",
    "You were mentioned 2 time(s)"
  ],
  "platform_data": {
    "slack": {
      "channels": ["eng-alerts"],
      "messages": [
        {
          "text": "Need urgent review of PR #456 - security vulnerability in auth module!",
          "timestamp": "2023-11-29T10:25:00Z",
          "user": "user123"
        }
      ]
    },
    "github": {
      "repos": ["company/saathy-core"],
      "prs": [
        {
          "number": 456,
          "action": "opened",
          "repo": "company/saathy-core"
        }
      ]
    }
  },
  "correlation_strength": 0.85
}
```

## Performance Considerations

### Redis Usage
- **Event Storage**: ~1KB per event, 30-day retention
- **User Timelines**: Sorted sets for chronological access
- **Correlation Groups**: 24-hour expiration
- **Action Queues**: FIFO processing with Redis lists

### API Rate Limits
- **Slack**: Socket Mode avoids rate limits
- **GitHub**: Webhook-based, no polling
- **Notion**: 5-minute polling intervals
- **OpenAI**: GPT-4o calls limited by daily action limits

### Scaling Considerations
- **Horizontal**: Multiple workers can process correlation queues
- **Redis Clustering**: For high-volume event storage
- **Action Generation**: Queue-based processing prevents overload
- **Context Validation**: Prevents unnecessary GPT-4 calls

## Monitoring & Debugging

### Key Metrics
- Events processed per minute
- Correlation groups created
- Actions generated per user
- GPT-4 API usage and costs
- Redis memory usage

### Logging
- Structured logging with correlation IDs
- Event processing timestamps
- Action generation reasoning
- Error handling with context

### Health Checks
- Redis connectivity
- Platform API connectivity
- Background processor status
- Action generation queue health

## Troubleshooting

### Common Issues

**No actions generated:**
- Check daily limits: `GET /actions/user/{user_id}/stats`
- Verify correlation strength > 0.3
- Check context validation logs
- Ensure GPT-4 API key is valid

**Missing event correlation:**
- Verify events are within 30-minute window
- Check similarity scoring thresholds
- Validate project context extraction
- Review keyword extraction logic

**Platform connection issues:**
- Slack: Verify Socket Mode app tokens
- GitHub: Check webhook signature validation
- Notion: Confirm integration permissions
- Redis: Check connectivity and authentication

## Future Enhancements

### Short Term (2-4 weeks)
- Web interface for action management
- Slack notifications for generated actions
- Action completion tracking and analytics
- Enhanced prompt engineering for better specificity

### Medium Term (1-2 months)
- Additional platforms (Linear, Jira, Figma)
- Machine learning for urgency scoring
- User preference learning
- Advanced correlation algorithms

### Long Term (3-6 months)
- Predictive action suggestions
- Team collaboration patterns
- Integration with calendar and email
- Mobile notifications and quick actions