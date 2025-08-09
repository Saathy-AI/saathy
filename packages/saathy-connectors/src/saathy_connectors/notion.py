"""Notion connector implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from notion_client import AsyncClient as NotionClient

from saathy_core import ContentType, ProcessedContent, ProcessingStatus, ConnectorStatus
from .base import BaseConnector

logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    """Connector for Notion integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("notion", config)
        self.token = config.get("token")
        self.databases = config.get("databases", [])
        self.pages = config.get("pages", [])
        self.poll_interval = config.get("poll_interval", 300)  # 5 minutes default
        self._client: Optional[NotionClient] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._last_sync: Dict[str, datetime] = {}
    
    async def validate_config(self) -> bool:
        """Validate Notion configuration."""
        if not self.token:
            self.logger.error("Notion token not provided")
            return False
        
        if not self.databases and not self.pages:
            self.logger.error("No Notion databases or pages configured")
            return False
        
        return True
    
    async def _start_connector(self) -> None:
        """Start the Notion connector."""
        # Initialize Notion client
        self._client = NotionClient(auth=self.token)
        
        # Test connection
        try:
            users = await self._client.users.list()
            self.logger.info(f"Connected to Notion workspace with {len(users['results'])} users")
            
            # Start polling task
            self._polling_task = asyncio.create_task(self._poll_notion())
            
        except Exception as e:
            raise ValueError(f"Failed to connect to Notion: {e}")
    
    async def _stop_connector(self) -> None:
        """Stop the Notion connector."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        
        self._client = None
    
    async def _poll_notion(self) -> None:
        """Poll Notion for changes."""
        while self.status == ConnectorStatus.ACTIVE:
            try:
                await self._check_for_updates()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error during Notion polling: {e}")
                self._error_count += 1
                self._last_error = str(e)
                await asyncio.sleep(self.poll_interval)
    
    async def _check_for_updates(self) -> None:
        """Check Notion for updates."""
        contents = []
        
        # Check databases
        for database_id in self.databases:
            db_contents = await self._sync_database(database_id)
            contents.extend(db_contents)
        
        # Check pages
        for page_id in self.pages:
            page_content = await self._sync_page(page_id)
            if page_content:
                contents.append(page_content)
        
        # Process contents
        for content in contents:
            self._processed_count += 1
            # Here you would typically send to vector store or event stream
    
    async def _sync_database(self, database_id: str) -> List[ProcessedContent]:
        """Sync a Notion database."""
        if not self._client:
            return []
        
        contents = []
        last_sync = self._last_sync.get(f"db:{database_id}", datetime.utcnow() - timedelta(days=1))
        
        try:
            # Get database info
            database = await self._client.databases.retrieve(database_id)
            
            # Query database for updated pages
            response = await self._client.databases.query(
                database_id=database_id,
                filter={
                    "timestamp": "last_edited_time",
                    "last_edited_time": {
                        "after": last_sync.isoformat()
                    }
                },
                sorts=[
                    {
                        "timestamp": "last_edited_time",
                        "direction": "descending"
                    }
                ]
            )
            
            for page in response["results"]:
                content = await self._process_notion_page(page, database["title"])
                if content:
                    contents.append(content)
            
            # Update last sync time
            self._last_sync[f"db:{database_id}"] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Failed to sync database {database_id}: {e}")
        
        return contents
    
    async def _sync_page(self, page_id: str) -> Optional[ProcessedContent]:
        """Sync a Notion page."""
        if not self._client:
            return None
        
        try:
            # Get page
            page = await self._client.pages.retrieve(page_id)
            
            # Check if updated since last sync
            last_edited = datetime.fromisoformat(
                page["last_edited_time"].replace("Z", "+00:00")
            )
            last_sync = self._last_sync.get(f"page:{page_id}", datetime.min)
            
            if last_edited > last_sync:
                content = await self._process_notion_page(page)
                self._last_sync[f"page:{page_id}"] = datetime.utcnow()
                return content
            
        except Exception as e:
            self.logger.error(f"Failed to sync page {page_id}: {e}")
        
        return None
    
    async def _process_notion_page(
        self,
        page: Dict[str, Any],
        database_title: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[ProcessedContent]:
        """Process a Notion page into ProcessedContent."""
        try:
            # Extract title
            title = ""
            if "properties" in page:
                # Database page
                title_prop = page["properties"].get("Name") or page["properties"].get("title")
                if title_prop and title_prop["type"] == "title":
                    title_texts = title_prop.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_texts)
            
            # Get page content
            page_id = page["id"]
            blocks = await self._get_page_blocks(page_id)
            content_text = self._blocks_to_text(blocks)
            
            # Create ProcessedContent
            return ProcessedContent(
                content_type=ContentType.DOCUMENT,
                title=title or "Untitled",
                content=content_text,
                source=f"notion:{page_id}",
                source_id=page_id,
                metadata={
                    "page_id": page_id,
                    "url": page.get("url", ""),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                    "created_by": page.get("created_by", {}).get("id"),
                    "last_edited_by": page.get("last_edited_by", {}).get("id"),
                    "parent": page.get("parent"),
                    "archived": page.get("archived", False),
                },
                timestamp=datetime.fromisoformat(
                    page["last_edited_time"].replace("Z", "+00:00")
                ),
                processing_status=ProcessingStatus.COMPLETED,
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process Notion page: {e}")
            return None
    
    async def _get_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        """Get all blocks in a page."""
        if not self._client:
            return []
        
        blocks = []
        
        try:
            response = await self._client.blocks.children.list(block_id=page_id)
            blocks.extend(response["results"])
            
            # Handle pagination
            while response.get("has_more"):
                response = await self._client.blocks.children.list(
                    block_id=page_id,
                    start_cursor=response["next_cursor"]
                )
                blocks.extend(response["results"])
            
        except Exception as e:
            self.logger.error(f"Failed to get page blocks: {e}")
        
        return blocks
    
    def _blocks_to_text(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert Notion blocks to plain text."""
        text_parts = []
        
        for block in blocks:
            block_type = block["type"]
            block_data = block.get(block_type, {})
            
            # Extract text based on block type
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                rich_texts = block_data.get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_texts)
                if text:
                    text_parts.append(text)
                    
            elif block_type == "bulleted_list_item" or block_type == "numbered_list_item":
                rich_texts = block_data.get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_texts)
                if text:
                    text_parts.append(f"• {text}")
                    
            elif block_type == "to_do":
                rich_texts = block_data.get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_texts)
                checked = block_data.get("checked", False)
                if text:
                    checkbox = "☑" if checked else "☐"
                    text_parts.append(f"{checkbox} {text}")
                    
            elif block_type == "code":
                rich_texts = block_data.get("rich_text", [])
                code = "".join(rt.get("plain_text", "") for rt in rich_texts)
                language = block_data.get("language", "")
                if code:
                    text_parts.append(f"```{language}\n{code}\n```")
                    
            elif block_type == "divider":
                text_parts.append("---")
                
            # Handle nested blocks
            if block.get("has_children"):
                # In a real implementation, you'd recursively fetch child blocks
                pass
        
        return "\n\n".join(text_parts)
    
    async def _process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Process Notion event (for future webhook support)."""
        # Notion doesn't have webhooks yet, but this is for future compatibility
        return []
    
    async def sync_content(
        self,
        full_sync: bool = False,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Manually sync Notion content."""
        if not self._client:
            raise RuntimeError("Notion client not initialized")
        
        results = {
            "contents": [],
            "pages": 0,
            "databases": 0,
            "blocks": 0,
        }
        
        # Sync databases
        for database_id in self.databases:
            contents = await self._sync_database(database_id)
            results["contents"].extend(contents)
            results["databases"] += 1
            results["pages"] += len(contents)
        
        # Sync pages
        for page_id in self.pages:
            content = await self._sync_page(page_id)
            if content:
                results["contents"].append(content)
                results["pages"] += 1
        
        return results
    
    async def search(self, query: str, limit: int = 10) -> List[ProcessedContent]:
        """Search Notion content."""
        if not self._client:
            raise RuntimeError("Notion client not initialized")
        
        contents = []
        
        try:
            response = await self._client.search(
                query=query,
                filter={"property": "object", "value": "page"},
                page_size=limit
            )
            
            for result in response["results"]:
                if result["object"] == "page":
                    content = await self._process_notion_page(result)
                    if content:
                        contents.append(content)
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
        
        return contents