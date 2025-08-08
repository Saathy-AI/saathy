from datetime import datetime, timedelta
from typing import Dict, Any
import redis.asyncio as redis
import json
import logging

logger = logging.getLogger(__name__)

class FrequencyController:
    """Control notification frequency to prevent fatigue"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        
    async def can_send_notification(self, user_id: str) -> bool:
        """Check if we can send a notification to the user based on frequency limits"""
        try:
            # Get user's notification history
            today_key = f"notifications:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
            notification_count = await self.redis.get(today_key)
            
            if notification_count is None:
                notification_count = 0
            else:
                notification_count = int(notification_count)
            
            # Get user's max daily limit (default to 5)
            user_prefs = await self._get_user_preferences(user_id)
            max_daily = user_prefs.get('max_daily_notifications', 5)
            
            # Check if under limit
            if notification_count >= max_daily:
                logger.info(f"User {user_id} has reached daily notification limit ({max_daily})")
                return False
            
            # Check rate limiting (no more than 1 notification per 15 minutes)
            last_notification_key = f"last_notification:{user_id}"
            last_notification = await self.redis.get(last_notification_key)
            
            if last_notification:
                last_time = datetime.fromisoformat(last_notification.decode())
                time_since_last = datetime.now() - last_time
                
                if time_since_last < timedelta(minutes=15):
                    logger.info(f"Rate limiting user {user_id}, last notification was {time_since_last.seconds/60:.1f} minutes ago")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification frequency: {e}")
            # Default to allowing notification on error
            return True
    
    async def record_notification_sent(self, user_id: str):
        """Record that a notification was sent to update frequency tracking"""
        try:
            # Increment daily count
            today_key = f"notifications:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
            await self.redis.incr(today_key)
            await self.redis.expire(today_key, 86400)  # Expire after 24 hours
            
            # Update last notification time
            last_notification_key = f"last_notification:{user_id}"
            await self.redis.setex(
                last_notification_key, 
                86400,  # Expire after 24 hours
                datetime.now().isoformat()
            )
            
            logger.debug(f"Recorded notification sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error recording notification: {e}")
    
    async def get_user_notification_stats(self, user_id: str) -> Dict[str, Any]:
        """Get notification statistics for a user"""
        try:
            stats = {
                'today_count': 0,
                'weekly_count': 0,
                'last_notification': None,
                'daily_limit': 5
            }
            
            # Get today's count
            today_key = f"notifications:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
            today_count = await self.redis.get(today_key)
            if today_count:
                stats['today_count'] = int(today_count)
            
            # Get weekly count
            weekly_count = 0
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                day_key = f"notifications:{user_id}:{date}"
                day_count = await self.redis.get(day_key)
                if day_count:
                    weekly_count += int(day_count)
            stats['weekly_count'] = weekly_count
            
            # Get last notification time
            last_notification_key = f"last_notification:{user_id}"
            last_notification = await self.redis.get(last_notification_key)
            if last_notification:
                stats['last_notification'] = datetime.fromisoformat(last_notification.decode())
            
            # Get user's limit
            user_prefs = await self._get_user_preferences(user_id)
            stats['daily_limit'] = user_prefs.get('max_daily_notifications', 5)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {}
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user notification preferences"""
        try:
            prefs_key = f"user:{user_id}:notification_preferences"
            prefs_data = await self.redis.get(prefs_key)
            
            if prefs_data:
                return json.loads(prefs_data)
            
            # Return defaults
            return {
                'max_daily_notifications': 5,
                'batch_frequency': 'hourly'
            }
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {'max_daily_notifications': 5}
    
    async def reset_user_limits(self, user_id: str):
        """Reset notification limits for a user (for testing or manual override)"""
        try:
            today_key = f"notifications:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
            await self.redis.delete(today_key)
            
            last_notification_key = f"last_notification:{user_id}"
            await self.redis.delete(last_notification_key)
            
            logger.info(f"Reset notification limits for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error resetting limits: {e}")
    
    async def adjust_user_frequency(self, user_id: str, feedback: str):
        """Adjust notification frequency based on user feedback"""
        # This would implement learning from user feedback
        # For example, if user marks notifications as "too frequent"
        # we could reduce their daily limit
        pass