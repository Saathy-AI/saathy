"""AI Intelligence endpoints for proactive action generation."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..dependencies import (
    IntelligenceDep,
    VectorStoreDep,
    ConnectorManagerDep,
    SettingsDep,
)

router = APIRouter()


class ActionRecommendation(BaseModel):
    """AI-generated action recommendation."""
    id: str
    user_id: str
    title: str
    description: str
    priority: str = Field(..., regex="^(high|medium|low)$")
    action_type: str
    platform_links: Dict[str, str] = Field(default_factory=dict)
    correlated_events: List[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
    feedback: Optional[str] = None


class EventCorrelation(BaseModel):
    """Correlation between events across platforms."""
    id: str
    event_ids: List[str]
    correlation_score: float = Field(..., ge=0.0, le=1.0)
    correlation_type: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlatformEvent(BaseModel):
    """Event from a platform."""
    id: str
    platform: str
    event_type: str
    content: str
    user_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionFeedback(BaseModel):
    """Feedback for an action recommendation."""
    useful: bool
    feedback_text: Optional[str] = None
    completed: bool = False


@router.get("/actions/user/{user_id}", response_model=List[ActionRecommendation])
async def get_user_actions(
    user_id: str,
    intelligence_service: IntelligenceDep,
    limit: int = Query(10, ge=1, le=50),
    include_completed: bool = Query(False),
    priority: Optional[str] = Query(None, regex="^(high|medium|low)$"),
) -> List[ActionRecommendation]:
    """
    Get proactive action recommendations for a user.
    
    Returns AI-generated actionable recommendations based on the user's
    recent activity across all connected platforms.
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service not available"
        )
    
    try:
        # Get user's recent actions
        actions = await intelligence_service.get_user_actions(
            user_id=user_id,
            limit=limit,
            include_completed=include_completed,
            priority=priority,
        )
        
        # Convert to response model
        return [
            ActionRecommendation(
                id=action["id"],
                user_id=action["user_id"],
                title=action["title"],
                description=action["description"],
                priority=action["priority"],
                action_type=action["action_type"],
                platform_links=action.get("platform_links", {}),
                correlated_events=action.get("correlated_events", []),
                created_at=action["created_at"],
                completed_at=action.get("completed_at"),
                feedback=action.get("feedback"),
            )
            for action in actions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user actions: {str(e)}"
        )


@router.post("/actions/{action_id}/complete", response_model=Dict[str, str])
async def complete_action(
    action_id: str,
    intelligence_service: IntelligenceDep,
) -> Dict[str, str]:
    """Mark an action recommendation as completed."""
    if not intelligence_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service not available"
        )
    
    try:
        success = await intelligence_service.mark_action_completed(action_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Action {action_id} not found"
            )
        
        return {
            "status": "success",
            "message": f"Action {action_id} marked as completed",
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete action: {str(e)}"
        )


@router.post("/actions/{action_id}/feedback", response_model=Dict[str, str])
async def provide_action_feedback(
    action_id: str,
    feedback: ActionFeedback,
    intelligence_service: IntelligenceDep,
) -> Dict[str, str]:
    """Provide feedback on an action recommendation's usefulness."""
    if not intelligence_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service not available"
        )
    
    try:
        success = await intelligence_service.add_action_feedback(
            action_id=action_id,
            useful=feedback.useful,
            feedback_text=feedback.feedback_text,
            completed=feedback.completed,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Action {action_id} not found"
            )
        
        return {
            "status": "success",
            "message": "Feedback recorded",
            "action_id": action_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record feedback: {str(e)}"
        )


@router.get("/correlations/user/{user_id}", response_model=List[EventCorrelation])
async def get_user_correlations(
    user_id: str,
    intelligence_service: IntelligenceDep,
    hours: int = Query(24, ge=1, le=168),  # Default 24 hours, max 1 week
    min_score: float = Query(0.7, ge=0.0, le=1.0),
) -> List[EventCorrelation]:
    """
    Get event correlations for a user.
    
    Returns correlations between events across different platforms,
    helping to identify related activities and context.
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service not available"
        )
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        correlations = await intelligence_service.get_event_correlations(
            user_id=user_id,
            since=since,
            min_score=min_score,
        )
        
        return [
            EventCorrelation(
                id=corr["id"],
                event_ids=corr["event_ids"],
                correlation_score=corr["correlation_score"],
                correlation_type=corr["correlation_type"],
                timestamp=corr["timestamp"],
                metadata=corr.get("metadata", {}),
            )
            for corr in correlations
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get correlations: {str(e)}"
        )


@router.get("/events/user/{user_id}", response_model=List[PlatformEvent])
async def get_user_events(
    user_id: str,
    intelligence_service: IntelligenceDep,
    hours: int = Query(24, ge=1, le=168),  # Default 24 hours, max 1 week
    platform: Optional[str] = Query(None, regex="^(github|slack|notion)$"),
    event_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
) -> List[PlatformEvent]:
    """
    Get recent events for a user across platforms.
    
    Returns a timeline of user events from all connected platforms,
    useful for understanding user activity and context.
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service not available"
        )
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        events = await intelligence_service.get_user_events(
            user_id=user_id,
            since=since,
            platform=platform,
            event_type=event_type,
            limit=limit,
        )
        
        return [
            PlatformEvent(
                id=event["id"],
                platform=event["platform"],
                event_type=event["event_type"],
                content=event["content"],
                user_id=event["user_id"],
                timestamp=event["timestamp"],
                metadata=event.get("metadata", {}),
            )
            for event in events
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}"
        )


@router.post("/events/analyze", response_model=Dict[str, Any])
async def analyze_events(
    user_id: str = Query(..., description="User ID to analyze"),
    hours: int = Query(24, ge=1, le=168),
    intelligence_service: IntelligenceDep = None,
) -> Dict[str, Any]:
    """
    Analyze user events and generate insights.
    
    Performs deep analysis on user events to identify patterns,
    suggest actions, and provide insights.
    """
    if not intelligence_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service not available"
        )
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        analysis = await intelligence_service.analyze_user_activity(
            user_id=user_id,
            since=since,
        )
        
        return {
            "user_id": user_id,
            "analysis_period": {
                "start": since.isoformat(),
                "end": datetime.utcnow().isoformat(),
                "hours": hours,
            },
            "insights": analysis.get("insights", []),
            "patterns": analysis.get("patterns", []),
            "recommendations": analysis.get("recommendations", []),
            "statistics": analysis.get("statistics", {}),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze events: {str(e)}"
        )