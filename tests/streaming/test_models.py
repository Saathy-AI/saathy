"""Test cases for streaming event models."""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.saathy.streaming.models.events import (
    BaseEvent,
    SlackEvent,
    GitHubEvent,
    NotionEvent,
    EventType,
)


class TestEventModels:
    """Test event model validation and functionality."""

    def test_base_event_creation(self):
        """Test BaseEvent creation with required fields."""
        event_data = {
            "event_id": "test_event_123",
            "event_type": EventType.SLACK_MESSAGE,
            "timestamp": datetime.now(),
            "user_id": "user123",
            "platform": "slack",
            "raw_data": {"test": "data"},
        }
        
        event = BaseEvent(**event_data)
        
        assert event.event_id == "test_event_123"
        assert event.event_type == EventType.SLACK_MESSAGE
        assert event.platform == "slack"
        assert event.user_id == "user123"
        assert event.keywords == []
        assert event.mentioned_users == []
        assert event.urgency_score == 0.0

    def test_base_event_with_optional_fields(self):
        """Test BaseEvent with optional fields populated."""
        event_data = {
            "event_id": "test_event_456",
            "event_type": EventType.GITHUB_PR,
            "timestamp": datetime.now(),
            "user_id": "user456",
            "platform": "github",
            "raw_data": {"pr": "data"},
            "mentioned_users": ["alice", "bob"],
            "keywords": ["review", "urgent"],
            "project_context": "saathy-core",
            "urgency_score": 0.8,
        }
        
        event = BaseEvent(**event_data)
        
        assert event.mentioned_users == ["alice", "bob"]
        assert event.keywords == ["review", "urgent"]
        assert event.project_context == "saathy-core"
        assert event.urgency_score == 0.8

    def test_slack_event_creation(self):
        """Test SlackEvent with Slack-specific fields."""
        slack_data = {
            "event_id": "slack_123",
            "event_type": EventType.SLACK_MESSAGE,
            "timestamp": datetime.now(),
            "user_id": "U123456",
            "platform": "slack",
            "raw_data": {"channel": "C123"},
            "channel_id": "C123456",
            "channel_name": "general",
            "message_text": "Hello team!",
            "thread_ts": "1234567890.123",
            "is_thread_reply": True,
            "reactions": ["👍", "🎉"],
            "message_ts": "1234567890.456",
        }
        
        event = SlackEvent(**slack_data)
        
        assert event.channel_id == "C123456"
        assert event.channel_name == "general"
        assert event.message_text == "Hello team!"
        assert event.is_thread_reply is True
        assert event.reactions == ["👍", "🎉"]

    def test_github_event_creation(self):
        """Test GitHubEvent with GitHub-specific fields."""
        github_data = {
            "event_id": "github_456",
            "event_type": EventType.GITHUB_PR,
            "timestamp": datetime.now(),
            "user_id": "githubuser",
            "platform": "github",
            "raw_data": {"pull_request": {"number": 123}},
            "repository": "org/repo",
            "action": "opened",
            "pr_number": 123,
            "branch": "feature/new-feature",
            "commit_sha": "abc123def456",
            "files_changed": ["src/main.py", "tests/test_main.py"],
            "commit_message": "Add new feature",
        }
        
        event = GitHubEvent(**github_data)
        
        assert event.repository == "org/repo"
        assert event.action == "opened"
        assert event.pr_number == 123
        assert event.branch == "feature/new-feature"
        assert event.commit_sha == "abc123def456"
        assert event.files_changed == ["src/main.py", "tests/test_main.py"]

    def test_notion_event_creation(self):
        """Test NotionEvent with Notion-specific fields."""
        notion_data = {
            "event_id": "notion_789",
            "event_type": EventType.NOTION_PAGE_UPDATE,
            "timestamp": datetime.now(),
            "user_id": "notion_user",
            "platform": "notion",
            "raw_data": {"page": {"id": "page123"}},
            "page_id": "page123",
            "page_title": "Project Requirements",
            "database_id": "db456",
            "change_type": "updated",
            "properties_changed": ["Status", "Assignee"],
            "page_url": "https://notion.so/page123",
        }
        
        event = NotionEvent(**notion_data)
        
        assert event.page_id == "page123"
        assert event.page_title == "Project Requirements"
        assert event.database_id == "db456"
        assert event.change_type == "updated"
        assert event.properties_changed == ["Status", "Assignee"]
        assert event.page_url == "https://notion.so/page123"

    def test_event_type_enum(self):
        """Test EventType enum values."""
        assert EventType.SLACK_MESSAGE == "slack_message"
        assert EventType.SLACK_REACTION == "slack_reaction"
        assert EventType.GITHUB_PUSH == "github_push"
        assert EventType.GITHUB_PR == "github_pr"
        assert EventType.GITHUB_ISSUE == "github_issue"
        assert EventType.NOTION_PAGE_UPDATE == "notion_page_update"

    def test_event_serialization(self):
        """Test event serialization to JSON."""
        event = SlackEvent(
            event_id="test_serialize",
            event_type=EventType.SLACK_MESSAGE,
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            user_id="user123",
            platform="slack",
            raw_data={"test": "data"},
            channel_id="C123",
            channel_name="test",
        )
        
        json_data = event.model_dump_json()
        assert "test_serialize" in json_data
        assert "slack_message" in json_data
        assert "C123" in json_data

    def test_event_validation_missing_required_field(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValueError):
            BaseEvent(
                # Missing event_id
                event_type=EventType.SLACK_MESSAGE,
                timestamp=datetime.now(),
                user_id="user123",
                platform="slack",
                raw_data={},
            )

    def test_event_validation_invalid_platform(self):
        """Test event creation with valid platforms."""
        # Valid platforms should work
        valid_platforms = ["slack", "github", "notion"]
        
        for platform in valid_platforms:
            event = BaseEvent(
                event_id="test",
                event_type=EventType.SLACK_MESSAGE,
                timestamp=datetime.now(),
                user_id="user123",
                platform=platform,
                raw_data={},
            )
            assert event.platform == platform