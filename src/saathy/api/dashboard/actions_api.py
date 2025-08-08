import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/actions", tags=["actions"])


class ActionAPI:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    async def get_user_actions(
        self,
        user_id: str,
        priority_filter: Optional[list[str]] = None,
        status_filter: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get user's actions with optional filtering"""
        try:
            # Get action IDs from user's queue
            user_queue_key = f"user:{user_id}:actions"

            # Get most recent actions (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).timestamp()
            action_ids = await self.redis.zrangebyscore(
                user_queue_key,
                week_ago,
                datetime.now().timestamp(),
                desc=True,  # Most recent first
                start=0,
                num=limit,
            )

            actions = []
            for action_id in action_ids:
                action_key = f"action:{action_id.decode()}"
                action_data = await self.redis.get(action_key)

                if action_data:
                    action = json.loads(action_data)

                    # Apply filters
                    if (
                        priority_filter
                        and action.get("priority") not in priority_filter
                    ):
                        continue
                    if status_filter and action.get("status") != status_filter:
                        continue

                    # Check if action has expired
                    if action.get("expires_at"):
                        expires_at = datetime.fromisoformat(
                            action["expires_at"].replace("Z", "+00:00")
                        )
                        if expires_at < datetime.now():
                            action["status"] = "expired"

                    actions.append(action)

            return actions

        except Exception as e:
            logger.error(f"Error getting user actions: {e}")
            return []

    async def update_action_status(
        self, user_id: str, action_id: str, status: str, feedback: Optional[str] = None
    ) -> bool:
        """Update action status and optional feedback"""
        try:
            action_key = f"action:{action_id}"
            action_data = await self.redis.get(action_key)

            if not action_data:
                return False

            action = json.loads(action_data)

            # Verify action belongs to user
            if action.get("user_id") != user_id:
                return False

            # Update status
            action["status"] = status
            if status == "completed":
                action["completed_at"] = datetime.now().isoformat()

            if feedback:
                action["user_feedback"] = feedback

            # Save updated action
            await self.redis.setex(action_key, 7 * 24 * 60 * 60, json.dumps(action))

            # Track completion for analytics
            await self.track_action_event(user_id, action_id, status, feedback)

            return True

        except Exception as e:
            logger.error(f"Error updating action status: {e}")
            return False

    async def get_action_details(
        self, user_id: str, action_id: str
    ) -> Optional[dict[str, Any]]:
        """Get detailed information for a single action"""
        try:
            action_key = f"action:{action_id}"
            action_data = await self.redis.get(action_key)

            if not action_data:
                return None

            action = json.loads(action_data)

            # Verify action belongs to user
            if action.get("user_id") != user_id:
                return None

            # Add related context information
            correlation_id = action.get("correlation_id")
            if correlation_id:
                context_key = f"context:{correlation_id}"
                context_data = await self.redis.get(context_key)
                if context_data:
                    context = json.loads(context_data)
                    action["related_context"] = {
                        "synthesized_context": context.get("synthesized_context"),
                        "key_insights": context.get("key_insights"),
                        "platform_data": context.get("platform_data"),
                    }

            return action

        except Exception as e:
            logger.error(f"Error getting action details: {e}")
            return None

    async def track_action_event(
        self,
        user_id: str,
        action_id: str,
        event_type: str,
        metadata: Optional[str] = None,
    ):
        """Track action events for analytics"""
        try:
            event_data = {
                "user_id": user_id,
                "action_id": action_id,
                "event_type": event_type,  # viewed, completed, dismissed, feedback
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata,
            }

            # Store in analytics stream
            analytics_key = "saathy:action_analytics"
            await self.redis.lpush(analytics_key, json.dumps(event_data))

            # Keep only last 10k events
            await self.redis.ltrim(analytics_key, 0, 9999)

        except Exception as e:
            logger.error(f"Error tracking action event: {e}")


# Initialize API instance
action_api = ActionAPI()


@router.get("/")
async def get_actions(
    user_id: str = Query(..., description="User ID"),
    priority: Optional[str] = Query(
        None, description="Priority filter: urgent,high,medium,low,fyi"
    ),
    status: Optional[str] = Query(
        None, description="Status filter: pending,completed,dismissed"
    ),
    limit: int = Query(20, description="Maximum number of actions to return"),
):
    """Get user's action items"""
    try:
        priority_filter = priority.split(",") if priority else None

        actions = await action_api.get_user_actions(
            user_id=user_id,
            priority_filter=priority_filter,
            status_filter=status,
            limit=limit,
        )

        return {
            "actions": actions,
            "total": len(actions),
            "filters_applied": {"priority": priority_filter, "status": status},
        }

    except Exception as e:
        logger.error(f"Error in get_actions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve actions") from e


@router.post("/{action_id}/status")
async def update_action_status(
    action_id: str,
    user_id: str = Query(..., description="User ID"),
    status: str = Query(..., description="New status: completed, dismissed, pending"),
    feedback: Optional[str] = Query(None, description="Optional user feedback"),
):
    """Update action status"""
    try:
        success = await action_api.update_action_status(
            user_id, action_id, status, feedback
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Action not found or unauthorized"
            )

        return {"success": True, "message": f"Action status updated to {status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating action status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update action status") from e


@router.get("/{action_id}")
async def get_action_detail(
    action_id: str, user_id: str = Query(..., description="User ID")
):
    """Get detailed information for a single action"""
    try:
        action = await action_api.get_action_details(user_id, action_id)

        if not action:
            raise HTTPException(status_code=404, detail="Action not found")

        return action

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting action detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve action details") from e


@router.post("/{action_id}/track")
async def track_action_interaction(
    action_id: str,
    user_id: str = Query(..., description="User ID"),
    event_type: str = Query(..., description="Event type: viewed, clicked_link, etc."),
    metadata: Optional[str] = Query(None, description="Additional event metadata"),
):
    """Track user interactions with actions"""
    try:
        await action_api.track_action_event(user_id, action_id, event_type, metadata)
        return {"success": True}

    except Exception as e:
        logger.error(f"Error tracking action interaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to track interaction") from e
