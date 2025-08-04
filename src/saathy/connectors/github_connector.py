import logging
from datetime import datetime
from typing import Any

from saathy.connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ContentType,
    ProcessedContent,
)

logger = logging.getLogger(__name__)


class GithubConnector(BaseConnector):
    """Connector for GitHub to process webhook events."""

    def __init__(self, name: str, config: dict[str, Any]):
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

    async def process_event(self, event_data: dict[str, Any]) -> list[ProcessedContent]:
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
            logger.error(
                f"Error processing GitHub event '{event_type}': {e}", exc_info=True
            )
            self.status = ConnectorStatus.ERROR
            return []

    async def _process_push_event(
        self, payload: dict[str, Any]
    ) -> list[ProcessedContent]:
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
                    timestamp=datetime.fromisoformat(commit.get("timestamp"))
                    if commit.get("timestamp")
                    else datetime.utcnow(),
                    raw_data=commit,
                )
            )
        logger.info(
            f"Processed {len(processed_items)} commits from push event for {repo_name}."
        )
        return processed_items

    async def _process_pull_request_event(
        self, payload: dict[str, Any]
    ) -> list[ProcessedContent]:
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
            timestamp=datetime.fromisoformat(pr.get("updated_at"))
            if pr.get("updated_at")
            else datetime.utcnow(),
            raw_data=payload,
        )
        logger.info(
            f"Processed pull request event: {action} for {repo_name} #{pr.get('number')}."
        )
        return [processed_item]

    async def _process_issues_event(
        self, payload: dict[str, Any]
    ) -> list[ProcessedContent]:
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
            timestamp=datetime.fromisoformat(issue.get("updated_at"))
            if issue.get("updated_at")
            else datetime.utcnow(),
            raw_data=payload,
        )
        logger.info(
            f"Processed issue event: {action} for {repo_name} #{issue.get('number')}."
        )
        return [processed_item]

    def extract_commit_content(
        self, commit_data: dict[str, Any]
    ) -> list[ProcessedContent]:
        """Extract content from commit events."""
        processed_items = []
        repo_name = commit_data.get("repository", {}).get("full_name", "unknown")

        for commit in commit_data.get("commits", []):
            commit_id = commit.get("id")
            if not commit_id:
                continue

            # Extract commit message
            commit_message = commit.get("message", "")
            if commit_message:
                processed_items.append(
                    ProcessedContent(
                        id=f"github:commit:{repo_name}:{commit_id}:message",
                        content=commit_message,
                        content_type=ContentType.TEXT,
                        source=commit.get("url", ""),
                        metadata={
                            "event_type": "commit",
                            "repository": repo_name,
                            "commit_sha": commit_id,
                            "author": commit.get("author", {}).get("name"),
                            "author_email": commit.get("author", {}).get("email"),
                            "ref": commit_data.get("ref"),
                            "branch": commit_data.get("ref", "").replace(
                                "refs/heads/", ""
                            ),
                            "timestamp": commit.get("timestamp"),
                        },
                        timestamp=datetime.fromisoformat(commit.get("timestamp"))
                        if commit.get("timestamp")
                        else datetime.utcnow(),
                        raw_data=commit,
                    )
                )

            # Extract file changes if available
            for file_change in commit.get("added", []):
                processed_items.append(
                    ProcessedContent(
                        id=f"github:commit:{repo_name}:{commit_id}:added:{file_change}",
                        content=f"Added file: {file_change}",
                        content_type=ContentType.TEXT,
                        source=commit.get("url", ""),
                        metadata={
                            "event_type": "commit_file_change",
                            "repository": repo_name,
                            "commit_sha": commit_id,
                            "change_type": "added",
                            "file_path": file_change,
                            "author": commit.get("author", {}).get("name"),
                            "ref": commit_data.get("ref"),
                        },
                        timestamp=datetime.fromisoformat(commit.get("timestamp"))
                        if commit.get("timestamp")
                        else datetime.utcnow(),
                        raw_data={"commit": commit, "file": file_change},
                    )
                )

            for file_change in commit.get("modified", []):
                processed_items.append(
                    ProcessedContent(
                        id=f"github:commit:{repo_name}:{commit_id}:modified:{file_change}",
                        content=f"Modified file: {file_change}",
                        content_type=ContentType.TEXT,
                        source=commit.get("url", ""),
                        metadata={
                            "event_type": "commit_file_change",
                            "repository": repo_name,
                            "commit_sha": commit_id,
                            "change_type": "modified",
                            "file_path": file_change,
                            "author": commit.get("author", {}).get("name"),
                            "ref": commit_data.get("ref"),
                        },
                        timestamp=datetime.fromisoformat(commit.get("timestamp"))
                        if commit.get("timestamp")
                        else datetime.utcnow(),
                        raw_data={"commit": commit, "file": file_change},
                    )
                )

        logger.info(
            f"Extracted {len(processed_items)} content items from commit data for {repo_name}"
        )
        return processed_items

    def extract_pr_content(self, pr_data: dict[str, Any]) -> list[ProcessedContent]:
        """Extract content from pull request events."""
        processed_items = []
        pr = pr_data.get("pull_request", {})
        repo_name = pr_data.get("repository", {}).get("full_name", "unknown")
        pr_id = pr.get("id")
        pr_number = pr.get("number")

        if not pr_id:
            return processed_items

        # Extract PR title and description
        title = pr.get("title", "")
        body = pr.get("body", "")

        if title:
            processed_items.append(
                ProcessedContent(
                    id=f"github:pr:{repo_name}:{pr_id}:title",
                    content=title,
                    content_type=ContentType.TEXT,
                    source=pr.get("html_url", ""),
                    metadata={
                        "event_type": "pull_request",
                        "repository": repo_name,
                        "pr_number": pr_number,
                        "pr_id": pr_id,
                        "action": pr_data.get("action"),
                        "state": pr.get("state"),
                        "user": pr.get("user", {}).get("login"),
                        "title": title,
                    },
                    timestamp=datetime.fromisoformat(pr.get("updated_at"))
                    if pr.get("updated_at")
                    else datetime.utcnow(),
                    raw_data=pr,
                )
            )

        if body:
            processed_items.append(
                ProcessedContent(
                    id=f"github:pr:{repo_name}:{pr_id}:body",
                    content=body,
                    content_type=ContentType.MARKDOWN,
                    source=pr.get("html_url", ""),
                    metadata={
                        "event_type": "pull_request",
                        "repository": repo_name,
                        "pr_number": pr_number,
                        "pr_id": pr_id,
                        "action": pr_data.get("action"),
                        "state": pr.get("state"),
                        "user": pr.get("user", {}).get("login"),
                        "title": title,
                    },
                    timestamp=datetime.fromisoformat(pr.get("updated_at"))
                    if pr.get("updated_at")
                    else datetime.utcnow(),
                    raw_data=pr,
                )
            )

        # Extract comments if available
        for comment in pr.get("comments", []):
            comment_id = comment.get("id")
            if comment_id:
                processed_items.append(
                    ProcessedContent(
                        id=f"github:pr:{repo_name}:{pr_id}:comment:{comment_id}",
                        content=comment.get("body", ""),
                        content_type=ContentType.MARKDOWN,
                        source=comment.get("html_url", ""),
                        metadata={
                            "event_type": "pull_request_comment",
                            "repository": repo_name,
                            "pr_number": pr_number,
                            "pr_id": pr_id,
                            "comment_id": comment_id,
                            "user": comment.get("user", {}).get("login"),
                            "created_at": comment.get("created_at"),
                        },
                        timestamp=datetime.fromisoformat(comment.get("created_at"))
                        if comment.get("created_at")
                        else datetime.utcnow(),
                        raw_data=comment,
                    )
                )

        logger.info(
            f"Extracted {len(processed_items)} content items from PR data for {repo_name} #{pr_number}"
        )
        return processed_items

    def extract_issue_content(
        self, issue_data: dict[str, Any]
    ) -> list[ProcessedContent]:
        """Extract content from issue events."""
        processed_items = []
        issue = issue_data.get("issue", {})
        repo_name = issue_data.get("repository", {}).get("full_name", "unknown")
        issue_id = issue.get("id")
        issue_number = issue.get("number")

        if not issue_id:
            return processed_items

        # Extract issue title and body
        title = issue.get("title", "")
        body = issue.get("body", "")

        if title:
            processed_items.append(
                ProcessedContent(
                    id=f"github:issue:{repo_name}:{issue_id}:title",
                    content=title,
                    content_type=ContentType.TEXT,
                    source=issue.get("html_url", ""),
                    metadata={
                        "event_type": "issue",
                        "repository": repo_name,
                        "issue_number": issue_number,
                        "issue_id": issue_id,
                        "action": issue_data.get("action"),
                        "state": issue.get("state"),
                        "user": issue.get("user", {}).get("login"),
                        "labels": [
                            label.get("name") for label in issue.get("labels", [])
                        ],
                        "title": title,
                    },
                    timestamp=datetime.fromisoformat(issue.get("updated_at"))
                    if issue.get("updated_at")
                    else datetime.utcnow(),
                    raw_data=issue,
                )
            )

        if body:
            processed_items.append(
                ProcessedContent(
                    id=f"github:issue:{repo_name}:{issue_id}:body",
                    content=body,
                    content_type=ContentType.MARKDOWN,
                    source=issue.get("html_url", ""),
                    metadata={
                        "event_type": "issue",
                        "repository": repo_name,
                        "issue_number": issue_number,
                        "issue_id": issue_id,
                        "action": issue_data.get("action"),
                        "state": issue.get("state"),
                        "user": issue.get("user", {}).get("login"),
                        "labels": [
                            label.get("name") for label in issue.get("labels", [])
                        ],
                        "title": title,
                    },
                    timestamp=datetime.fromisoformat(issue.get("updated_at"))
                    if issue.get("updated_at")
                    else datetime.utcnow(),
                    raw_data=issue,
                )
            )

        # Extract comments if available
        for comment in issue.get("comments", []):
            comment_id = comment.get("id")
            if comment_id:
                processed_items.append(
                    ProcessedContent(
                        id=f"github:issue:{repo_name}:{issue_id}:comment:{comment_id}",
                        content=comment.get("body", ""),
                        content_type=ContentType.MARKDOWN,
                        source=comment.get("html_url", ""),
                        metadata={
                            "event_type": "issue_comment",
                            "repository": repo_name,
                            "issue_number": issue_number,
                            "issue_id": issue_id,
                            "comment_id": comment_id,
                            "user": comment.get("user", {}).get("login"),
                            "created_at": comment.get("created_at"),
                        },
                        timestamp=datetime.fromisoformat(comment.get("created_at"))
                        if comment.get("created_at")
                        else datetime.utcnow(),
                        raw_data=comment,
                    )
                )

        logger.info(
            f"Extracted {len(processed_items)} content items from issue data for {repo_name} #{issue_number}"
        )
        return processed_items
