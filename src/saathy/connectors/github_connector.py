import logging
from typing import Any, Dict, List
from datetime import datetime

from saathy.connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ContentType,
    ProcessedContent,
)

logger = logging.getLogger(__name__)


class GithubConnector(BaseConnector):
    """Connector for GitHub to process webhook events."""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)

    async def start(self) -> None:
        """Start the GitHub connector."""
        logger.info(f"Starting {self.name} connector.")
        self.status = ConnectorStatus.ACTIVE
        logger.info(f"{self.name} connector started.")

    async def stop(self) -> None:
        """Stop the GitHub connector."""
        logger.info(f"Stopping {self.name} connector.")
        self.status = ConnectorStatus.INACTIVE
        logger.info(f"{self.name} connector stopped.")

    async def process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Process a GitHub webhook event."""
        # In a real scenario, we'd get this from request headers.
        # For now, we'll assume it's part of the event_data for simulation.
        event_type = event_data.get("event_type")
        if not event_type:
            logger.warning("Received event with no event_type specified.")
            return []

        logger.info(f"Processing GitHub event: {event_type}")

        try:
            if event_type == "push":
                return await self._process_push_event(event_data["payload"])
            elif event_type == "pull_request":
                return await self._process_pull_request_event(event_data["payload"])
            elif event_type == "issues":
                return await self._process_issues_event(event_data["payload"])
            else:
                logger.debug(f"Ignoring unsupported GitHub event type: {event_type}")
                return []
        except Exception as e:
            logger.error(f"Error processing GitHub event '{event_type}': {e}", exc_info=True)
            self.status = ConnectorStatus.ERROR
            return []

    async def _process_push_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process a 'push' event."""
        processed_items = []
        repo_name = payload.get("repository", {}).get("full_name")
        for commit in payload.get("commits", []):
            commit_id = commit.get("id")
            if not commit_id:
                continue

            processed_items.append(
                ProcessedContent(
                    id=f"github:push:{repo_name}:{commit_id}",
                    content=commit.get("message", ""),
                    content_type=ContentType.TEXT,
                    source=commit.get("url"),
                    metadata={
                        "author": commit.get("author", {}).get("name"),
                        "repository": repo_name,
                        "ref": payload.get("ref"),
                    },
                    timestamp=datetime.fromisoformat(commit.get("timestamp")) if commit.get("timestamp") else datetime.utcnow(),
                    raw_data=commit,
                )
            )
        logger.info(f"Processed {len(processed_items)} commits from push event for {repo_name}.")
        return processed_items

    async def _process_pull_request_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process a 'pull_request' event."""
        pr = payload.get("pull_request", {})
        repo_name = payload.get("repository", {}).get("full_name")
        pr_id = pr.get("id")
        if not pr_id:
            return []
            
        action = payload.get("action")
        title = pr.get("title", "")
        body = pr.get("body", "")
        content = f"Title: {title}\n\n{body}"

        processed_item = ProcessedContent(
            id=f"github:pull_request:{repo_name}:{pr_id}",
            content=content,
            content_type=ContentType.MARKDOWN,
            source=pr.get("html_url"),
            metadata={
                "action": action,
                "repository": repo_name,
                "user": pr.get("user", {}).get("login"),
                "number": pr.get("number"),
                "state": pr.get("state"),
            },
            timestamp=datetime.fromisoformat(pr.get("updated_at")) if pr.get("updated_at") else datetime.utcnow(),
            raw_data=payload,
        )
        logger.info(f"Processed pull request event: {action} for {repo_name} #{pr.get('number')}.")
        return [processed_item]

    async def _process_issues_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process an 'issues' event."""
        issue = payload.get("issue", {})
        repo_name = payload.get("repository", {}).get("full_name")
        issue_id = issue.get("id")
        if not issue_id:
            return []

        action = payload.get("action")
        title = issue.get("title", "")
        body = issue.get("body", "")
        content = f"Title: {title}\n\n{body}"

        processed_item = ProcessedContent(
            id=f"github:issue:{repo_name}:{issue_id}",
            content=content,
            content_type=ContentType.MARKDOWN,
            source=issue.get("html_url"),
            metadata={
                "action": action,
                "repository": repo_name,
                "user": issue.get("user", {}).get("login"),
                "number": issue.get("number"),
                "state": issue.get("state"),
            },
            timestamp=datetime.fromisoformat(issue.get("updated_at")) if issue.get("updated_at") else datetime.utcnow(),
            raw_data=payload,
        )
        logger.info(f"Processed issue event: {action} for {repo_name} #{issue.get('number')}.")
        return [processed_item]
