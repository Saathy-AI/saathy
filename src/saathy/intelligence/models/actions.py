"""Data models for AI-generated actions and context synthesis."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ActionPriority(str, Enum):
    """Priority levels for generated actions."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FYI = "fyi"

class ActionType(str, Enum):
    """Types of actions that can be generated."""
    REVIEW = "review"           # Review PR, document, etc.
    RESPOND = "respond"         # Reply to message, comment
    UPDATE = "update"           # Update document, status
    MEETING = "meeting"         # Schedule, prepare for meeting
    FOLLOW_UP = "follow_up"     # Follow up on previous item
    CREATE = "create"           # Create new document, issue
    FIX = "fix"                # Fix bug, issue

class ActionLink(BaseModel):
    """Link to take action on a platform."""
    platform: str = Field(..., description="slack, github, notion")
    url: str = Field(..., description="Direct link to take action")
    label: str = Field(..., description="What this link does")
    action_type: str = Field(..., description="view, edit, comment, reply, etc.")

class GeneratedAction(BaseModel):
    """AI-generated action item with full context and metadata."""
    action_id: str = Field(..., description="Unique action identifier")
    title: str = Field(..., description="Clear, actionable title")
    description: str = Field(..., description="Detailed description with context")
    priority: ActionPriority
    action_type: ActionType
    
    # Context and reasoning
    reasoning: str = Field(..., description="Why this action is suggested")
    context_summary: str = Field(..., description="Relevant background context")
    estimated_time_minutes: int = Field(default=15, description="Estimated time to complete")
    
    # Links and actions
    action_links: List[ActionLink] = Field(default=[], description="Links to take action")
    related_people: List[str] = Field(default=[], description="People involved or to notify")
    
    # Metadata
    user_id: str = Field(..., description="User this action is for")
    correlation_id: str = Field(..., description="Event correlation that generated this")
    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(None, description="When action becomes irrelevant")
    
    # Tracking
    status: str = Field(default="pending", description="pending, completed, dismissed")
    completed_at: Optional[datetime] = None
    user_feedback: Optional[str] = Field(None, description="User feedback on usefulness")
    feedback_score: Optional[float] = Field(None, description="0-1 score from user feedback")

class ContextBundle(BaseModel):
    """Synthesized context for action generation."""
    correlation_id: str
    user_id: str
    primary_event: Dict[str, Any]
    related_events: List[Dict[str, Any]]
    synthesized_context: str
    key_insights: List[str]
    urgency_signals: List[str]
    platform_data: Dict[str, Any]  # Organized data by platform
    correlation_strength: float = Field(default=0.0, description="0-1 strength of correlation")
    created_at: datetime = Field(default_factory=datetime.now)

class ActionFeedback(BaseModel):
    """User feedback on action usefulness."""
    action_id: str
    user_id: str
    helpful: bool
    completed: bool
    feedback_text: Optional[str] = None
    time_taken_minutes: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ActionMetrics(BaseModel):
    """Metrics for action generation performance."""
    user_id: str
    date: datetime
    actions_generated: int
    actions_completed: int
    actions_dismissed: int
    avg_completion_time_minutes: Optional[float]
    avg_feedback_score: Optional[float]
    most_common_action_type: Optional[str]
    most_active_platform: Optional[str]