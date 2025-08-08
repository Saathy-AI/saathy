#!/usr/bin/env python3
"""
Demo script for advanced Notion content processing pipeline.

This script demonstrates the comprehensive Notion integration that transforms
your entire knowledge base into a searchable, AI-powered system with rich metadata.
"""

import asyncio
import logging
from datetime import datetime

from saathy.connectors.base import ContentType, ProcessedContent


def create_sample_notion_content() -> list[ProcessedContent]:
    """Create sample Notion content for demonstration."""

    # Sample page content
    page_content = ProcessedContent(
        id="demo-page-001",
        content="""
# Project Planning Guide

This is a comprehensive guide for project planning and execution.

## Key Components

### 1. Requirements Gathering
- Identify stakeholder needs
- Define project scope
- Document functional requirements

### 2. Technical Architecture
- Design system architecture
- Choose appropriate technologies
- Plan data flow

### 3. Implementation Strategy
- Break down into sprints
- Assign team responsibilities
- Set up development environment

## Code Examples

Here's a sample API endpoint:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ProjectRequest(BaseModel):
    name: str
    description: str
    priority: str

@app.post("/projects")
async def create_project(project: ProjectRequest):
    # Implementation here
    return {"status": "created", "project_id": "123"}
```

## Action Items
- [ ] Review requirements with stakeholders
- [ ] Set up development environment
- [ ] Create initial project structure
- [ ] Schedule team kickoff meeting
        """,
        content_type=ContentType.TEXT,
        source="notion",
        metadata={
            "type": "page",
            "page_id": "demo-page-001",
            "title": "Project Planning Guide",
            "url": "https://notion.so/demo-page-001",
            "created_time": "2024-01-15T10:00:00Z",
            "last_edited_time": "2024-01-16T14:30:00Z",
            "parent_database": "Project Documentation",
            "database_id": "demo-db-001",
        },
        timestamp=datetime.now(),
        raw_data={},
    )

    # Sample database page content
    database_page = ProcessedContent(
        id="demo-db-page-002",
        content="""
# Sprint Planning Meeting Notes

**Date:** January 16, 2024
**Attendees:** Team Lead, Developers, QA

## Sprint Goals
- Complete user authentication system
- Implement basic CRUD operations
- Set up automated testing pipeline

## Technical Decisions
- Use JWT for authentication
- Implement role-based access control
- Use PostgreSQL for data persistence

## Task Breakdown
1. **Authentication Module** (3 days)
   - JWT implementation
   - Password hashing
   - Session management

2. **API Development** (5 days)
   - RESTful endpoints
   - Input validation
   - Error handling

3. **Testing** (2 days)
   - Unit tests
   - Integration tests
   - API documentation
        """,
        content_type=ContentType.TEXT,
        source="notion",
        metadata={
            "type": "database_page",
            "page_id": "demo-db-page-002",
            "title": "Sprint Planning Meeting Notes",
            "url": "https://notion.so/demo-db-page-002",
            "created_time": "2024-01-16T09:00:00Z",
            "last_edited_time": "2024-01-16T16:45:00Z",
            "parent_database": "Sprint Planning",
            "database_id": "demo-db-002",
            "properties_count": 8,
        },
        timestamp=datetime.now(),
        raw_data={},
    )

    # Sample code block content
    code_block = ProcessedContent(
        id="demo-code-003",
        content="""
```python
import jwt
from datetime import datetime, timedelta
from typing import Optional

class AuthService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.PyJWTError:
            return None
```""",
        content_type=ContentType.CODE,
        source="notion",
        metadata={
            "type": "code_block",
            "page_id": "demo-page-001",
            "language": "python",
            "title": "Authentication Service Implementation",
        },
        timestamp=datetime.now(),
        raw_data={},
    )

    return [page_content, database_page, code_block]


async def demo_advanced_processing():
    """Demonstrate the advanced Notion content processing pipeline."""

    print("🚀 Advanced Notion Content Processing Pipeline Demo")
    print("=" * 60)

    # Create sample content
    print("\n2. Creating sample Notion content...")
    content_items = create_sample_notion_content()

    print(f"   ✅ Created {len(content_items)} content items:")
    for i, content in enumerate(content_items, 1):
        print(
            f"      {i}. {content.metadata.get('title', 'Untitled')} ({content.metadata.get('type', 'unknown')})"
        )

    # Demonstrate content analysis
    print("\n3. Analyzing content characteristics...")

    for content in content_items:
        notion_type = content.metadata.get("type", "")
        content_length = len(content.content)
        has_code = "```" in content.content
        has_headers = "#" in content.content
        has_todos = any(
            word in content.content.lower() for word in ["todo", "task", "action"]
        )

        print(f"   📄 {content.metadata.get('title', 'Untitled')}:")
        print(f"      - Type: {notion_type}")
        print(f"      - Length: {content_length} characters")
        print(f"      - Has code: {has_code}")
        print(f"      - Has headers: {has_headers}")
        print(f"      - Has action items: {has_todos}")

        if content.metadata.get("parent_database"):
            print(f"      - Database: {content.metadata['parent_database']}")

    # Demonstrate embedding model selection
    print("\n4. Selecting optimal embedding models...")

    for content in content_items:
        if (
            content.content_type == ContentType.CODE
            or content.metadata.get("type") == "code_block"
        ):
            model = "microsoft/codebert-base"
            reason = "Code content - using CodeBERT for better code understanding"
        elif len(content.content) > 500:
            model = "all-mpnet-base-v2"
            reason = "Long-form content - using high-quality model"
        else:
            model = "all-MiniLM-L6-v2"
            reason = "Short content - using fast model"

        print(f"   🤖 {content.metadata.get('title', 'Untitled')}: {model}")
        print(f"      Reason: {reason}")

    # Demonstrate metadata extraction
    print("\n5. Extracting rich metadata...")

    for content in content_items:
        print(f"   📊 {content.metadata.get('title', 'Untitled')}:")

        # Core metadata
        print(f"      - Page ID: {content.metadata.get('page_id', 'N/A')}")
        print(f"      - URL: {content.metadata.get('url', 'N/A')}")
        print(f"      - Created: {content.metadata.get('created_time', 'N/A')}")
        print(f"      - Last edited: {content.metadata.get('last_edited_time', 'N/A')}")

        # Database context
        if content.metadata.get("parent_database"):
            print(f"      - Database: {content.metadata['parent_database']}")
            print(f"      - Database ID: {content.metadata.get('database_id', 'N/A')}")

        # Content analysis
        print(f"      - Content length: {len(content.content)} characters")
        print(f"      - Word count: {len(content.content.split())}")

        # Programming language for code blocks
        if content.metadata.get("language"):
            print(f"      - Language: {content.metadata['language']}")

    # Demonstrate tag generation
    print("\n6. Generating searchable tags...")

    for content in content_items:
        tags = []
        tags.append("notion")

        # Type-based tags
        notion_type = content.metadata.get("type", "")
        if notion_type:
            tags.append(f"type:{notion_type}")

        # Content-based tags
        if content.content_type == ContentType.CODE:
            tags.append("code")
            if content.metadata.get("language"):
                tags.append(f"lang:{content.metadata['language']}")

        # Database tags
        if content.metadata.get("parent_database"):
            db_name = content.metadata["parent_database"].lower().replace(" ", "_")
            tags.append(f"database:{db_name}")

        # Content analysis tags
        if len(content.content) > 1000:
            tags.append("long_form")
        elif len(content.content) < 100:
            tags.append("short_form")

        if "```" in content.content:
            tags.append("contains_code")

        if any(word in content.content.lower() for word in ["todo", "task", "action"]):
            tags.append("actionable")

        print(f"   🏷️  {content.metadata.get('title', 'Untitled')}:")
        print(f"      Tags: {', '.join(tags)}")

    # Demonstrate hierarchy extraction
    print("\n7. Extracting content hierarchy...")

    for content in content_items:
        if "# " in content.content:
            headers = []
            for line in content.content.split("\n"):
                if line.strip().startswith("#"):
                    level = len(line) - len(line.lstrip("#"))
                    header_text = line.lstrip("# ").strip()
                    if header_text:
                        headers.append({"level": level, "text": header_text})

            if headers:
                print(f"   📑 {content.metadata.get('title', 'Untitled')}:")
                print(f"      Main header: {headers[0]['text']}")
                print(f"      Total headers: {len(headers)}")
                for header in headers[:3]:  # Show first 3 headers
                    indent = "  " * (header["level"] - 1)
                    print(f"      {indent}{'#' * header['level']} {header['text']}")

    # Demonstrate search capabilities
    print("\n8. Search capabilities enabled...")

    search_examples = [
        "Find all code blocks in Python",
        "Show project planning documents",
        "Find content with action items",
        "Search in Project Documentation database",
        "Find long-form content about authentication",
        "Show content created in the last week",
    ]

    for example in search_examples:
        print(f"   🔍 Example query: '{example}'")

    print("\n9. Processing statistics...")

    stats = {
        "pages_processed": 0,
        "databases_processed": 0,
        "code_blocks_processed": 0,
        "properties_extracted": 0,
        "total_content_length": 0,
    }

    for content in content_items:
        notion_type = content.metadata.get("type", "")

        if notion_type == "page":
            stats["pages_processed"] += 1
        elif notion_type == "database_page":
            stats["databases_processed"] += 1
        elif notion_type == "code_block":
            stats["code_blocks_processed"] += 1

        stats["properties_extracted"] += content.metadata.get("properties_count", 0)
        stats["total_content_length"] += len(content.content)

    print("   📈 Processing Summary:")
    print(f"      - Pages processed: {stats['pages_processed']}")
    print(f"      - Database pages processed: {stats['databases_processed']}")
    print(f"      - Code blocks processed: {stats['code_blocks_processed']}")
    print(f"      - Properties extracted: {stats['properties_extracted']}")
    print(f"      - Total content length: {stats['total_content_length']} characters")

    print("\n✅ Advanced Notion content processing pipeline demonstration completed!")
    print("\n🎯 Key Benefits:")
    print("   • Rich metadata for powerful search capabilities")
    print("   • Optimal embedding model selection based on content type")
    print("   • Hierarchical organization with tags and categories")
    print("   • Code blocks processed with appropriate models")
    print("   • Database properties extracted and searchable")
    print("   • Content analysis for actionable items and structure")
    print("   • Temporal data for time-based queries")
    print("   • Comprehensive processing statistics and monitoring")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Run the demo
    asyncio.run(demo_advanced_processing())
