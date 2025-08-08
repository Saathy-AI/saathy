import logging
from datetime import datetime, time, timedelta
from typing import Any

import pytz

logger = logging.getLogger(__name__)


class TimingOptimizer:
    """Optimize notification timing based on user preferences and patterns"""

    def __init__(self):
        # Default optimal notification times
        self.optimal_hours = {
            "morning": (9, 10),  # 9am - 10am
            "midday": (12, 13),  # 12pm - 1pm
            "afternoon": (15, 16),  # 3pm - 4pm
            "evening": (17, 18),  # 5pm - 6pm
        }

    async def is_quiet_hours(self, user_prefs: dict[str, Any]) -> bool:
        """Check if current time is within user's quiet hours"""
        try:
            quiet_hours = user_prefs.get("quiet_hours", {})
            if not quiet_hours.get("enabled", True):
                return False

            # Get user's timezone
            timezone_str = quiet_hours.get("timezone", "UTC")
            user_tz = pytz.timezone(timezone_str)

            # Get current time in user's timezone
            now = datetime.now(user_tz)

            # Parse quiet hours
            start_str = quiet_hours.get("start", "22:00")
            end_str = quiet_hours.get("end", "08:00")

            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))

            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)

            current_time = now.time()

            # Handle overnight quiet hours
            if start_time > end_time:
                # Quiet hours span midnight
                return current_time >= start_time or current_time <= end_time
            else:
                # Normal quiet hours
                return start_time <= current_time <= end_time

        except Exception as e:
            logger.error(f"Error checking quiet hours: {e}")
            # Default to not quiet hours on error
            return False

    async def is_good_time_for_batch(
        self, user_id: str, user_prefs: dict[str, Any]
    ) -> bool:
        """Check if it's a good time to send batch notifications"""
        try:
            # Check if in quiet hours
            if await self.is_quiet_hours(user_prefs):
                return False

            # Get user's timezone
            timezone_str = user_prefs.get("quiet_hours", {}).get("timezone", "UTC")
            user_tz = pytz.timezone(timezone_str)
            now = datetime.now(user_tz)

            # Check if current hour is in optimal hours
            current_hour = now.hour

            for _period, (start, end) in self.optimal_hours.items():
                if start <= current_hour < end:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking batch timing: {e}")
            return False

    async def get_next_batch_time(self, user_prefs: dict[str, Any]) -> datetime:
        """Get the next optimal time for batch notifications"""
        try:
            # Get user's timezone
            timezone_str = user_prefs.get("quiet_hours", {}).get("timezone", "UTC")
            user_tz = pytz.timezone(timezone_str)
            now = datetime.now(user_tz)

            # Get batch frequency preference
            batch_frequency = user_prefs.get("batch_frequency", "daily")

            if batch_frequency == "immediate":
                return now

            # Find next optimal hour
            next_time = None
            current_hour = now.hour

            # Check today's remaining optimal hours
            for _period, (start, _end) in self.optimal_hours.items():
                if start > current_hour:
                    next_time = now.replace(
                        hour=start, minute=0, second=0, microsecond=0
                    )
                    break

            # If no optimal hours left today, use tomorrow's first optimal hour
            if not next_time:
                tomorrow = now + timedelta(days=1)
                first_optimal_hour = min(h[0] for h in self.optimal_hours.values())
                next_time = tomorrow.replace(
                    hour=first_optimal_hour, minute=0, second=0, microsecond=0
                )

            # Check if next time falls in quiet hours
            quiet_hours = user_prefs.get("quiet_hours", {})
            if quiet_hours.get("enabled", True):
                start_str = quiet_hours.get("start", "22:00")
                end_str = quiet_hours.get("end", "08:00")

                start_hour = int(start_str.split(":")[0])
                end_hour = int(end_str.split(":")[0])

                # If next time is in quiet hours, push to end of quiet hours
                if self._is_in_quiet_range(next_time.hour, start_hour, end_hour):
                    next_time = next_time.replace(hour=end_hour, minute=0)

            return next_time

        except Exception as e:
            logger.error(f"Error calculating next batch time: {e}")
            # Default to 1 hour from now
            return datetime.now() + timedelta(hours=1)

    def _is_in_quiet_range(self, hour: int, start: int, end: int) -> bool:
        """Check if hour is in quiet hours range"""
        if start > end:  # Overnight range
            return hour >= start or hour < end
        else:
            return start <= hour < end

    async def learn_user_patterns(
        self, user_id: str, interaction_history: list[dict[str, Any]]
    ):
        """Learn from user interaction patterns to optimize timing"""
        # This would analyze when users typically interact with notifications
        # and adjust optimal_hours accordingly
        # For V1, we'll use default optimal hours
        pass
