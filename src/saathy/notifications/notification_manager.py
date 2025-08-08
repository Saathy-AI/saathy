import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis

from .channels.email_notifications import EmailNotifier
from .channels.slack_notifications import SlackNotifier
from .intelligence.frequency_controller import FrequencyController
from .intelligence.timing_optimizer import TimingOptimizer

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack_dm"
    BROWSER = "browser"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    IMMEDIATE = "immediate"  # Send right away
    BATCHED = "batched"  # Send in next batch (hourly/daily)
    QUIET = "quiet"  # Dashboard only, no active notification


class NotificationManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.email_notifier = EmailNotifier()
        self.slack_notifier = SlackNotifier()
        self.timing_optimizer = TimingOptimizer()
        self.frequency_controller = FrequencyController(redis_url)

        # Default user preferences
        self.default_preferences = {
            "urgent_actions": [NotificationChannel.SLACK, NotificationChannel.EMAIL],
            "high_actions": [NotificationChannel.SLACK],
            "medium_actions": [NotificationChannel.IN_APP],
            "low_actions": [NotificationChannel.IN_APP],
            "fyi_actions": [NotificationChannel.IN_APP],
            "batch_frequency": "hourly",  # hourly, daily, immediate
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00",
                "timezone": "UTC",
            },
            "max_daily_notifications": 5,
        }

    async def notify_new_action(self, action_data: dict[str, Any]) -> bool:
        """Main entry point for notifying about new actions"""
        try:
            user_id = action_data.get("user_id")
            if not user_id:
                logger.error("No user_id in action data")
                return False

            # Get user preferences
            user_prefs = await self.get_user_preferences(user_id)

            # Determine notification priority and channels
            (
                notification_priority,
                channels,
            ) = await self.determine_notification_strategy(action_data, user_prefs)

            # Check if we should notify now or batch it
            should_notify_now = await self.should_notify_immediately(
                user_id, action_data, notification_priority, user_prefs
            )

            if should_notify_now:
                await self.send_immediate_notifications(
                    action_data, channels, user_prefs
                )
            else:
                await self.queue_for_batch_notification(
                    action_data, channels, user_prefs
                )

            return True

        except Exception as e:
            logger.error(f"Error in notify_new_action: {e}")
            return False

    async def determine_notification_strategy(
        self, action_data: dict[str, Any], user_prefs: dict[str, Any]
    ) -> tuple[NotificationPriority, list[NotificationChannel]]:
        """Determine how urgently and through which channels to notify"""

        action_priority = action_data.get("priority", "medium")
        action_type = action_data.get("action_type", "update")
        urgency_score = action_data.get("urgency_score", 0.0)

        # Map action priority to notification channels
        channels = user_prefs.get(
            f"{action_priority}_actions", [NotificationChannel.IN_APP]
        )

        # Determine notification priority
        if action_priority == "urgent" or urgency_score > 0.7:
            notification_priority = NotificationPriority.IMMEDIATE
        elif action_priority == "high" or urgency_score > 0.5:
            notification_priority = NotificationPriority.IMMEDIATE
        elif action_priority == "medium":
            notification_priority = NotificationPriority.BATCHED
        else:
            notification_priority = NotificationPriority.QUIET

        # Special cases that increase urgency
        mentioned_users = action_data.get("mentioned_users", [])
        if action_data.get("user_id") in mentioned_users:
            notification_priority = NotificationPriority.IMMEDIATE

        # Time-sensitive action types
        time_sensitive_types = ["review", "respond", "meeting"]
        if action_type in time_sensitive_types:
            if notification_priority == NotificationPriority.QUIET:
                notification_priority = NotificationPriority.BATCHED

        return notification_priority, channels

    async def should_notify_immediately(
        self,
        user_id: str,
        action_data: dict[str, Any],
        notification_priority: NotificationPriority,
        user_prefs: dict[str, Any],
    ) -> bool:
        """Decide if we should notify immediately or wait for batch"""

        if notification_priority == NotificationPriority.QUIET:
            return False

        if notification_priority == NotificationPriority.IMMEDIATE:
            # Check frequency limits
            if not await self.frequency_controller.can_send_notification(user_id):
                logger.info(
                    f"Frequency limit reached for user {user_id}, batching instead"
                )
                return False

            # Check quiet hours
            if await self.timing_optimizer.is_quiet_hours(user_prefs):
                logger.info(f"Quiet hours for user {user_id}, batching instead")
                return False

            return True

        # BATCHED priority - check if it's a good time for batch
        return await self.timing_optimizer.is_good_time_for_batch(user_id, user_prefs)

    async def send_immediate_notifications(
        self,
        action_data: dict[str, Any],
        channels: list[NotificationChannel],
        user_prefs: dict[str, Any],
    ):
        """Send notifications immediately through specified channels"""

        user_id = action_data["user_id"]

        # Prepare notification content
        notification_content = await self.prepare_notification_content(action_data)

        # Send through each channel
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    await self.email_notifier.send_action_notification(
                        user_id, action_data, notification_content
                    )
                elif channel == NotificationChannel.SLACK:
                    await self.slack_notifier.send_dm_notification(
                        user_id, action_data, notification_content
                    )
                elif channel == NotificationChannel.BROWSER:
                    # Browser notifications would need WebSocket or push service
                    await self.send_browser_notification(user_id, notification_content)

                # Track notification sent
                await self.track_notification_sent(
                    user_id, action_data["action_id"], channel.value
                )

            except Exception as e:
                logger.error(
                    f"Failed to send {channel.value} notification to {user_id}: {e}"
                )

    async def queue_for_batch_notification(
        self,
        action_data: dict[str, Any],
        channels: list[NotificationChannel],
        user_prefs: dict[str, Any],
    ):
        """Queue action for batch notification"""
        try:
            user_id = action_data["user_id"]
            batch_key = f"notification_batch:{user_id}"

            batch_item = {
                "action_data": action_data,
                "channels": [c.value for c in channels],
                "queued_at": datetime.now().isoformat(),
            }

            await self.redis.lpush(batch_key, json.dumps(batch_item))

            # Set expiration for batch (24 hours)
            await self.redis.expire(batch_key, 24 * 60 * 60)

            logger.info(
                f"Queued action {action_data['action_id']} for batch notification"
            )

        except Exception as e:
            logger.error(f"Error queuing batch notification: {e}")

    async def prepare_notification_content(
        self, action_data: dict[str, Any]
    ) -> dict[str, str]:
        """Prepare notification content for different channels"""

        title = action_data.get("title", "New Action Available")
        description = action_data.get("description", "")
        priority = action_data.get("priority", "medium")
        estimated_time = action_data.get("estimated_time_minutes", 15)

        # Create different versions for different channels
        content = {
            "subject": f"⚡ Action: {title}",
            "short_text": f"{title} (~{estimated_time} min)",
            "full_text": f"{title}\n\n{description}\n\nEstimated time: {estimated_time} minutes\nPriority: {priority.title()}",
            "action_links": action_data.get("action_links", []),
        }

        return content

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user notification preferences"""
        try:
            prefs_key = f"user:{user_id}:notification_preferences"
            prefs_data = await self.redis.get(prefs_key)

            if prefs_data:
                user_prefs = json.loads(prefs_data)
                # Merge with defaults for any missing keys
                return {**self.default_preferences, **user_prefs}

            return self.default_preferences

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return self.default_preferences

    async def update_user_preferences(
        self, user_id: str, preferences: dict[str, Any]
    ) -> bool:
        """Update user notification preferences"""
        try:
            prefs_key = f"user:{user_id}:notification_preferences"
            await self.redis.setex(
                prefs_key, 30 * 24 * 60 * 60, json.dumps(preferences)
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False

    async def track_notification_sent(self, user_id: str, action_id: str, channel: str):
        """Track notification delivery for analytics"""
        try:
            event_data = {
                "user_id": user_id,
                "action_id": action_id,
                "channel": channel,
                "sent_at": datetime.now().isoformat(),
                "event_type": "notification_sent",
            }

            analytics_key = "saathy:notification_analytics"
            await self.redis.lpush(analytics_key, json.dumps(event_data))

        except Exception as e:
            logger.error(f"Error tracking notification: {e}")

    async def send_browser_notification(self, user_id: str, content: dict[str, str]):
        """Send browser/push notification (placeholder for now)"""
        # This would integrate with a push notification service
        # For now, we'll just log it
        logger.info(
            f"Would send browser notification to {user_id}: {content['short_text']}"
        )

    async def process_batch_notifications(self):
        """Background task to process batched notifications"""
        while True:
            try:
                # Find users with pending batch notifications
                pattern = "notification_batch:*"
                batch_keys = []
                async for key in self.redis.scan_iter(match=pattern):
                    batch_keys.append(key.decode())

                for batch_key in batch_keys:
                    user_id = batch_key.split(":")[1]
                    await self.process_user_batch_notifications(user_id)

                # Wait before next batch processing cycle
                await asyncio.sleep(3600)  # Process batches every hour

            except Exception as e:
                logger.error(f"Error in batch notification processing: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

    async def process_user_batch_notifications(self, user_id: str):
        """Process batch notifications for a specific user"""
        try:
            batch_key = f"notification_batch:{user_id}"

            # Get all queued notifications
            batch_items = []
            while True:
                item_data = await self.redis.rpop(batch_key)
                if not item_data:
                    break
                batch_items.append(json.loads(item_data))

            if not batch_items:
                return

            logger.info(
                f"Processing {len(batch_items)} batch notifications for user {user_id}"
            )

            # Group by channels
            channel_groups = {}
            for item in batch_items:
                for channel in item["channels"]:
                    if channel not in channel_groups:
                        channel_groups[channel] = []
                    channel_groups[channel].append(item["action_data"])

            # Send batch notifications for each channel
            for channel, actions in channel_groups.items():
                if channel == NotificationChannel.EMAIL.value:
                    await self.email_notifier.send_batch_notification(user_id, actions)
                elif channel == NotificationChannel.SLACK.value:
                    await self.slack_notifier.send_batch_dm(user_id, actions)

        except Exception as e:
            logger.error(
                f"Error processing batch notifications for user {user_id}: {e}"
            )
