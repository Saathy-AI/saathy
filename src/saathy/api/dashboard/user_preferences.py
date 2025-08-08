import json
import logging
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class UserPreferencesAPI:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

        # Default preferences template
        self.default_preferences = {
            "notifications": {
                "urgent_actions": ["slack_dm", "email"],
                "high_actions": ["slack_dm"],
                "medium_actions": ["in_app"],
                "low_actions": ["in_app"],
                "fyi_actions": ["in_app"],
                "batch_frequency": "hourly",  # hourly, daily, immediate
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "08:00",
                    "timezone": "UTC",
                },
                "max_daily_notifications": 5,
            },
            "dashboard": {
                "default_view": "priority",  # priority, timeline, type
                "items_per_page": 20,
                "auto_refresh": True,
                "refresh_interval_seconds": 30,
            },
            "integrations": {
                "slack": {"enabled": True, "dm_enabled": True},
                "email": {"enabled": True, "address": None},
                "browser": {"enabled": False},
            },
        }

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user preferences, returning defaults if not set"""
        try:
            prefs_key = f"user:{user_id}:preferences"
            prefs_data = await self.redis.get(prefs_key)

            if prefs_data:
                user_prefs = json.loads(prefs_data)
                # Merge with defaults to ensure all keys exist
                return self._merge_preferences(self.default_preferences, user_prefs)

            return self.default_preferences

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return self.default_preferences

    async def update_user_preferences(
        self, user_id: str, preferences: dict[str, Any]
    ) -> bool:
        """Update user preferences"""
        try:
            # Validate preferences structure
            if not self._validate_preferences(preferences):
                return False

            prefs_key = f"user:{user_id}:preferences"

            # Get existing preferences
            existing_prefs = await self.get_user_preferences(user_id)

            # Merge with existing (deep merge)
            updated_prefs = self._merge_preferences(existing_prefs, preferences)

            # Save to Redis
            await self.redis.setex(
                prefs_key, 30 * 24 * 60 * 60, json.dumps(updated_prefs)
            )

            logger.info(f"Updated preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False

    def _merge_preferences(self, base: dict, updates: dict) -> dict:
        """Deep merge preferences dictionaries"""
        result = base.copy()

        for key, value in updates.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_preferences(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_preferences(self, preferences: dict[str, Any]) -> bool:
        """Validate preferences structure"""
        # Basic validation - can be expanded
        valid_channels = ["slack_dm", "email", "browser", "in_app"]
        valid_frequencies = ["immediate", "hourly", "daily"]
        valid_views = ["priority", "timeline", "type"]

        if "notifications" in preferences:
            notif = preferences["notifications"]

            # Check action notification channels
            for action_type in [
                "urgent_actions",
                "high_actions",
                "medium_actions",
                "low_actions",
                "fyi_actions",
            ]:
                if action_type in notif:
                    if not isinstance(notif[action_type], list):
                        return False
                    for channel in notif[action_type]:
                        if channel not in valid_channels:
                            return False

            # Check batch frequency
            if (
                "batch_frequency" in notif
                and notif["batch_frequency"] not in valid_frequencies
            ):
                return False

            # Check max daily notifications
            if "max_daily_notifications" in notif:
                if (
                    not isinstance(notif["max_daily_notifications"], int)
                    or notif["max_daily_notifications"] < 0
                ):
                    return False

        if "dashboard" in preferences:
            dash = preferences["dashboard"]

            if "default_view" in dash and dash["default_view"] not in valid_views:
                return False

            if "items_per_page" in dash:
                if (
                    not isinstance(dash["items_per_page"], int)
                    or dash["items_per_page"] < 1
                ):
                    return False

        return True


# Initialize API instance
preferences_api = UserPreferencesAPI()


@router.get("/{user_id}")
async def get_preferences(user_id: str):
    """Get user preferences"""
    try:
        preferences = await preferences_api.get_user_preferences(user_id)
        return preferences

    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve preferences"
        ) from e


@router.put("/{user_id}")
async def update_preferences(user_id: str, preferences: dict[str, Any]):
    """Update user preferences"""
    try:
        success = await preferences_api.update_user_preferences(user_id, preferences)

        if not success:
            raise HTTPException(status_code=400, detail="Invalid preferences format")

        return {"success": True, "message": "Preferences updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update preferences"
        ) from e


@router.post("/{user_id}/reset")
async def reset_preferences(user_id: str):
    """Reset user preferences to defaults"""
    try:
        prefs_key = f"user:{user_id}:preferences"
        await preferences_api.redis.delete(prefs_key)

        return {"success": True, "message": "Preferences reset to defaults"}

    except Exception as e:
        logger.error(f"Error resetting preferences: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to reset preferences"
        ) from e
