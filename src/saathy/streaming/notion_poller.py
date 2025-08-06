"""Notion polling service for detecting page and database changes."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from notion_client import AsyncClient

from .event_manager import EventManager
from .models.events import EventType, NotionEvent

logger = logging.getLogger(__name__)


class NotionPollingService:
    """Polls Notion for changes and converts them to standardized events."""

    def __init__(
        self, notion_token: str, event_manager: EventManager, poll_interval: int = 300
    ):
        """Initialize Notion polling service."""
        self.notion_token = notion_token
        self.event_manager = event_manager
        self.client = AsyncClient(auth=notion_token)
        self.polling_interval = poll_interval  # seconds

        # Track known pages and their last edit times
        self.known_pages: set[str] = set()
        self.page_versions: dict[str, str] = {}  # page_id -> last_edited_time
        self.database_cache: dict[str, dict[str, Any]] = {}

        # Polling state
        self.last_check = datetime.now() - timedelta(minutes=10)  # Start 10 mins ago
        self.is_running = False

        # User mapping cache (Notion IDs to user names)
        self.user_cache: dict[str, str] = {}

    async def start_polling(self):
        """Start the polling loop."""
        self.is_running = True
        logger.info(
            f"Starting Notion polling service (interval: {self.polling_interval}s)..."
        )

        try:
            # Initialize cache
            await self.initialize_caches()

            while self.is_running:
                try:
                    await self.poll_changes()
                    await asyncio.sleep(self.polling_interval)
                except Exception as e:
                    logger.error(f"Error in Notion polling: {e}")
                    await asyncio.sleep(30)  # Short delay before retry

        except Exception as e:
            logger.error(f"Fatal error in Notion polling service: {e}")
        finally:
            logger.info("Notion polling service stopped")

    async def stop_polling(self):
        """Stop the polling service."""
        self.is_running = False
        logger.info("Stopping Notion polling service...")

    async def initialize_caches(self):
        """Initialize caches with current state."""
        try:
            # Get all accessible databases
            databases = await self.get_databases()
            logger.info(f"Found {len(databases)} accessible databases")

            # Initialize page cache with recent pages
            for database_id in databases:
                await self.cache_database_pages(database_id)

            # Cache user information
            await self.cache_users()

            logger.info(f"Initialized cache with {len(self.known_pages)} pages")

        except Exception as e:
            logger.error(f"Error initializing Notion caches: {e}")

    async def poll_changes(self):
        """Poll for changes in Notion workspaces."""
        try:
            current_time = datetime.now()
            logger.debug(f"Polling Notion changes since {self.last_check}")

            # Get all databases
            databases = await self.get_databases()

            # Check each database for changes
            for database_id in databases:
                await self.check_database_changes(database_id)

            # Also search for recently modified pages globally
            await self.search_recent_pages()

            # Update last check time
            self.last_check = current_time

        except Exception as e:
            logger.error(f"Error polling Notion changes: {e}")

    async def get_databases(self) -> list[str]:
        """Get list of accessible databases."""
        try:
            database_ids = []

            # Search for databases
            response = await self.client.search(
                filter={"property": "object", "value": "database"}, page_size=100
            )

            for result in response.get("results", []):
                if result.get("object") == "database":
                    database_id = result["id"]
                    database_ids.append(database_id)

                    # Cache database info
                    self.database_cache[database_id] = {
                        "title": self.extract_title(result),
                        "last_edited_time": result.get("last_edited_time"),
                    }

            return database_ids

        except Exception as e:
            logger.error(f"Error getting Notion databases: {e}")
            return []

    async def cache_database_pages(self, database_id: str):
        """Cache pages from a database to initialize state."""
        try:
            # Get recent pages from this database
            response = await self.client.databases.query(
                database_id=database_id,
                page_size=50,  # Limit initial cache size
                sorts=[{"property": "last_edited_time", "direction": "descending"}],
            )

            for page in response.get("results", []):
                page_id = page["id"]
                last_edited_time = page.get("last_edited_time")

                self.known_pages.add(page_id)
                if last_edited_time:
                    self.page_versions[page_id] = last_edited_time

        except Exception as e:
            logger.error(f"Error caching database pages for {database_id}: {e}")

    async def cache_users(self):
        """Cache user information for user ID to name mapping."""
        try:
            response = await self.client.users.list()

            for user in response.get("results", []):
                user_id = user.get("id", "")
                user_name = ""

                if user.get("type") == "person":
                    user_name = user.get("name", "")
                    if not user_name and "person" in user:
                        user_name = user["person"].get("email", "")
                elif user.get("type") == "bot":
                    user_name = user.get("name", "Bot")

                if user_id and user_name:
                    self.user_cache[user_id] = user_name

            logger.debug(f"Cached {len(self.user_cache)} Notion users")

        except Exception as e:
            logger.error(f"Error caching Notion users: {e}")

    async def check_database_changes(self, database_id: str):
        """Check for changes in a specific database."""
        try:
            # Query for pages modified since last check
            response = await self.client.databases.query(
                database_id=database_id,
                filter={
                    "property": "last_edited_time",
                    "date": {"after": self.last_check.isoformat()},
                }
                if hasattr(self, "last_check")
                else None,
                sorts=[{"property": "last_edited_time", "direction": "descending"}],
                page_size=50,
            )

            for page in response.get("results", []):
                await self.process_page_change(page, database_id)

        except Exception as e:
            logger.error(f"Error checking database {database_id}: {e}")

    async def search_recent_pages(self):
        """Search for recently modified pages globally."""
        try:
            # Search for pages modified recently
            response = await self.client.search(
                filter={"property": "object", "value": "page"},
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=20,  # Limit to most recent
            )

            for page in response.get("results", []):
                # Only process if it's newer than our last check
                last_edited = page.get("last_edited_time")
                if last_edited:
                    page_time = datetime.fromisoformat(
                        last_edited.replace("Z", "+00:00")
                    )
                    if page_time > self.last_check:
                        await self.process_page_change(page, None)

        except Exception as e:
            logger.error(f"Error searching recent pages: {e}")

    async def process_page_change(
        self, page_data: dict[str, Any], database_id: Optional[str]
    ):
        """Process a changed page and create event if significant."""
        try:
            page_id = page_data["id"]
            last_edited_time = page_data.get("last_edited_time")

            if not last_edited_time:
                return

            # Determine if this is a new page or update
            is_new_page = page_id not in self.known_pages
            is_updated = (
                not is_new_page and self.page_versions.get(page_id) != last_edited_time
            )

            if not (is_new_page or is_updated):
                return

            # Get detailed page information
            try:
                page_details = await self.client.pages.retrieve(page_id)
            except Exception as e:
                logger.warning(f"Could not retrieve page details for {page_id}: {e}")
                page_details = page_data

            page_title = self.extract_page_title(page_details)

            # Detect what properties changed (simplified)
            properties_changed = self.detect_property_changes(
                page_id, page_details, is_new_page
            )

            # Skip if this looks like an automatic update (no significant changes)
            if not is_new_page and not properties_changed:
                logger.debug(
                    f"Skipping page {page_id} - no significant changes detected"
                )
                return

            # Determine change type
            change_type = "created" if is_new_page else "updated"

            # Extract context and keywords
            keywords = self.extract_notion_keywords(
                page_title, page_details, properties_changed
            )
            project_context = self.infer_project_from_page(
                page_title, page_details, database_id
            )

            # Get the user who made the change
            last_edited_by = page_details.get("last_edited_by", {})
            user_id = last_edited_by.get("id", "unknown")
            user_name = self.user_cache.get(user_id, user_id)

            # Generate page URL
            page_url = f"https://notion.so/{page_id.replace('-', '')}"

            # Calculate urgency
            urgency_score = self.calculate_notion_urgency(
                page_title, properties_changed, keywords, is_new_page
            )

            notion_event = NotionEvent(
                event_id=f"notion_{page_id}_{last_edited_time.replace(':', '_').replace('-', '_')}",
                event_type=EventType.NOTION_PAGE_UPDATE,
                timestamp=datetime.fromisoformat(
                    last_edited_time.replace("Z", "+00:00")
                ),
                user_id=user_name,  # Use readable name instead of ID
                platform="notion",
                raw_data=page_details,
                mentioned_users=[],  # Notion doesn't have @ mentions like Slack
                keywords=keywords,
                project_context=project_context,
                urgency_score=urgency_score,
                page_id=page_id,
                page_title=page_title,
                database_id=database_id,
                change_type=change_type,
                properties_changed=properties_changed,
                page_url=page_url,
            )

            # Update tracking
            self.known_pages.add(page_id)
            self.page_versions[page_id] = last_edited_time

            # Send to event manager
            await self.event_manager.process_event(notion_event)

            logger.debug(f"Processed Notion {change_type} event for page: {page_title}")

        except Exception as e:
            logger.error(f"Error processing Notion page change: {e}")

    def extract_title(self, data: dict[str, Any]) -> str:
        """Extract title from any Notion object."""
        # Try different title property formats
        title_properties = data.get("properties", {})

        for _, prop_data in title_properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    return title_array[0].get("text", {}).get("content", "Untitled")

        # Fallback to object title
        if "title" in data:
            title_array = data["title"]
            if title_array:
                return title_array[0].get("text", {}).get("content", "Untitled")

        return "Untitled"

    def extract_page_title(self, page_data: dict[str, Any]) -> str:
        """Extract page title from Notion page data."""
        return self.extract_title(page_data)

    def detect_property_changes(
        self, page_id: str, page_data: dict[str, Any], is_new: bool
    ) -> list[str]:
        """Detect which properties changed (simplified implementation)."""
        if is_new:
            return ["created"]

        # This is a simplified implementation
        # In a full implementation, you'd store previous page states and compare
        changed_props = []

        properties = page_data.get("properties", {})

        # Look for properties that commonly indicate real changes
        significant_props = [
            "Status",
            "Assignee",
            "Priority",
            "Due Date",
            "Tags",
            "Project",
        ]

        for prop_name, _ in properties.items():
            if any(
                sig_prop.lower() in prop_name.lower() for sig_prop in significant_props
            ):
                changed_props.append(prop_name)

        # If no significant properties, assume content was changed
        if not changed_props:
            changed_props = ["content"]

        return changed_props[:5]  # Limit to avoid noise

    def extract_notion_keywords(
        self, title: str, page_data: dict[str, Any], changes: list[str]
    ) -> list[str]:
        """Extract keywords from Notion page."""
        keywords = []
        title_lower = title.lower()

        # Common project/work keywords
        notion_keywords = [
            "project",
            "task",
            "bug",
            "feature",
            "meeting",
            "notes",
            "spec",
            "design",
            "deadline",
            "milestone",
            "release",
            "sprint",
            "epic",
            "todo",
            "done",
            "review",
            "feedback",
            "documentation",
            "docs",
            "requirements",
        ]

        for keyword in notion_keywords:
            if keyword in title_lower:
                keywords.append(keyword)

        # Add change types as keywords
        keywords.extend(changes)

        # Check properties for status/priority indicators
        properties = page_data.get("properties", {})
        for prop_name, prop_data in properties.items():
            prop_name_lower = prop_name.lower()

            if "status" in prop_name_lower:
                keywords.append("status_change")
                # Try to extract status value
                if prop_data.get("type") == "select":
                    select_value = prop_data.get("select", {})
                    if select_value:
                        status_name = select_value.get("name", "").lower()
                        if status_name:
                            keywords.append(status_name)

            elif "priority" in prop_name_lower:
                keywords.append("priority_change")

            elif "assign" in prop_name_lower:
                keywords.append("assignment_change")

        # Look for database type indicators
        if page_data.get("parent", {}).get("type") == "database_id":
            database_id = page_data["parent"]["database_id"]
            db_info = self.database_cache.get(database_id, {})
            db_title = db_info.get("title", "").lower()

            if any(word in db_title for word in ["task", "project", "bug", "issue"]):
                keywords.append("work_item")
            elif any(word in db_title for word in ["meeting", "note"]):
                keywords.append("documentation")

        return list(set(keywords))  # Remove duplicates

    def infer_project_from_page(
        self, title: str, page_data: dict[str, Any], database_id: Optional[str]
    ) -> Optional[str]:
        """Infer project context from page."""
        # Look for project indicators in title
        title_lower = title.lower()

        # Common project patterns
        if "project" in title_lower:
            # Try to extract project name
            words = title.split()
            for i, word in enumerate(words):
                if word.lower() == "project" and i > 0:
                    return words[i - 1]  # Word before "project"
                elif word.lower() == "project" and i < len(words) - 1:
                    return words[i + 1]  # Word after "project"

        # Check if page is in a database with project context
        if database_id:
            db_info = self.database_cache.get(database_id, {})
            db_title = db_info.get("title", "")
            if db_title:
                return db_title

        # Look for project mentions in properties
        properties = page_data.get("properties", {})
        for prop_name, prop_data in properties.items():
            if "project" in prop_name.lower():
                # Try to extract project value
                if prop_data.get("type") == "select":
                    select_value = prop_data.get("select", {})
                    if select_value:
                        return select_value.get("name")
                elif prop_data.get("type") == "title":
                    title_array = prop_data.get("title", [])
                    if title_array:
                        return title_array[0].get("text", {}).get("content")

        return None

    def calculate_notion_urgency(
        self,
        title: str,
        properties_changed: list[str],
        keywords: list[str],
        is_new: bool,
    ) -> float:
        """Calculate urgency for Notion changes."""
        score = 0.0
        title_lower = title.lower()

        # Urgent keywords in title
        if any(
            word in title_lower
            for word in ["urgent", "critical", "asap", "deadline", "emergency"]
        ):
            score += 0.4

        # High-priority keywords
        if any(word in title_lower for word in ["bug", "issue", "broken", "error"]):
            score += 0.3

        # Status/priority property changes are important
        status_changes = [
            p
            for p in properties_changed
            if "status" in p.lower() or "priority" in p.lower()
        ]
        if status_changes:
            score += 0.3

        # Assignment changes need attention
        if any("assign" in p.lower() for p in properties_changed):
            score += 0.25

        # New items are moderately urgent
        if is_new:
            score += 0.2

        # Deadline-related keywords
        if any(keyword in keywords for keyword in ["deadline", "due", "milestone"]):
            score += 0.2

        # Task completion is moderately urgent (for status updates)
        if any(keyword in keywords for keyword in ["done", "completed", "finished"]):
            score += 0.15

        return min(score, 1.0)

    async def force_sync(self) -> dict[str, Any]:
        """Force a synchronization of all databases (for testing/manual trigger)."""
        try:
            logger.info("Starting forced Notion sync...")

            # Reset last check to get more data
            original_last_check = self.last_check
            self.last_check = datetime.now() - timedelta(hours=1)

            # Poll changes
            await self.poll_changes()

            # Restore original last check
            self.last_check = original_last_check

            return {
                "status": "success",
                "pages_cached": len(self.known_pages),
                "databases_cached": len(self.database_cache),
            }

        except Exception as e:
            logger.error(f"Error in forced Notion sync: {e}")
            return {"status": "error", "error": str(e)}

    def get_stats(self) -> dict[str, Any]:
        """Get polling service statistics."""
        return {
            "is_running": self.is_running,
            "polling_interval": self.polling_interval,
            "known_pages": len(self.known_pages),
            "cached_databases": len(self.database_cache),
            "cached_users": len(self.user_cache),
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }
