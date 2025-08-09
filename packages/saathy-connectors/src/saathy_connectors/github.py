"""GitHub connector implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from github import Github, GithubException

from saathy_core import ContentType, ProcessedContent, ProcessingStatus
from .base import BaseConnector

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """Connector for GitHub integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("github", config)
        self.token = config.get("token")
        self.owner = config.get("owner")
        self.repo = config.get("repo")
        self.webhook_secret = config.get("webhook_secret")
        self._client: Optional[Github] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def validate_config(self) -> bool:
        """Validate GitHub configuration."""
        if not self.token:
            self.logger.error("GitHub token not provided")
            return False
        
        if not self.owner or not self.repo:
            self.logger.error("GitHub owner and repo must be specified")
            return False
        
        return True
    
    async def _start_connector(self) -> None:
        """Start the GitHub connector."""
        # Initialize GitHub client
        self._client = Github(self.token)
        self._session = aiohttp.ClientSession()
        
        # Test connection
        try:
            user = self._client.get_user()
            self.logger.info(f"Connected to GitHub as {user.login}")
        except GithubException as e:
            raise ValueError(f"Failed to connect to GitHub: {e}")
    
    async def _stop_connector(self) -> None:
        """Stop the GitHub connector."""
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._client:
            self._client.close()
            self._client = None
    
    async def _process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Process GitHub webhook event."""
        event_type = event_data.get("event_type")
        payload = event_data.get("payload", {})
        
        processors = {
            "push": self._process_push_event,
            "pull_request": self._process_pr_event,
            "issues": self._process_issue_event,
            "issue_comment": self._process_comment_event,
            "pull_request_review": self._process_review_event,
        }
        
        processor = processors.get(event_type)
        if not processor:
            self.logger.warning(f"Unsupported event type: {event_type}")
            return []
        
        return await processor(payload)
    
    async def _process_push_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process push event."""
        contents = []
        
        repo_name = payload.get("repository", {}).get("full_name", "")
        pusher = payload.get("pusher", {}).get("name", "unknown")
        commits = payload.get("commits", [])
        
        for commit in commits:
            content = ProcessedContent(
                content_type=ContentType.CODE,
                title=f"Commit by {commit.get('author', {}).get('name', pusher)}",
                content=commit.get("message", ""),
                source=f"github:{repo_name}",
                source_id=commit.get("id", ""),
                metadata={
                    "event_type": "push",
                    "commit_id": commit.get("id"),
                    "author": commit.get("author", {}),
                    "timestamp": commit.get("timestamp"),
                    "url": commit.get("url"),
                    "added": commit.get("added", []),
                    "removed": commit.get("removed", []),
                    "modified": commit.get("modified", []),
                },
                timestamp=datetime.utcnow(),
                processing_status=ProcessingStatus.COMPLETED,
            )
            contents.append(content)
        
        return contents
    
    async def _process_pr_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process pull request event."""
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        
        content = ProcessedContent(
            content_type=ContentType.ISSUE,
            title=f"PR {action}: {pr.get('title', '')}",
            content=pr.get("body", ""),
            source=f"github:{repo.get('full_name', '')}",
            source_id=f"pr-{pr.get('number', '')}",
            metadata={
                "event_type": "pull_request",
                "action": action,
                "pr_number": pr.get("number"),
                "author": pr.get("user", {}).get("login"),
                "state": pr.get("state"),
                "merged": pr.get("merged"),
                "url": pr.get("html_url"),
                "created_at": pr.get("created_at"),
                "updated_at": pr.get("updated_at"),
            },
            timestamp=datetime.utcnow(),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        return [content]
    
    async def _process_issue_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process issue event."""
        action = payload.get("action")
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        
        content = ProcessedContent(
            content_type=ContentType.ISSUE,
            title=f"Issue {action}: {issue.get('title', '')}",
            content=issue.get("body", ""),
            source=f"github:{repo.get('full_name', '')}",
            source_id=f"issue-{issue.get('number', '')}",
            metadata={
                "event_type": "issues",
                "action": action,
                "issue_number": issue.get("number"),
                "author": issue.get("user", {}).get("login"),
                "state": issue.get("state"),
                "labels": [label.get("name") for label in issue.get("labels", [])],
                "url": issue.get("html_url"),
                "created_at": issue.get("created_at"),
                "updated_at": issue.get("updated_at"),
            },
            timestamp=datetime.utcnow(),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        return [content]
    
    async def _process_comment_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process issue comment event."""
        action = payload.get("action")
        comment = payload.get("comment", {})
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        
        content = ProcessedContent(
            content_type=ContentType.MESSAGE,
            title=f"Comment on: {issue.get('title', '')}",
            content=comment.get("body", ""),
            source=f"github:{repo.get('full_name', '')}",
            source_id=f"comment-{comment.get('id', '')}",
            metadata={
                "event_type": "issue_comment",
                "action": action,
                "issue_number": issue.get("number"),
                "comment_id": comment.get("id"),
                "author": comment.get("user", {}).get("login"),
                "url": comment.get("html_url"),
                "created_at": comment.get("created_at"),
                "updated_at": comment.get("updated_at"),
            },
            timestamp=datetime.utcnow(),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        return [content]
    
    async def _process_review_event(self, payload: Dict[str, Any]) -> List[ProcessedContent]:
        """Process pull request review event."""
        action = payload.get("action")
        review = payload.get("review", {})
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        
        content = ProcessedContent(
            content_type=ContentType.MESSAGE,
            title=f"PR Review: {pr.get('title', '')}",
            content=review.get("body", ""),
            source=f"github:{repo.get('full_name', '')}",
            source_id=f"review-{review.get('id', '')}",
            metadata={
                "event_type": "pull_request_review",
                "action": action,
                "pr_number": pr.get("number"),
                "review_id": review.get("id"),
                "author": review.get("user", {}).get("login"),
                "state": review.get("state"),
                "url": review.get("html_url"),
                "submitted_at": review.get("submitted_at"),
            },
            timestamp=datetime.utcnow(),
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        return [content]
    
    async def sync_repository(
        self,
        full_sync: bool = False,
        since: Optional[datetime] = None,
        limit: Optional[int] = 100
    ) -> Dict[str, Any]:
        """Sync repository data."""
        if not self._client:
            raise RuntimeError("GitHub client not initialized")
        
        results = {
            "contents": [],
            "commits": 0,
            "issues": 0,
            "pull_requests": 0,
        }
        
        try:
            repo = self._client.get_repo(f"{self.owner}/{self.repo}")
            
            # Sync commits
            if full_sync or not since:
                since = datetime.utcnow() - timedelta(days=7)
            
            commits = repo.get_commits(since=since)
            for commit in commits[:limit]:
                content = ProcessedContent(
                    content_type=ContentType.CODE,
                    title=f"Commit: {commit.commit.message.split('\\n')[0]}",
                    content=commit.commit.message,
                    source=f"github:{self.owner}/{self.repo}",
                    source_id=commit.sha,
                    metadata={
                        "sha": commit.sha,
                        "author": commit.commit.author.name,
                        "date": commit.commit.author.date.isoformat(),
                        "url": commit.html_url,
                    },
                    timestamp=commit.commit.author.date,
                    processing_status=ProcessingStatus.COMPLETED,
                )
                results["contents"].append(content)
                results["commits"] += 1
            
            # Sync issues
            issues = repo.get_issues(state="all", since=since)
            for issue in issues[:limit]:
                if not issue.pull_request:  # Skip PRs
                    content = ProcessedContent(
                        content_type=ContentType.ISSUE,
                        title=f"Issue #{issue.number}: {issue.title}",
                        content=issue.body or "",
                        source=f"github:{self.owner}/{self.repo}",
                        source_id=f"issue-{issue.number}",
                        metadata={
                            "number": issue.number,
                            "state": issue.state,
                            "author": issue.user.login,
                            "labels": [label.name for label in issue.labels],
                            "created_at": issue.created_at.isoformat(),
                            "updated_at": issue.updated_at.isoformat(),
                            "url": issue.html_url,
                        },
                        timestamp=issue.updated_at,
                        processing_status=ProcessingStatus.COMPLETED,
                    )
                    results["contents"].append(content)
                    results["issues"] += 1
            
            # Sync pull requests
            pulls = repo.get_pulls(state="all")
            for pr in pulls[:limit]:
                content = ProcessedContent(
                    content_type=ContentType.ISSUE,
                    title=f"PR #{pr.number}: {pr.title}",
                    content=pr.body or "",
                    source=f"github:{self.owner}/{self.repo}",
                    source_id=f"pr-{pr.number}",
                    metadata={
                        "number": pr.number,
                        "state": pr.state,
                        "author": pr.user.login,
                        "merged": pr.merged,
                        "created_at": pr.created_at.isoformat(),
                        "updated_at": pr.updated_at.isoformat(),
                        "url": pr.html_url,
                    },
                    timestamp=pr.updated_at,
                    processing_status=ProcessingStatus.COMPLETED,
                )
                results["contents"].append(content)
                results["pull_requests"] += 1
            
        except GithubException as e:
            self.logger.error(f"GitHub sync failed: {e}")
            raise
        
        return results