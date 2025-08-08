from typing import List, Optional, Dict, Set
from pydantic import BaseModel, Field
from datetime import datetime
import enum


class QueryIntent(str, enum.Enum):
    """Types of user query intents"""
    QUERY_ACTIONS = "query_actions"  # "What should I do?"
    QUERY_EVENTS = "query_events"    # "What happened with X?"
    GET_CONTEXT = "get_context"      # "Show me Y project"
    EXPLAIN_ACTION = "explain_action" # "Why do you suggest Z?"
    GENERAL_HELP = "general_help"    # "Help me with..."
    TIMELINE_QUERY = "timeline_query" # "What happened yesterday?"
    SEARCH_CONTENT = "search_content" # "Find information about..."


class TimeReference(BaseModel):
    """Represents temporal context in queries"""
    reference_type: str  # "absolute", "relative", "range"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    relative_expression: Optional[str] = None  # "yesterday", "last week", etc.


class ExtractedEntity(BaseModel):
    """Represents an extracted entity from the query"""
    entity_type: str  # "project", "person", "feature", "platform", etc.
    value: str
    confidence: float = 1.0
    context: Optional[str] = None  # Additional context about the entity


class InformationNeeds(BaseModel):
    """Analyzed information needs from user query"""
    query: str
    user_id: str
    intent: QueryIntent
    intent_confidence: float = Field(ge=0.0, le=1.0)
    
    # Extracted components
    entities: List[ExtractedEntity] = Field(default_factory=list)
    time_reference: Optional[TimeReference] = None
    platforms: Set[str] = Field(default_factory=set)  # slack, github, notion, etc.
    
    # Query characteristics
    complexity: str = "simple"  # simple, moderate, complex
    requires_correlation: bool = False
    requires_explanation: bool = False
    
    # Context requirements
    required_context_types: List[str] = Field(default_factory=list)
    max_results_needed: int = 10
    
    # Additional metadata
    session_context: Dict = Field(default_factory=dict)
    previous_turn_relevant: bool = False
    
    class Config:
        arbitrary_types_allowed = True


class QueryAnalysisResult(BaseModel):
    """Result of query analysis"""
    information_needs: InformationNeeds
    confidence_score: float
    suggested_retrieval_strategies: List[str]
    potential_follow_ups: List[str] = Field(default_factory=list)