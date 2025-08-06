"""Test cases for the context synthesizer."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.saathy.intelligence.context_synthesizer import ContextSynthesizer
from src.saathy.intelligence.models.actions import ContextBundle


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock()
    redis_mock.setex = AsyncMock()
    return redis_mock


@pytest.fixture
def synthesizer(mock_redis):
    """Create a ContextSynthesizer with mocked Redis."""
    with patch('redis.asyncio.from_url', return_value=mock_redis):
        synthesizer = ContextSynthesizer()
        synthesizer.redis = mock_redis
        return synthesizer


@pytest.fixture
def sample_correlation_data():
    """Create sample correlation data for testing."""
    base_time = datetime.now()
    return {
        "correlation_id": "corr_test_123",
        "user_id": "user123",
        "primary_event": {
            "event_id": "slack_msg_123",
            "platform": "slack",
            "event_type": "slack_message",
            "timestamp": base_time.isoformat(),
            "user_id": "user123",
            "keywords": ["urgent", "review"],
            "project_context": "saathy-core",
            "urgency_score": 0.8,
            "channel_name": "eng-alerts",
            "message_text": "Need urgent review of PR #456",
            "mentioned_users": ["alice", "bob"]
        },
        "related_events": [
            {
                "event_id": "github_pr_456",
                "platform": "github",
                "event_type": "github_pr",
                "timestamp": (base_time - timedelta(minutes=10)).isoformat(),
                "user_id": "user123",
                "keywords": ["review", "security"],
                "project_context": "saathy-core",
                "urgency_score": 0.6,
                "repository": "company/saathy-core",
                "action": "opened",
                "pr_number": 456,
                "similarity_score": 0.8
            },
            {
                "event_id": "notion_page_789",
                "platform": "notion",
                "event_type": "notion_page_update",
                "timestamp": (base_time - timedelta(minutes=15)).isoformat(),
                "user_id": "user123",
                "keywords": ["status", "security"],
                "project_context": "saathy-core",
                "urgency_score": 0.4,
                "page_title": "Security Review Checklist",
                "change_type": "updated",
                "similarity_score": 0.6
            }
        ],
        "status": "pending_action_generation",
        "created_at": base_time.isoformat()
    }


class TestContextSynthesizer:
    """Test ContextSynthesizer functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis):
        """Test ContextSynthesizer initialization."""
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            synthesizer = ContextSynthesizer()
            await synthesizer.initialize()
            
            mock_redis.ping.assert_called_once()
            assert synthesizer.redis is not None

    @pytest.mark.asyncio
    async def test_synthesize_context_success(self, synthesizer, mock_redis, sample_correlation_data):
        """Test successful context synthesis."""
        correlation_id = "corr_test_123"
        
        # Mock Redis response
        mock_redis.get.return_value = json.dumps(sample_correlation_data)
        
        context_bundle = await synthesizer.synthesize_context(correlation_id)
        
        assert context_bundle is not None
        assert isinstance(context_bundle, ContextBundle)
        assert context_bundle.correlation_id == correlation_id
        assert context_bundle.user_id == "user123"
        assert len(context_bundle.related_events) == 2
        assert len(context_bundle.key_insights) > 0
        assert context_bundle.synthesized_context != ""

    @pytest.mark.asyncio
    async def test_synthesize_context_no_correlation_found(self, synthesizer, mock_redis):
        """Test context synthesis when correlation doesn't exist."""
        correlation_id = "nonexistent_corr"
        
        # Mock Redis returning None
        mock_redis.get.return_value = None
        
        context_bundle = await synthesizer.synthesize_context(correlation_id)
        
        assert context_bundle is None

    def test_organize_by_platform(self, synthesizer, sample_correlation_data):
        """Test organizing events by platform."""
        primary_event = sample_correlation_data["primary_event"]
        related_events = sample_correlation_data["related_events"]
        
        platform_data = synthesizer.organize_by_platform(primary_event, related_events)
        
        # Check Slack data
        assert "slack" in platform_data
        assert len(platform_data["slack"]["events"]) == 1
        assert "eng-alerts" in platform_data["slack"]["channels"]
        assert len(platform_data["slack"]["messages"]) == 1
        assert "Need urgent review" in platform_data["slack"]["messages"][0]["text"]
        
        # Check GitHub data
        assert "github" in platform_data
        assert len(platform_data["github"]["events"]) == 1
        assert "company/saathy-core" in platform_data["github"]["repos"]
        assert len(platform_data["github"]["prs"]) == 1
        assert platform_data["github"]["prs"][0]["number"] == 456
        
        # Check Notion data
        assert "notion" in platform_data
        assert len(platform_data["notion"]["events"]) == 1
        assert len(platform_data["notion"]["pages"]) == 1
        assert "Security Review Checklist" in platform_data["notion"]["pages"][0]["title"]

    def test_extract_insights(self, synthesizer, sample_correlation_data):
        """Test extracting key insights from events."""
        primary_event = sample_correlation_data["primary_event"]
        related_events = sample_correlation_data["related_events"]
        
        insights = synthesizer.extract_insights(primary_event, related_events)
        
        assert len(insights) > 0
        
        # Should detect cross-platform activity
        cross_platform_insight = next((i for i in insights if "multiple platforms" in i), None)
        assert cross_platform_insight is not None
        
        # Should detect project context
        project_insight = next((i for i in insights if "saathy-core" in i), None)
        assert project_insight is not None
        
        # Should detect frequent keywords
        keyword_insight = next((i for i in insights if "Key themes" in i), None)
        assert keyword_insight is not None

    def test_extract_platform_specific_insights(self, synthesizer, sample_correlation_data):
        """Test extracting platform-specific insights."""
        platform_data = {
            "slack": {
                "events": [sample_correlation_data["primary_event"]],
                "channels": ["eng-alerts"],
                "messages": [{"text": "urgent review", "user": "user123"}]
            },
            "github": {
                "events": [sample_correlation_data["related_events"][0]],
                "repos": ["company/saathy-core"],
                "prs": [{"number": 456, "action": "opened"}]
            },
            "notion": {
                "events": [sample_correlation_data["related_events"][1]],
                "pages": [{"title": "Security Review", "change_type": "updated"}]
            }
        }
        
        insights = synthesizer._extract_platform_specific_insights(platform_data)
        
        assert len(insights) > 0
        
        # Should have Slack insight
        slack_insight = next((i for i in insights if "Slack discussion" in i), None)
        assert slack_insight is not None
        
        # Should have GitHub insight
        github_insight = next((i for i in insights if "PR workflow" in i), None)
        assert github_insight is not None

    def test_identify_urgency_signals(self, synthesizer, sample_correlation_data):
        """Test identifying urgency signals."""
        primary_event = sample_correlation_data["primary_event"]
        related_events = sample_correlation_data["related_events"]
        
        urgency_signals = synthesizer.identify_urgency_signals(primary_event, related_events)
        
        assert len(urgency_signals) > 0
        
        # Should detect high urgency events
        high_urgency_signal = next((s for s in urgency_signals if "high-urgency events" in s), None)
        assert high_urgency_signal is not None
        
        # Should detect urgent keywords
        urgent_keywords_signal = next((s for s in urgency_signals if "Urgent indicators" in s), None)
        assert urgent_keywords_signal is not None
        
        # Should detect PR activity
        pr_signal = next((s for s in urgency_signals if "Pull request" in s), None)
        assert pr_signal is not None

    def test_generate_context_narrative_slack_primary(self, synthesizer, sample_correlation_data):
        """Test narrative generation with Slack as primary event."""
        primary_event = sample_correlation_data["primary_event"]
        related_events = sample_correlation_data["related_events"]
        platform_data = synthesizer.organize_by_platform(primary_event, related_events)
        key_insights = ["Cross-platform activity", "Security focus"]
        
        narrative = synthesizer.generate_context_narrative(
            primary_event, related_events, platform_data, key_insights
        )
        
        assert "Slack message in #eng-alerts" in narrative
        assert "followed by" in narrative
        assert "github, notion" in narrative.lower()
        assert "Cross-platform activity" in narrative

    def test_generate_context_narrative_github_primary(self, synthesizer):
        """Test narrative generation with GitHub as primary event."""
        primary_event = {
            "platform": "github",
            "repository": "org/repo",
            "action": "opened",
            "timestamp": datetime.now().isoformat()
        }
        related_events = []
        platform_data = {}
        key_insights = ["PR workflow"]
        
        narrative = synthesizer.generate_context_narrative(
            primary_event, related_events, platform_data, key_insights
        )
        
        assert "GitHub opened in org/repo" in narrative
        assert "PR workflow" in narrative

    def test_generate_context_narrative_notion_primary(self, synthesizer):
        """Test narrative generation with Notion as primary event."""
        primary_event = {
            "platform": "notion",
            "change_type": "updated",
            "page_title": "Project Plan",
            "timestamp": datetime.now().isoformat()
        }
        related_events = []
        platform_data = {}
        key_insights = []
        
        narrative = synthesizer.generate_context_narrative(
            primary_event, related_events, platform_data, key_insights
        )
        
        assert "Notion page updated: Project Plan" in narrative

    def test_generate_platform_details(self, synthesizer):
        """Test generating platform-specific details."""
        platform_data = {
            "slack": {
                "channels": ["general", "eng-alerts"],
                "messages": [
                    {"text": "Hello world", "user": "user1"},
                    {"text": "Need help", "user": "user2"}
                ]
            },
            "github": {
                "repos": ["org/repo1"],
                "prs": [{"number": 123, "action": "opened"}],
                "commits": [{"sha": "abc123"}]
            },
            "notion": {
                "pages": [{"title": "Meeting Notes", "change_type": "created"}]
            }
        }
        
        details = synthesizer._generate_platform_details("slack", platform_data["slack"])
        assert "Channels: general, eng-alerts" in details
        assert "Recent messages" in details
        
        details = synthesizer._generate_platform_details("github", platform_data["github"])
        assert "Repositories: org/repo1" in details
        assert "PR #123 (opened)" in details
        assert "Commits: abc123" in details
        
        details = synthesizer._generate_platform_details("notion", platform_data["notion"])
        assert "Meeting Notes (created)" in details

    @pytest.mark.asyncio
    async def test_store_context_bundle(self, synthesizer, mock_redis):
        """Test storing context bundle."""
        context_bundle = ContextBundle(
            correlation_id="test_corr",
            user_id="user123",
            primary_event={"event_id": "primary"},
            related_events=[],
            synthesized_context="Test context",
            key_insights=["Test insight"],
            urgency_signals=["Test signal"],
            platform_data={},
            correlation_strength=0.7,
            created_at=datetime.now()
        )
        
        await synthesizer.store_context_bundle(context_bundle)
        
        # Verify Redis storage
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "context:test_corr"
        assert call_args[0][1] == 24 * 60 * 60  # 24 hours

    @pytest.mark.asyncio
    async def test_get_context_bundle(self, synthesizer, mock_redis):
        """Test retrieving context bundle."""
        correlation_id = "test_corr"
        context_data = {
            "correlation_id": correlation_id,
            "user_id": "user123",
            "primary_event": {"event_id": "primary"},
            "related_events": [],
            "synthesized_context": "Test context",
            "key_insights": ["Test insight"],
            "urgency_signals": ["Test signal"],
            "platform_data": {},
            "correlation_strength": 0.7,
            "created_at": datetime.now().isoformat()
        }
        
        mock_redis.get.return_value = json.dumps(context_data)
        
        result = await synthesizer.get_context_bundle(correlation_id)
        
        assert result == context_data
        mock_redis.get.assert_called_once_with(f"context:{correlation_id}")

    @pytest.mark.asyncio
    async def test_error_handling_in_synthesize_context(self, synthesizer, mock_redis):
        """Test error handling in synthesize_context."""
        correlation_id = "error_corr"
        
        # Make Redis get fail
        mock_redis.get.side_effect = Exception("Redis error")
        
        result = await synthesizer.synthesize_context(correlation_id)
        
        assert result is None

    def test_process_slack_event(self, synthesizer):
        """Test processing Slack event data."""
        slack_data = {"events": [], "channels": set(), "messages": []}
        event = {
            "platform": "slack",
            "channel_name": "general",
            "message_text": "Hello world",
            "timestamp": datetime.now().isoformat(),
            "user_id": "user123"
        }
        
        synthesizer._process_slack_event(event, slack_data)
        
        assert len(slack_data["events"]) == 1
        assert "general" in slack_data["channels"]
        assert len(slack_data["messages"]) == 1
        assert slack_data["messages"][0]["text"] == "Hello world"

    def test_process_github_event(self, synthesizer):
        """Test processing GitHub event data."""
        github_data = {"events": [], "repos": set(), "prs": [], "commits": [], "issues": []}
        event = {
            "platform": "github",
            "repository": "org/repo",
            "pr_number": 123,
            "action": "opened",
            "commit_sha": "abc123def"
        }
        
        synthesizer._process_github_event(event, github_data)
        
        assert len(github_data["events"]) == 1
        assert "org/repo" in github_data["repos"]
        assert len(github_data["prs"]) == 1
        assert github_data["prs"][0]["number"] == 123
        assert len(github_data["commits"]) == 1

    def test_process_notion_event(self, synthesizer):
        """Test processing Notion event data."""
        notion_data = {"events": [], "pages": [], "databases": set()}
        event = {
            "platform": "notion",
            "page_title": "Meeting Notes",
            "change_type": "created",
            "database_id": "db123",
            "timestamp": datetime.now().isoformat()
        }
        
        synthesizer._process_notion_event(event, notion_data)
        
        assert len(notion_data["events"]) == 1
        assert len(notion_data["pages"]) == 1
        assert notion_data["pages"][0]["title"] == "Meeting Notes"
        assert "db123" in notion_data["databases"]