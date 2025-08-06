"""GitHub webhook processor for real-time repository events."""

import hashlib
import hmac
import logging
import re
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from .event_manager import EventManager
from .models.events import EventType, GitHubEvent

logger = logging.getLogger(__name__)


class GitHubWebhookProcessor:
    """Processes GitHub webhook events and converts them to standardized format."""

    def __init__(self, webhook_secret: str, event_manager: EventManager):
        """Initialize GitHub webhook processor."""
        self.webhook_secret = webhook_secret
        self.event_manager = event_manager

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature for security."""
        if not signature:
            logger.warning("No signature provided for GitHub webhook")
            return False

        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode("utf-8"), payload, hashlib.sha256
            ).hexdigest()

            # GitHub signature format: sha256=<hash>
            signature_hash = signature.replace("sha256=", "")

            return hmac.compare_digest(expected_signature, signature_hash)

        except Exception as e:
            logger.error(f"Error verifying GitHub webhook signature: {e}")
            return False

    async def process_webhook(
        self, payload: dict[str, Any], event_type: str, delivery_id: str
    ) -> dict[str, str]:
        """Process incoming GitHub webhook events."""
        try:
            logger.info(
                f"Processing GitHub webhook: {event_type} (delivery: {delivery_id})"
            )

            if event_type == "push":
                await self.handle_push_event(payload)
            elif event_type == "pull_request":
                await self.handle_pr_event(payload)
            elif event_type == "issues":
                await self.handle_issue_event(payload)
            elif event_type == "issue_comment":
                await self.handle_comment_event(payload)
            elif event_type == "pull_request_review":
                await self.handle_pr_review_event(payload)
            elif event_type == "pull_request_review_comment":
                await self.handle_pr_review_comment_event(payload)
            elif event_type == "ping":
                logger.info("GitHub webhook ping received")
                return {"status": "pong", "message": "Webhook active"}
            else:
                logger.info(f"Ignoring GitHub event type: {event_type}")

            return {"status": "processed", "event_type": event_type}

        except Exception as e:
            logger.error(f"Error processing GitHub webhook {event_type}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Webhook processing failed: {str(e)}"
            ) from e

    async def handle_push_event(self, payload: dict[str, Any]):
        """Handle git push events."""
        try:
            commits = payload.get("commits", [])
            if not commits:
                logger.debug("Push event has no commits, skipping")
                return

            repository = payload.get("repository", {}).get("name", "unknown")
            full_name = payload.get("repository", {}).get("full_name", repository)
            pusher = payload.get("pusher", {}).get("name", "unknown")
            branch = payload.get("ref", "").replace("refs/heads/", "")

            # Process each commit
            for commit in commits:
                commit_message = commit.get("message", "")
                commit_sha = commit.get("id", "")
                author = commit.get("author", {}).get("username", pusher)
                timestamp_str = commit.get("timestamp")

                if not timestamp_str:
                    timestamp = datetime.now()
                else:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )

                # Get files changed
                files_changed = []
                for file_info in commit.get("modified", []):
                    files_changed.append(file_info)
                for file_info in commit.get("added", []):
                    files_changed.append(file_info)
                for file_info in commit.get("removed", []):
                    files_changed.append(file_info)

                # Extract information for correlation
                mentioned_users = self.extract_github_mentions(commit_message)
                keywords = self.extract_commit_keywords(
                    commit_message, files_changed, branch
                )
                urgency_score = self.calculate_commit_urgency(
                    commit_message, files_changed, branch
                )

                github_event = GitHubEvent(
                    event_id=f"github_{repository}_{commit_sha[:12]}",
                    event_type=EventType.GITHUB_PUSH,
                    timestamp=timestamp,
                    user_id=author,
                    platform="github",
                    raw_data=payload,
                    mentioned_users=mentioned_users,
                    keywords=keywords,
                    project_context=repository,
                    urgency_score=urgency_score,
                    repository=full_name,
                    action="pushed",
                    branch=branch,
                    commit_sha=commit_sha,
                    files_changed=files_changed,
                    commit_message=commit_message,
                )

                await self.event_manager.process_event(github_event)
                logger.debug(
                    f"Processed push event for commit {commit_sha[:8]} in {repository}"
                )

        except Exception as e:
            logger.error(f"Error processing push event: {e}")

    async def handle_pr_event(self, payload: dict[str, Any]):
        """Handle pull request events."""
        try:
            action = payload.get("action")  # opened, closed, synchronized, etc.
            pr_data = payload.get("pull_request", {})
            repository = payload.get("repository", {}).get("name", "unknown")
            full_name = payload.get("repository", {}).get("full_name", repository)

            pr_number = pr_data.get("number")
            pr_title = pr_data.get("title", "")
            pr_body = pr_data.get("body", "") or ""
            author = pr_data.get("user", {}).get("login", "unknown")
            updated_at = pr_data.get("updated_at")

            # Convert timestamp
            if updated_at:
                timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            # Combine title and body for analysis
            pr_text = f"{pr_title}\n{pr_body}"

            # Get changed files if available
            files_changed = []
            if "commits" in payload:
                # Some webhook payloads include commit info
                for commit in payload["commits"]:
                    files_changed.extend(commit.get("modified", []))
                    files_changed.extend(commit.get("added", []))

            mentioned_users = self.extract_github_mentions(pr_text)
            keywords = self.extract_pr_keywords(pr_text, action)
            urgency_score = self.calculate_pr_urgency(pr_text, action, pr_data)

            github_event = GitHubEvent(
                event_id=f"github_{repository}_pr_{pr_number}_{action}_{int(timestamp.timestamp())}",
                event_type=EventType.GITHUB_PR,
                timestamp=timestamp,
                user_id=author,
                platform="github",
                raw_data=payload,
                mentioned_users=mentioned_users,
                keywords=keywords,
                project_context=repository,
                urgency_score=urgency_score,
                repository=full_name,
                action=action,
                pr_number=pr_number,
                files_changed=files_changed,
            )

            await self.event_manager.process_event(github_event)
            logger.debug(
                f"Processed PR {action} event for #{pr_number} in {repository}"
            )

        except Exception as e:
            logger.error(f"Error processing PR event: {e}")

    async def handle_issue_event(self, payload: dict[str, Any]):
        """Handle GitHub issue events."""
        try:
            action = payload.get("action")  # opened, closed, edited, etc.
            issue_data = payload.get("issue", {})
            repository = payload.get("repository", {}).get("name", "unknown")
            full_name = payload.get("repository", {}).get("full_name", repository)

            issue_number = issue_data.get("number")
            issue_title = issue_data.get("title", "")
            issue_body = issue_data.get("body", "") or ""
            author = issue_data.get("user", {}).get("login", "unknown")
            updated_at = issue_data.get("updated_at")

            if updated_at:
                timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            # Combine title and body for analysis
            issue_text = f"{issue_title}\n{issue_body}"

            mentioned_users = self.extract_github_mentions(issue_text)
            keywords = self.extract_issue_keywords(issue_text, action, issue_data)
            urgency_score = self.calculate_issue_urgency(issue_text, action, issue_data)

            github_event = GitHubEvent(
                event_id=f"github_{repository}_issue_{issue_number}_{action}_{int(timestamp.timestamp())}",
                event_type=EventType.GITHUB_ISSUE,
                timestamp=timestamp,
                user_id=author,
                platform="github",
                raw_data=payload,
                mentioned_users=mentioned_users,
                keywords=keywords,
                project_context=repository,
                urgency_score=urgency_score,
                repository=full_name,
                action=action,
                issue_number=issue_number,
            )

            await self.event_manager.process_event(github_event)
            logger.debug(
                f"Processed issue {action} event for #{issue_number} in {repository}"
            )

        except Exception as e:
            logger.error(f"Error processing issue event: {e}")

    async def handle_comment_event(self, payload: dict[str, Any]):
        """Handle issue and PR comment events."""
        try:
            action = payload.get("action")  # created, edited, deleted
            comment_data = payload.get("comment", {})
            repository = payload.get("repository", {}).get("name", "unknown")
            full_name = payload.get("repository", {}).get("full_name", repository)

            comment_body = comment_data.get("body", "")
            author = comment_data.get("user", {}).get("login", "unknown")
            updated_at = comment_data.get("updated_at")

            if updated_at:
                timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            # Determine if it's an issue or PR comment
            issue_or_pr = payload.get("issue", {})
            is_pr = "pull_request" in issue_or_pr
            number = issue_or_pr.get("number")

            mentioned_users = self.extract_github_mentions(comment_body)
            keywords = self.extract_comment_keywords(comment_body, is_pr)
            urgency_score = self.calculate_comment_urgency(comment_body, is_pr)

            github_event = GitHubEvent(
                event_id=f"github_{repository}_comment_{comment_data.get('id')}_{action}",
                event_type=EventType.GITHUB_COMMENT,
                timestamp=timestamp,
                user_id=author,
                platform="github",
                raw_data=payload,
                mentioned_users=mentioned_users,
                keywords=keywords,
                project_context=repository,
                urgency_score=urgency_score,
                repository=full_name,
                action=action,
                pr_number=number if is_pr else None,
                issue_number=number if not is_pr else None,
            )

            await self.event_manager.process_event(github_event)
            logger.debug(f"Processed comment {action} event in {repository}")

        except Exception as e:
            logger.error(f"Error processing comment event: {e}")

    async def handle_pr_review_event(self, payload: dict[str, Any]):
        """Handle pull request review events."""
        try:
            action = payload.get("action")  # submitted, edited, dismissed
            review_data = payload.get("review", {})
            pr_data = payload.get("pull_request", {})
            repository = payload.get("repository", {}).get("name", "unknown")
            full_name = payload.get("repository", {}).get("full_name", repository)

            review_body = review_data.get("body", "") or ""
            reviewer = review_data.get("user", {}).get("login", "unknown")
            pr_number = pr_data.get("number")
            review_state = review_data.get(
                "state", ""
            )  # approved, changes_requested, commented

            submitted_at = review_data.get("submitted_at")
            if submitted_at:
                timestamp = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            mentioned_users = self.extract_github_mentions(review_body)
            keywords = ["review", review_state.lower()] + self.extract_github_mentions(
                review_body
            )
            urgency_score = self.calculate_review_urgency(review_state, review_body)

            github_event = GitHubEvent(
                event_id=f"github_{repository}_review_{review_data.get('id')}_{action}",
                event_type=EventType.GITHUB_COMMENT,  # Reviews are a type of comment
                timestamp=timestamp,
                user_id=reviewer,
                platform="github",
                raw_data=payload,
                mentioned_users=mentioned_users,
                keywords=keywords,
                project_context=repository,
                urgency_score=urgency_score,
                repository=full_name,
                action=f"review_{action}",
                pr_number=pr_number,
            )

            await self.event_manager.process_event(github_event)
            logger.debug(
                f"Processed review {action} event for PR #{pr_number} in {repository}"
            )

        except Exception as e:
            logger.error(f"Error processing PR review event: {e}")

    async def handle_pr_review_comment_event(self, payload: dict[str, Any]):
        """Handle pull request review comment events."""
        # Similar to regular comments but specifically for code reviews
        await self.handle_comment_event(payload)

    def extract_github_mentions(self, text: str) -> list[str]:
        """Extract @mentions from GitHub text."""
        # GitHub format: @username
        mentions = re.findall(
            r"@([a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38})", text
        )
        return mentions

    def extract_commit_keywords(
        self, message: str, files: list[str], branch: str
    ) -> list[str]:
        """Extract keywords from commit message and context."""
        keywords = []
        message_lower = message.lower()

        # Conventional commit prefixes
        commit_keywords = [
            "fix",
            "feat",
            "docs",
            "style",
            "refactor",
            "test",
            "chore",
            "bug",
            "hotfix",
            "release",
            "merge",
            "revert",
            "perf",
            "build",
        ]

        for keyword in commit_keywords:
            if keyword in message_lower or message_lower.startswith(f"{keyword}:"):
                keywords.append(keyword)

        # File-based keywords
        for file_path in files:
            file_lower = file_path.lower()
            if any(
                ext in file_lower
                for ext in [".py", ".js", ".ts", ".go", ".java", ".rb"]
            ):
                keywords.append("code")
            elif any(ext in file_lower for ext in [".md", ".txt", ".rst", ".adoc"]):
                keywords.append("docs")
            elif any(
                ext in file_lower for ext in [".json", ".yaml", ".yml", ".toml", ".ini"]
            ):
                keywords.append("config")
            elif any(ext in file_lower for ext in [".sql", ".db"]):
                keywords.append("database")
            elif any(
                name in file_lower
                for name in ["dockerfile", "docker-compose", ".docker"]
            ):
                keywords.append("docker")

        # Branch-based keywords
        branch_lower = branch.lower()
        if any(word in branch_lower for word in ["feature", "feat"]):
            keywords.append("feature")
        elif any(word in branch_lower for word in ["fix", "bug", "hotfix"]):
            keywords.append("fix")
        elif any(word in branch_lower for word in ["release", "rel"]):
            keywords.append("release")

        return keywords

    def extract_pr_keywords(self, text: str, action: str) -> list[str]:
        """Extract keywords from PR title/body."""
        keywords = [action]  # opened, closed, etc.
        text_lower = text.lower()

        pr_keywords = [
            "feature",
            "bug",
            "fix",
            "docs",
            "refactor",
            "test",
            "security",
            "performance",
            "ui",
            "api",
            "database",
            "migration",
            "breaking",
            "wip",
            "draft",
            "ready",
            "urgent",
        ]

        for keyword in pr_keywords:
            if keyword in text_lower:
                keywords.append(keyword)

        # Look for issue references
        issue_refs = re.findall(r"#(\d+)", text)
        if issue_refs:
            keywords.append("references_issue")

        # Look for closing keywords
        closing_keywords = ["fixes", "closes", "resolves", "fix", "close", "resolve"]
        for keyword in closing_keywords:
            if f"{keyword} #" in text_lower:
                keywords.append("closes_issue")
                break

        return keywords

    def extract_issue_keywords(
        self, text: str, action: str, issue_data: dict[str, Any]
    ) -> list[str]:
        """Extract keywords from issue title/body."""
        keywords = [action, "issue"]
        text_lower = text.lower()

        # Check labels
        labels = issue_data.get("labels", [])
        for label in labels:
            label_name = label.get("name", "").lower()
            keywords.append(label_name)

        # Issue type keywords
        issue_keywords = [
            "bug",
            "feature",
            "enhancement",
            "question",
            "help",
            "documentation",
            "good first issue",
            "urgent",
            "critical",
            "blocked",
        ]

        for keyword in issue_keywords:
            if keyword in text_lower:
                keywords.append(keyword)

        return keywords

    def extract_comment_keywords(self, text: str, is_pr: bool) -> list[str]:
        """Extract keywords from comments."""
        keywords = ["comment"]
        if is_pr:
            keywords.append("pr_comment")
        else:
            keywords.append("issue_comment")

        text_lower = text.lower()

        # Review-specific keywords
        review_keywords = [
            "lgtm",
            "looks good",
            "approved",
            "changes requested",
            "needs work",
            "question",
            "suggestion",
            "nit",
        ]

        for keyword in review_keywords:
            if keyword in text_lower:
                keywords.append(keyword.replace(" ", "_"))

        return keywords

    def calculate_commit_urgency(
        self, message: str, files: list[str], branch: str
    ) -> float:
        """Calculate urgency for commits."""
        score = 0.0
        message_lower = message.lower()

        # Urgent commit keywords
        if any(
            word in message_lower
            for word in ["hotfix", "urgent", "critical", "security", "emergency"]
        ):
            score += 0.5

        # Production/main branch
        if branch.lower() in ["main", "master", "production", "prod"]:
            score += 0.2

        # Breaking changes
        if "breaking" in message_lower or "BREAKING CHANGE" in message:
            score += 0.3

        # Production files
        prod_indicators = ["prod", "production", "config", ".env"]
        if any(indicator in f.lower() for f in files for indicator in prod_indicators):
            score += 0.2

        # Database changes
        if any(".sql" in f.lower() or "migration" in f.lower() for f in files):
            score += 0.15

        return min(score, 1.0)

    def calculate_pr_urgency(
        self, text: str, action: str, pr_data: dict[str, Any]
    ) -> float:
        """Calculate urgency for PRs."""
        score = 0.0
        text_lower = text.lower()

        if action == "opened":
            score += 0.1  # New PRs need attention
        elif action == "review_requested":
            score += 0.3  # Reviews are time-sensitive
        elif action == "ready_for_review":
            score += 0.25

        # Check for urgent keywords
        if any(
            word in text_lower
            for word in ["urgent", "hotfix", "security", "critical", "emergency"]
        ):
            score += 0.4

        # Check labels
        labels = pr_data.get("labels", [])
        urgent_labels = ["urgent", "critical", "hotfix", "security", "breaking"]
        for label in labels:
            if label.get("name", "").lower() in urgent_labels:
                score += 0.3
                break

        # Draft PRs are less urgent
        if pr_data.get("draft", False):
            score *= 0.5

        return min(score, 1.0)

    def calculate_issue_urgency(
        self, text: str, action: str, issue_data: dict[str, Any]
    ) -> float:
        """Calculate urgency for issues."""
        score = 0.0
        text_lower = text.lower()

        if action == "opened":
            score += 0.2  # New issues need triage

        # Check for urgent keywords
        if any(
            word in text_lower
            for word in ["urgent", "critical", "emergency", "blocking", "broken"]
        ):
            score += 0.4

        # Check labels
        labels = issue_data.get("labels", [])
        urgent_labels = ["urgent", "critical", "bug", "security", "blocking"]
        for label in labels:
            if label.get("name", "").lower() in urgent_labels:
                score += 0.3
                break

        return min(score, 1.0)

    def calculate_comment_urgency(self, text: str, is_pr: bool) -> float:
        """Calculate urgency for comments."""
        score = 0.1  # Base score for comments
        text_lower = text.lower()

        # Review-specific urgency
        if is_pr:
            if any(
                phrase in text_lower
                for phrase in ["changes requested", "needs work", "blocking"]
            ):
                score += 0.3
            elif any(
                phrase in text_lower for phrase in ["lgtm", "approved", "looks good"]
            ):
                score += 0.2

        # General urgent indicators
        if any(
            word in text_lower for word in ["urgent", "asap", "critical", "important"]
        ):
            score += 0.3

        return min(score, 1.0)

    def calculate_review_urgency(self, review_state: str, review_body: str) -> float:
        """Calculate urgency for PR reviews."""
        score = 0.2  # Base score for reviews

        if review_state == "changes_requested":
            score += 0.3  # Blocking
        elif review_state == "approved":
            score += 0.25  # Can proceed

        body_lower = review_body.lower()
        if any(word in body_lower for word in ["urgent", "critical", "blocking"]):
            score += 0.3

        return min(score, 1.0)
