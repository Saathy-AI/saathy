"""Event data models for cross-platform activity tracking."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    """Types of events that can be processed."""
    SLACK_MESSAGE = "slack_message"
    SLACK_REACTION = "slack_reaction"
    GITHUB_PUSH = "github_push"
    GITHUB_PR = "github_pr"
    GITHUB_ISSUE = "github_issue"
    GITHUB_COMMENT = "github_comment"
    NOTION_PAGE_UPDATE = "notion_page_update"
    NOTION_DATABASE_UPDATE = "notion_database_update"

class BaseEvent(BaseModel):
    """Base event model for all platform events."""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType
    timestamp: datetime
    user_id: str = Field(..., description="User who triggered the event")
    platform: str = Field(..., description="slack, github, or notion")
    raw_data: Dict[str, Any] = Field(..., description="Original platform data")
    
    # For correlation and analysis
    mentioned_users: List[str] = Field(default=[], description="Users mentioned in event")
    keywords: List[str] = Field(default=[], description="Extracted keywords")
    project_context: Optional[str] = Field(None, description="Project/repo/workspace")
    urgency_score: float = Field(default=0.0, description="0-1 urgency indicator")

class SlackEvent(BaseEvent):
    """Slack-specific event model."""
    channel_id: str
    channel_name: str
    message_text: Optional[str] = None
    thread_ts: Optional[str] = None
    is_thread_reply: bool = False
    reactions: List[str] = Field(default=[])
    message_ts: Optional[str] = None

class GitHubEvent(BaseEvent):
    """GitHub-specific event model."""
    repository: str
    action: str  # opened, closed, pushed, etc.
    pr_number: Optional[int] = None
    issue_number: Optional[int] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    files_changed: List[str] = Field(default=[])
    commit_message: Optional[str] = None

class NotionEvent(BaseEvent):
    """Notion-specific event model."""
    page_id: str
    page_title: str
    database_id: Optional[str] = None
    change_type: str  # created, updated, deleted
    properties_changed: List[str] = Field(default=[])
    page_url: Optional[str] = None