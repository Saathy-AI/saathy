"""Notion content extractor for processing pages, databases, and blocks."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from notion_client import AsyncClient

from .base import ContentType, ProcessedContent


class NotionContentExtractor:
    """Extract and process Notion content into searchable text format."""

    def __init__(self, client: AsyncClient):
        self.client = client
        self.logger = logging.getLogger("saathy.connector.notion.extractor")

    async def extract_page_content(
        self, page_data: dict[str, Any], parent_database: Optional[str] = None
    ) -> list[ProcessedContent]:
        """Extract content from a Notion page and its blocks."""
        try:
            page_id = page_data["id"]
            page_title = self._extract_title(
                page_data.get("properties", {}).get("title", {}).get("title", [])
            )

            if not page_title:
                page_title = self._extract_title(
                    page_data.get("properties", {}).get("Name", {}).get("title", [])
                )

            if not page_title:
                page_title = "Untitled Page"

            processed_contents = []

            # Extract page properties as metadata
            properties_content = self._extract_properties_content(
                page_data.get("properties", {})
            )

            # Create main page content
            page_content = f"Title: {page_title}\n\n"
            if properties_content:
                page_content += f"Properties:\n{properties_content}\n\n"

            # Extract blocks content
            blocks_content = await self._extract_blocks_content(page_id)
            if blocks_content:
                page_content += f"Content:\n{blocks_content}"

            # Create ProcessedContent for the page
            page_processed = ProcessedContent(
                id=f"page_{page_id}",
                content=page_content.strip(),
                content_type=ContentType.TEXT,
                source="notion_page",
                metadata={
                    "page_id": page_id,
                    "page_title": page_title,
                    "parent_database": parent_database,
                    "url": page_data.get("url", ""),
                    "created_time": page_data.get("created_time", ""),
                    "last_edited_time": page_data.get("last_edited_time", ""),
                    "archived": page_data.get("archived", False),
                },
                timestamp=datetime.now(timezone.utc),
                raw_data=page_data,
            )
            processed_contents.append(page_processed)

            # Extract individual blocks as separate content items for better search
            if blocks_content:
                block_contents = await self._extract_individual_blocks(
                    page_id, page_title
                )
                processed_contents.extend(block_contents)

            return processed_contents

        except Exception as e:
            self.logger.error(
                f"Failed to extract page content for {page_data.get('id')}: {e}"
            )
            return []

    async def _extract_blocks_content(self, page_id: str) -> str:
        """Extract all blocks content from a page."""
        try:
            blocks_content = []
            has_more = True
            start_cursor = None

            while has_more:
                query_params = {"block_id": page_id, "page_size": 100}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response = await self.client.blocks.children.list(**query_params)

                for block in response["results"]:
                    block_text = self._extract_block_text(block)
                    if block_text:
                        blocks_content.append(block_text)

                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")

            return "\n\n".join(blocks_content)

        except Exception as e:
            self.logger.error(
                f"Failed to extract blocks content for page {page_id}: {e}"
            )
            return ""

    async def _extract_individual_blocks(
        self, page_id: str, page_title: str
    ) -> list[ProcessedContent]:
        """Extract individual blocks as separate content items."""
        try:
            block_contents = []
            has_more = True
            start_cursor = None
            block_index = 0

            while has_more:
                query_params = {"block_id": page_id, "page_size": 100}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response = await self.client.blocks.children.list(**query_params)

                for block in response["results"]:
                    block_text = self._extract_block_text(block)
                    if block_text:
                        block_id = block["id"]
                        block_type = block["type"]

                        # Determine content type based on block type
                        content_type = self._get_content_type_for_block(block_type)

                        block_processed = ProcessedContent(
                            id=f"block_{block_id}",
                            content=block_text,
                            content_type=content_type,
                            source="notion_block",
                            metadata={
                                "block_id": block_id,
                                "block_type": block_type,
                                "page_id": page_id,
                                "page_title": page_title,
                                "block_index": block_index,
                                "created_time": block.get("created_time", ""),
                                "last_edited_time": block.get("last_edited_time", ""),
                            },
                            timestamp=datetime.now(timezone.utc),
                            raw_data=block,
                        )
                        block_contents.append(block_processed)
                        block_index += 1

                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")

            return block_contents

        except Exception as e:
            self.logger.error(
                f"Failed to extract individual blocks for page {page_id}: {e}"
            )
            return []

    def _extract_block_text(self, block: dict[str, Any]) -> str:
        """Extract text content from a single block."""
        try:
            block_type = block["type"]

            if block_type == "paragraph":
                return self._extract_rich_text(block["paragraph"].get("rich_text", []))

            elif block_type == "heading_1":
                return f"# {self._extract_rich_text(block['heading_1'].get('rich_text', []))}"

            elif block_type == "heading_2":
                return f"## {self._extract_rich_text(block['heading_2'].get('rich_text', []))}"

            elif block_type == "heading_3":
                return f"### {self._extract_rich_text(block['heading_3'].get('rich_text', []))}"

            elif block_type == "bulleted_list_item":
                return f"• {self._extract_rich_text(block['bulleted_list_item'].get('rich_text', []))}"

            elif block_type == "numbered_list_item":
                return f"1. {self._extract_rich_text(block['numbered_list_item'].get('rich_text', []))}"

            elif block_type == "to_do":
                todo_item = block["to_do"]
                checked = "☑" if todo_item.get("checked", False) else "☐"
                return f"{checked} {self._extract_rich_text(todo_item.get('rich_text', []))}"

            elif block_type == "toggle":
                return (
                    f"▶ {self._extract_rich_text(block['toggle'].get('rich_text', []))}"
                )

            elif block_type == "quote":
                return (
                    f"> {self._extract_rich_text(block['quote'].get('rich_text', []))}"
                )

            elif block_type == "callout":
                callout = block["callout"]
                icon = callout.get("icon", {}).get("emoji", "💡")
                return f"{icon} {self._extract_rich_text(callout.get('rich_text', []))}"

            elif block_type == "code":
                code_block = block["code"]
                language = code_block.get("language", "")
                code_text = self._extract_rich_text(code_block.get("rich_text", []))
                return f"```{language}\n{code_text}\n```"

            elif block_type == "divider":
                return "---"

            elif block_type == "table_of_contents":
                return "[Table of Contents]"

            elif block_type == "breadcrumb":
                return "[Breadcrumb]"

            elif block_type == "column_list":
                return "[Column Layout]"

            elif block_type == "column":
                return "[Column]"

            elif block_type == "synced_block":
                return f"[Synced Block: {block['synced_block'].get('synced_from', {}).get('block_id', 'unknown')}]"

            elif block_type == "template":
                return "[Template Block]"

            elif block_type == "link_to_page":
                return (
                    f"[Link to Page: {block['link_to_page'].get('page_id', 'unknown')}]"
                )

            elif block_type == "table":
                return "[Table]"

            elif block_type == "table_row":
                cells = block["table_row"].get("cells", [])
                cell_texts = []
                for cell in cells:
                    cell_text = self._extract_rich_text(cell)
                    cell_texts.append(cell_text if cell_text else "")
                return " | ".join(cell_texts)

            elif block_type == "embed":
                embed = block["embed"]
                url = embed.get("url", "")
                caption = self._extract_rich_text(embed.get("caption", []))
                return f"[Embed: {url}] {caption}"

            elif block_type == "bookmark":
                bookmark = block["bookmark"]
                url = bookmark.get("url", "")
                caption = self._extract_rich_text(bookmark.get("caption", []))
                return f"[Bookmark: {url}] {caption}"

            elif block_type == "image":
                image = block["image"]
                caption = self._extract_rich_text(image.get("caption", []))
                return f"[Image] {caption}"

            elif block_type == "video":
                video = block["video"]
                caption = self._extract_rich_text(video.get("caption", []))
                return f"[Video] {caption}"

            elif block_type == "file":
                file_block = block["file"]
                caption = self._extract_rich_text(file_block.get("caption", []))
                return f"[File] {caption}"

            elif block_type == "pdf":
                pdf = block["pdf"]
                caption = self._extract_rich_text(pdf.get("caption", []))
                return f"[PDF] {caption}"

            elif block_type == "audio":
                audio = block["audio"]
                caption = self._extract_rich_text(audio.get("caption", []))
                return f"[Audio] {caption}"

            else:
                # Unknown block type, try to extract any rich text
                for _, value in block.items():
                    if isinstance(value, dict) and "rich_text" in value:
                        return self._extract_rich_text(value["rich_text"])
                return f"[Unknown block type: {block_type}]"

        except Exception as e:
            self.logger.error(
                f"Failed to extract text from block {block.get('id')}: {e}"
            )
            return ""

    def _extract_rich_text(self, rich_text_array: list[dict[str, Any]]) -> str:
        """Extract plain text from Notion rich text array."""
        if not rich_text_array:
            return ""

        text_parts = []
        for item in rich_text_array:
            if "plain_text" in item:
                text_parts.append(item["plain_text"])

        return "".join(text_parts)

    def _extract_properties_content(self, properties: dict[str, Any]) -> str:
        """Extract content from page properties."""
        try:
            property_texts = []

            for prop_name, prop_data in properties.items():
                if not prop_data:
                    continue

                prop_type = prop_data.get("type")
                if not prop_type:
                    continue

                if prop_type == "title":
                    title_text = self._extract_rich_text(
                        prop_data["title"].get("title", [])
                    )
                    if title_text:
                        property_texts.append(f"{prop_name}: {title_text}")

                elif prop_type == "rich_text":
                    rich_text = self._extract_rich_text(
                        prop_data["rich_text"].get("rich_text", [])
                    )
                    if rich_text:
                        property_texts.append(f"{prop_name}: {rich_text}")

                elif prop_type == "number":
                    number_value = prop_data["number"].get("number")
                    if number_value is not None:
                        property_texts.append(f"{prop_name}: {number_value}")

                elif prop_type == "select":
                    select_value = prop_data["select"].get("name")
                    if select_value:
                        property_texts.append(f"{prop_name}: {select_value}")

                elif prop_type == "multi_select":
                    multi_select = prop_data["multi_select"].get("multi_select", [])
                    if multi_select:
                        values = [item.get("name", "") for item in multi_select]
                        property_texts.append(f"{prop_name}: {', '.join(values)}")

                elif prop_type == "date":
                    date_data = prop_data["date"].get("date")
                    if date_data:
                        start_date = date_data.get("start", "")
                        end_date = date_data.get("end", "")
                        if end_date:
                            property_texts.append(
                                f"{prop_name}: {start_date} to {end_date}"
                            )
                        else:
                            property_texts.append(f"{prop_name}: {start_date}")

                elif prop_type == "checkbox":
                    checkbox_value = prop_data["checkbox"].get("checkbox", False)
                    property_texts.append(
                        f"{prop_name}: {'Yes' if checkbox_value else 'No'}"
                    )

                elif prop_type == "url":
                    url_value = prop_data["url"].get("url")
                    if url_value:
                        property_texts.append(f"{prop_name}: {url_value}")

                elif prop_type == "email":
                    email_value = prop_data["email"].get("email")
                    if email_value:
                        property_texts.append(f"{prop_name}: {email_value}")

                elif prop_type == "phone_number":
                    phone_value = prop_data["phone_number"].get("phone_number")
                    if phone_value:
                        property_texts.append(f"{prop_name}: {phone_value}")

                elif prop_type == "formula":
                    formula_value = prop_data["formula"].get("string")
                    if formula_value:
                        property_texts.append(f"{prop_name}: {formula_value}")

                elif prop_type == "relation":
                    relation = prop_data["relation"].get("relation", [])
                    if relation:
                        relation_ids = [item.get("id", "") for item in relation]
                        property_texts.append(f"{prop_name}: {', '.join(relation_ids)}")

                elif prop_type == "rollup":
                    rollup = prop_data["rollup"].get("rollup", {})
                    rollup_type = rollup.get("type")
                    if rollup_type == "array":
                        array_items = rollup.get("array", [])
                        if array_items:
                            property_texts.append(
                                f"{prop_name}: {len(array_items)} items"
                            )
                    elif rollup_type == "number":
                        number_value = rollup.get("number")
                        if number_value is not None:
                            property_texts.append(f"{prop_name}: {number_value}")
                    elif rollup_type == "date":
                        date_data = rollup.get("date")
                        if date_data:
                            property_texts.append(
                                f"{prop_name}: {date_data.get('start', '')}"
                            )

                elif prop_type == "people":
                    people = prop_data["people"].get("people", [])
                    if people:
                        people_names = [person.get("name", "") for person in people]
                        property_texts.append(f"{prop_name}: {', '.join(people_names)}")

                elif prop_type == "files":
                    files = prop_data["files"].get("files", [])
                    if files:
                        file_names = [file.get("name", "") for file in files]
                        property_texts.append(f"{prop_name}: {', '.join(file_names)}")

                elif prop_type == "created_time":
                    created_time = prop_data["created_time"].get("created_time")
                    if created_time:
                        property_texts.append(f"{prop_name}: {created_time}")

                elif prop_type == "created_by":
                    created_by = prop_data["created_by"].get("created_by", {})
                    if created_by:
                        name = created_by.get("name", "")
                        property_texts.append(f"{prop_name}: {name}")

                elif prop_type == "last_edited_time":
                    last_edited_time = prop_data["last_edited_time"].get(
                        "last_edited_time"
                    )
                    if last_edited_time:
                        property_texts.append(f"{prop_name}: {last_edited_time}")

                elif prop_type == "last_edited_by":
                    last_edited_by = prop_data["last_edited_by"].get(
                        "last_edited_by", {}
                    )
                    if last_edited_by:
                        name = last_edited_by.get("name", "")
                        property_texts.append(f"{prop_name}: {name}")

            return "\n".join(property_texts)

        except Exception as e:
            self.logger.error(f"Failed to extract properties content: {e}")
            return ""

    def _extract_title(self, title_array: list[dict[str, Any]]) -> str:
        """Extract plain text from Notion title array."""
        if not title_array:
            return "Untitled"
        return "".join([item.get("plain_text", "") for item in title_array])

    def _get_content_type_for_block(self, block_type: str) -> ContentType:
        """Determine content type based on block type."""
        if block_type == "code":
            return ContentType.CODE
        elif block_type in [
            "paragraph",
            "heading_1",
            "heading_2",
            "heading_3",
            "quote",
        ]:
            return ContentType.MARKDOWN
        else:
            return ContentType.TEXT
