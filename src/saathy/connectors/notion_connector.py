"""Notion connector for Saathy - handles content extraction and monitoring."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from .base import BaseConnector, ConnectorStatus, ProcessedContent
from .content_processor import NotionContentProcessor
from .notion_content_extractor import NotionContentExtractor


class NotionConnector(BaseConnector):
    """Notion connector for extracting and monitoring content."""

    def __init__(self, config: dict[str, Any]):
        super().__init__("notion", config)
        self.token = config.get("token")
        self.databases = config.get("databases", [])  # List of database IDs to monitor
        self.pages = config.get("pages", [])  # List of page IDs to monitor
        self.poll_interval = config.get("poll_interval", 300)  # 5 minutes default
        self.client: Optional[AsyncClient] = None
        self.content_extractor: Optional[NotionContentExtractor] = None
        self.content_processor: Optional[NotionContentProcessor] = None
        self._running = False
        self._start_time: Optional[datetime] = (
            None  # Track start time for uptime calculation
        )
        self._last_sync: dict[str, datetime] = {}  # Track last sync time per resource
        self._processed_items: set[str] = (
            set()
        )  # Track processed items to avoid duplicates

    async def start(self) -> None:
        """Start Notion connector with initial full sync and polling."""
        if not self.token:
            self.logger.error("Missing Notion token")
            self.status = ConnectorStatus.ERROR
            return

        try:
            self.status = ConnectorStatus.ACTIVE
            self.logger.info("Starting Notion connector...")

            # Initialize client and content extractor
            self.client = AsyncClient(auth=self.token)
            self.content_extractor = NotionContentExtractor(self.client)

            # Test connection
            await self._test_connection()

            self.status = ConnectorStatus.ACTIVE
            self._running = True
            self._start_time = datetime.now(timezone.utc)

            # Perform initial full sync
            await self._initial_sync()

            # Start polling task
            asyncio.create_task(self._polling_loop())

            self.logger.info("Notion connector started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start Notion connector: {e}")
            self.status = ConnectorStatus.ERROR
            raise

    async def stop(self) -> None:
        """Stop Notion connector."""
        self._running = False
        self.status = ConnectorStatus.INACTIVE
        self._start_time = None

        if self.client:
            # notion-client doesn't have explicit close method
            self.client = None

        self.logger.info("Notion connector stopped")

    def set_content_processor(self, processor: NotionContentProcessor) -> None:
        """Set the content processor for this connector."""
        self.content_processor = processor

    async def _test_connection(self) -> None:
        """Test Notion API connection."""
        try:
            # Try to list users to test connection
            await self.client.users.list()
            self.logger.info("Notion API connection successful")
        except APIResponseError as e:
            raise Exception(f"Notion API connection failed: {e}") from e

    async def _initial_sync(self) -> None:
        """Perform initial full sync of all configured content."""
        self.logger.info("Starting initial Notion sync...")

        try:
            # Sync configured databases
            for database_id in self.databases:
                await self._sync_database(database_id, full_sync=True)

            # Sync configured pages
            for page_id in self.pages:
                await self._sync_page(page_id, full_sync=True)

            # Auto-discover databases if none configured
            if not self.databases and not self.pages:
                await self._auto_discover_content()

            self.logger.info("Initial Notion sync completed")

        except Exception as e:
            self.logger.error(f"Initial sync failed: {e}")
            raise

    async def _auto_discover_content(self) -> None:
        """Auto-discover databases and pages to sync."""
        try:
            self.logger.info("Auto-discovering Notion content...")

            # Search for databases
            search_response = await self.client.search(
                filter={"property": "object", "value": "database"}
            )

            discovered_databases = []
            for result in search_response.get("results", []):
                db_id = result["id"]
                db_title = self._extract_title(result.get("title", []))
                discovered_databases.append(db_id)
                self.logger.info(f"Discovered database: {db_title} ({db_id})")

            # Sync discovered databases (limit to prevent overwhelming)
            for db_id in discovered_databases[:5]:  # Limit to 5 databases
                await self._sync_database(db_id, full_sync=True)

        except Exception as e:
            self.logger.warning(f"Auto-discovery failed: {e}")

    async def _polling_loop(self) -> None:
        """Main polling loop for incremental updates."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                if not self._running:
                    break

                self.logger.debug("Polling for Notion updates...")

                # Poll configured databases for changes
                for database_id in self.databases:
                    await self._sync_database(database_id, full_sync=False)

                # Poll configured pages for changes
                for page_id in self.pages:
                    await self._sync_page(page_id, full_sync=False)

            except Exception as e:
                self.logger.error(f"Polling error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _sync_database(self, database_id: str, full_sync: bool = False) -> None:
        """Sync a database and its pages."""
        try:
            # Get database info
            database = await self.client.databases.retrieve(database_id)
            database_title = self._extract_title(database.get("title", []))

            # Query database pages
            query_params = {"database_id": database_id, "page_size": 100}

            # For incremental sync, filter by last edited time
            if not full_sync and database_id in self._last_sync:
                last_sync_time = self._last_sync[database_id]
                query_params["filter"] = {
                    "timestamp": "last_edited_time",
                    "last_edited_time": {"after": last_sync_time.isoformat()},
                }

            # Query pages with pagination
            has_more = True
            start_cursor = None
            page_count = 0

            while has_more:
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response = await self.client.databases.query(**query_params)

                for page in response["results"]:
                    await self._process_database_page(page, database_title)
                    page_count += 1

                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")

            # Update last sync time
            self._last_sync[database_id] = datetime.now(timezone.utc)

            self.logger.info(f"Synced database '{database_title}': {page_count} pages")

        except Exception as e:
            self.logger.error(f"Failed to sync database {database_id}: {e}")

    async def _sync_page(self, page_id: str, full_sync: bool = False) -> None:
        """Sync a single page and its content."""
        try:
            # Get page info
            page = await self.client.pages.retrieve(page_id)

            # Check if page was modified since last sync
            if not full_sync and page_id in self._last_sync:
                last_edited = datetime.fromisoformat(
                    page["last_edited_time"].replace("Z", "+00:00")
                )
                if last_edited <= self._last_sync[page_id]:
                    return  # No changes

            # Process the page
            await self._process_page(page)

            # Update last sync time
            self._last_sync[page_id] = datetime.now(timezone.utc)

        except Exception as e:
            self.logger.error(f"Failed to sync page {page_id}: {e}")

    async def _process_database_page(
        self, page_data: dict[str, Any], database_title: str
    ) -> None:
        """Process a page from a database with content processor."""
        try:
            page_id = page_data["id"]

            if page_id in self._processed_items:
                return

            # Extract page content
            processed_content = await self.content_extractor.extract_page_content(
                page_data, parent_database=database_title
            )

            if processed_content and self.content_processor:
                # Process and store in vector database
                result = await self.content_processor.process_notion_content(
                    processed_content
                )
                self.logger.info(
                    f"Processed database page '{database_title}': {result.processed} items, {result.errors} errors"
                )

                # Mark as processed
                self._processed_items.add(page_id)
            else:
                self.logger.warning(
                    "No content processor configured or no content extracted"
                )

        except Exception as e:
            self.logger.error(
                f"Failed to process database page {page_data.get('id')}: {e}"
            )

    async def _process_page(self, page_data: dict[str, Any]) -> None:
        """Process a standalone page with content processor."""
        try:
            page_id = page_data["id"]

            if page_id in self._processed_items:
                return

            # Extract page content
            processed_content = await self.content_extractor.extract_page_content(
                page_data
            )

            if processed_content and self.content_processor:
                # Process and store in vector database
                result = await self.content_processor.process_notion_content(
                    processed_content
                )
                self.logger.info(
                    f"Processed page: {result.processed} items, {result.errors} errors"
                )

                # Mark as processed
                self._processed_items.add(page_id)
            else:
                self.logger.warning(
                    "No content processor configured or no content extracted"
                )

        except Exception as e:
            self.logger.error(f"Failed to process page {page_data.get('id')}: {e}")

    def _extract_title(self, title_array: list[dict[str, Any]]) -> str:
        """Extract plain text from Notion title array."""
        if not title_array:
            return "Untitled"
        return "".join([item.get("plain_text", "") for item in title_array])

    async def process_event(self, event_data: dict[str, Any]) -> list[ProcessedContent]:
        """Process Notion event data (for manual processing)."""
        processed_items = []

        try:
            event_type = event_data.get("type", "")

            if event_type == "page":
                content = await self.content_extractor.extract_page_content(event_data)
                if content:
                    processed_items.extend(content)

        except Exception as e:
            self.logger.error(f"Error processing event: {e}")

        return processed_items
