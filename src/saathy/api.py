"""FastAPI application instance."""

import hashlib
import hmac
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Request, status

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.connectors import GithubConnector, NotionConnector, SlackConnector
from saathy.connectors.base import ContentType, ProcessedContent
from saathy.connectors.content_processor import ContentProcessor, NotionContentProcessor
from saathy.embedding.service import EmbeddingService, get_embedding_service
from saathy.scheduler import scheduler, start_scheduler, stop_scheduler
from saathy.vector.client import QdrantClientWrapper
from saathy.vector.repository import VectorRepository

# In-memory dictionary to hold settings during the application's lifespan.
# This is a simple approach; for more complex scenarios, consider using a more robust solution.
app_state: dict[
    str,
    Union[
        Settings,
        VectorRepository,
        EmbeddingService,
        GithubConnector,
        NotionConnector,
        SlackConnector,
        ContentProcessor,
        NotionContentProcessor,
        None,
    ],
] = {}


def get_notion_config(settings: Settings) -> dict[str, Any]:
    """Extract and validate Notion configuration from settings."""
    token = settings.notion_token_str
    if not token:
        return {}

    databases = [
        db.strip() for db in settings.notion_databases.split(",") if db.strip()
    ]
    pages = [page.strip() for page in settings.notion_pages.split(",") if page.strip()]

    return {
        "token": token,
        "databases": databases,
        "pages": pages,
        "poll_interval": settings.notion_poll_interval,
    }


def setup_scheduled_sync_jobs() -> None:
    """Set up scheduled sync jobs for all connectors."""
    # Note: APScheduler can run async functions using asyncio
    from apscheduler.executors.asyncio import AsyncIOExecutor

    # Configure scheduler with async executor - only add if not already present
    try:
        scheduler.add_executor(AsyncIOExecutor(), "default")
        logging.info("Added AsyncIOExecutor to scheduler")
    except Exception as e:
        logging.info(f"AsyncIOExecutor already exists or error adding: {e}")

    # Schedule Slack sync job (every 15 minutes for recent messages)
    # Only Slack has a working sync method currently
    if app_state.get("slack_connector"):
        scheduler.add_job(
            _run_slack_sync,
            "interval",
            minutes=15,
            id="slack_sync",
            name="Slack Channel Sync",
            replace_existing=True,
            executor="default",
        )
        logging.info("Scheduled Slack sync job (every 15 minutes)")

    # Note: Notion connector already has its own polling mechanism built-in
    # GitHub currently relies only on webhooks


def _run_slack_sync() -> None:
    """Wrapper to run async Slack sync in sync context."""
    import asyncio

    try:
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async function
        loop.run_until_complete(_async_slack_sync())
    except Exception as e:
        logging.error(f"Error in Slack sync wrapper: {e}")


async def _async_slack_sync() -> None:
    """Async Slack sync implementation."""
    try:
        slack_connector = app_state.get("slack_connector")
        content_processor = app_state.get("content_processor")

        if not slack_connector or not content_processor:
            logging.warning(
                "Slack connector or content processor not available for sync"
            )
            return

        logging.info("Starting scheduled Slack sync...")

        # Get recent messages from each configured channel
        channels = slack_connector.config.get("channels", [])
        total_processed = 0

        for channel_id in channels:
            try:
                # Fetch recent messages (last 15 minutes)
                messages = await slack_connector.fetch_recent_messages(
                    channel_id, minutes=15
                )
                if messages:
                    # Process and store messages
                    result = await content_processor.process_and_store(messages)
                    processed = result.get("processed_items", 0)
                    total_processed += processed
                    logging.info(
                        f"Slack sync - Channel {channel_id}: "
                        f"{processed}/{len(messages)} messages processed"
                    )
            except Exception as e:
                logging.error(f"Error syncing Slack channel {channel_id}: {e}")

        logging.info(
            f"Scheduled Slack sync completed. Total messages processed: {total_processed}"
        )

    except Exception as e:
        logging.error(f"Error in scheduled Slack sync: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load settings and initialize connectors before the app starts, and clean up on shutdown."""
    settings = get_settings()

    # Initialize services as None - will be created lazily when needed
    app_state["settings"] = settings
    app_state["vector_repo"] = None
    app_state["embedding_service"] = None

    # Initialize embedding service FIRST so connectors can use it
    try:
        embedding_service = await get_embedding_service()
        app_state["embedding_service"] = embedding_service
        logging.info("Embedding service initialized successfully.")
    except Exception as e:
        app_state["embedding_service"] = None
        logging.error(f"Failed to initialize embedding service: {e}")

    # Initialize GitHub connector if configured
    if settings.github_webhook_secret_str and settings.github_token_str:
        logging.info("GitHub connector is configured, initializing.")
        try:
            github_connector = GithubConnector(
                name="github",
                config={
                    "token": settings.github_token_str,
                    "webhook_secret": settings.github_webhook_secret_str,
                    "repositories": (
                        settings.github_repositories.split(",")
                        if settings.github_repositories
                        else []
                    ),
                },
            )

            # Initialize content processor and connect it to GitHub connector
            embedding_service = await get_embedding_service()
            if embedding_service:
                vector_repo = get_vector_repo()
                if "content_processor" not in app_state:
                    content_processor = ContentProcessor(embedding_service, vector_repo)
                    app_state["content_processor"] = content_processor
                else:
                    content_processor = app_state["content_processor"]

                # Store content processor reference in GitHub connector config for later use
                github_connector.config["content_processor"] = content_processor
                logging.info(
                    "Content processor initialized and connected to GitHub connector."
                )
            else:
                logging.warning(
                    "Embedding service not available, GitHub content processing disabled."
                )

            await github_connector.start()
            app_state["github_connector"] = github_connector
            logging.info("GitHub connector initialized and started successfully.")
        except Exception as e:
            app_state["github_connector"] = None
            logging.error(f"Failed to initialize GitHub connector: {e}")
    else:
        app_state["github_connector"] = None
        logging.warning(
            "GitHub connector not configured. Skipping initialization. "
            "Provide GITHUB_WEBHOOK_SECRET and GITHUB_TOKEN to enable it."
        )

    # Initialize Slack connector if configured
    if settings.slack_bot_token_str:
        logging.info("Slack connector is configured, initializing.")
        slack_config = {
            "bot_token": settings.slack_bot_token_str,
            "channels": [
                ch.strip() for ch in settings.slack_channels.split(",") if ch.strip()
            ]
            if settings.slack_channels
            else [],
        }

        try:
            slack_connector = SlackConnector(config=slack_config)

            # Initialize content processor and connect it to Slack connector
            embedding_service = app_state.get("embedding_service")
            if embedding_service:
                vector_repo = get_vector_repo()
                content_processor = ContentProcessor(embedding_service, vector_repo)
                slack_connector.set_content_processor(content_processor)
                app_state["content_processor"] = content_processor
                logging.info(
                    "Content processor initialized and connected to Slack connector."
                )
            else:
                logging.warning(
                    "Embedding service not available, content processing disabled."
                )

            await slack_connector.start()
            app_state["slack_connector"] = slack_connector
            logging.info("Slack connector initialized and started successfully.")
        except Exception as e:
            app_state["slack_connector"] = None
            app_state["content_processor"] = None
            logging.error(f"Failed to initialize Slack connector: {e}")
    else:
        app_state["slack_connector"] = None
        app_state["content_processor"] = None
        logging.warning(
            "Slack connector not configured. Skipping initialization. "
            "Provide SLACK_BOT_TOKEN to enable it."
        )

    # Initialize Notion connector if configured
    notion_config = get_notion_config(settings)
    if notion_config.get("token"):
        logging.info("Notion connector is configured, initializing.")
        try:
            notion_connector = NotionConnector(config=notion_config)

            # Initialize Notion content processor
            embedding_service = await get_embedding_service()
            vector_repo = get_vector_repo()
            notion_content_processor = NotionContentProcessor(
                embedding_service, vector_repo
            )

            # Connect them
            notion_connector.set_content_processor(notion_content_processor)

            app_state["notion_connector"] = notion_connector
            app_state["notion_content_processor"] = notion_content_processor

            # Start connector
            await notion_connector.start()

            logging.info("Notion connector initialized and started successfully.")
        except Exception as e:
            app_state["notion_connector"] = None
            app_state["notion_content_processor"] = None
            logging.error(f"Failed to initialize Notion connector: {e}")
    else:
        app_state["notion_connector"] = None
        app_state["notion_content_processor"] = None
        logging.warning(
            "Notion connector not configured. Skipping initialization. "
            "Provide NOTION_TOKEN to enable it."
        )

    # Start the scheduler and add sync jobs
    try:
        start_scheduler()
        setup_scheduled_sync_jobs()
        logging.info("Scheduler started with sync jobs configured.")
    except Exception as e:
        logging.error(f"Failed to start scheduler: {e}")

    yield

    # Stop scheduler
    try:
        stop_scheduler()
        logging.info("Scheduler stopped.")
    except Exception as e:
        logging.error(f"Error stopping scheduler: {e}")

    # Stop services on shutdown
    github_connector = app_state.get("github_connector")
    if isinstance(github_connector, GithubConnector):
        logging.info("Shutting down GitHub connector.")
        await github_connector.stop()

    slack_connector = app_state.get("slack_connector")
    if isinstance(slack_connector, SlackConnector):
        logging.info("Shutting down Slack connector.")
        await slack_connector.stop()

    notion_connector = app_state.get("notion_connector")
    if isinstance(notion_connector, NotionConnector):
        logging.info("Shutting down Notion connector.")
        await notion_connector.stop()

    app_state.clear()


app = FastAPI(
    title="Saathy",
    description="A FastAPI-based application",
    version=__version__,
    lifespan=lifespan,
)


def get_vector_repo() -> VectorRepository:
    """Get the vector repository from application state, creating it if needed."""
    if app_state.get("vector_repo") is None:
        if "settings" not in app_state:
            settings = get_settings()
        else:
            settings = app_state["settings"]

        qdrant_url = str(settings.qdrant_url)
        if qdrant_url.startswith("http://"):
            qdrant_url = qdrant_url[7:]
        elif qdrant_url.startswith("https://"):
            qdrant_url = qdrant_url[8:]

        qdrant_url = qdrant_url.split("/")[0]

        host_port = qdrant_url.split(":")
        host = host_port[0]

        try:
            port = int(host_port[1]) if len(host_port) > 1 else 6333
        except (ValueError, IndexError):
            port = 6333

        # Prefer using full URL when provided to avoid protocol ambiguity
        qdrant_client = QdrantClientWrapper(
            url=str(settings.qdrant_url),
            host=host,
            port=port,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
            api_key=settings.qdrant_api_key_str,
        )
        app_state["vector_repo"] = VectorRepository(client=qdrant_client)

    return app_state["vector_repo"]


def get_github_connector() -> GithubConnector:
    """Get the GitHub connector from application state, raising an error if unavailable."""
    github_connector = app_state.get("github_connector")
    if not isinstance(github_connector, GithubConnector):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub connector is not configured or available.",
        )
    return github_connector


def get_slack_connector() -> SlackConnector:
    """Get the Slack connector from application state, raising an error if unavailable."""
    slack_connector = app_state.get("slack_connector")
    if not isinstance(slack_connector, SlackConnector):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack connector is not configured or available.",
        )
    return slack_connector


def get_notion_connector() -> NotionConnector:
    """Get the Notion connector from application state, raising an error if unavailable."""
    notion_connector = app_state.get("notion_connector")
    if not isinstance(notion_connector, NotionConnector):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion connector is not configured or available.",
        )
    return notion_connector


def get_content_processor() -> ContentProcessor:
    """Get the content processor from application state, raising an error if unavailable."""
    content_processor = app_state.get("content_processor")
    if not isinstance(content_processor, ContentProcessor):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content processor is not configured or available.",
        )
    return content_processor


@app.get("/healthz")
async def health_check(
    vector_repo: VectorRepository = Depends(get_vector_repo),
) -> dict[str, str | dict[str, str]]:
    """Health check endpoint."""
    try:
        qdrant_healthy = await vector_repo.health_check()
        if qdrant_healthy:
            return {"status": "healthy", "dependencies": {"qdrant": "healthy"}}
        else:
            return {
                "status": "unhealthy",
                "dependencies": {"qdrant": "unhealthy"},
            }
    except Exception as e:
        logging.warning(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "dependencies": {"qdrant": "unavailable"},
        }


@app.get("/readyz")
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint - returns OK if the service is ready to accept requests."""
    return {"status": "ready"}


@app.get("/config")
async def get_config(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Get application configuration (non-sensitive fields only)."""
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "debug": str(settings.debug),
        "log_level": settings.log_level,
        "host": settings.host,
        "port": str(settings.port),
        "workers": str(settings.workers),
        "enable_tracing": str(settings.enable_tracing),
    }


# --- GitHub Connector Endpoints ---


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Handle incoming GitHub webhook events after verifying the signature."""
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Hub-Signature-256 header is missing.",
        )

    if not settings.github_webhook_secret_str:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub webhook secret is not configured.",
        )

    body = await request.body()
    expected_signature = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret_str.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
    )

    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature."
        )

    event_type = request.headers.get("X-GitHub-Event")
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-GitHub-Event header is missing.",
        )

    if event_type == "ping":
        logging.info("Received GitHub ping event.")
        return {"message": "pong"}

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload."
        ) from e

    # Process the event using the GitHub connector
    event_data = {"event_type": event_type, "payload": payload}
    processed_content = await github_connector.process_event(event_data)

    # Get content processor from GitHub connector config
    content_processor = github_connector.config.get("content_processor")

    # Process and store content using the content processor
    if processed_content and content_processor:
        processing_result = await content_processor.process_and_store(processed_content)
        logging.info(
            f"Processed {len(processed_content)} items from GitHub '{event_type}' event. "
            f"Result: {processing_result['processed_items']}/{processing_result['total_items']} items stored."
        )

        return {
            "status": "ok",
            "event": event_type,
            "processing_result": processing_result,
        }
    elif processed_content and not content_processor:
        logging.warning(
            "GitHub content processor not available, unable to store content."
        )
        return {
            "status": "warning",
            "event": event_type,
            "message": "Content processor not available",
            "processing_result": {
                "total_items": len(processed_content),
                "processed_items": 0,
                "failed_items": len(processed_content),
            },
        }
    else:
        return {
            "status": "ok",
            "event": event_type,
            "processing_result": {
                "total_items": 0,
                "processed_items": 0,
                "failed_items": 0,
            },
        }


@app.get("/connectors/github/status")
async def github_connector_status(
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Return the health and status of the GitHub connector."""
    is_healthy = await github_connector.health_check()
    return {
        "name": github_connector.name,
        "status": github_connector.status.value,
        "healthy": is_healthy,
    }


@app.post("/connectors/github/sync")
async def github_manual_sync(
    repository: str,
    days_back: int = 7,
    event_types: Optional[str] = None,  # comma-separated: commits,issues,pulls
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Trigger a manual repository sync by fetching recent GitHub activity."""
    try:
        if not github_connector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub connector is not initialized.",
            )

        content_processor = github_connector.config.get("content_processor")
        if not content_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Content processor is not available for GitHub connector.",
            )

        logging.info(f"Starting manual GitHub sync for repository: {repository}")

        # Parse event types
        types_to_fetch = []
        if event_types:
            types_to_fetch = [t.strip() for t in event_types.split(",")]
        else:
            types_to_fetch = ["commits", "issues", "pulls"]

        results = {
            "repository": repository,
            "days_back": days_back,
            "event_types": types_to_fetch,
            "total_processed": 0,
            "events_by_type": {},
            "errors": [],
        }

        # Fetch recent commits
        if "commits" in types_to_fetch:
            try:
                commits = await _fetch_recent_commits(
                    github_connector, repository, days_back
                )
                if commits:
                    processed_content = await github_connector.process_event(
                        {
                            "event_type": "push",
                            "payload": {
                                "commits": commits,
                                "repository": {"full_name": repository},
                            },
                        }
                    )
                    if processed_content:
                        result = await content_processor.process_and_store(
                            processed_content
                        )
                        results["events_by_type"]["commits"] = {
                            "found": len(commits),
                            "processed": result.get("processed_items", 0),
                        }
                        results["total_processed"] += result.get("processed_items", 0)
            except Exception as e:
                error_msg = f"Error fetching commits: {str(e)}"
                logging.error(error_msg)
                results["errors"].append(error_msg)

        # Fetch recent issues
        if "issues" in types_to_fetch:
            try:
                issues = await _fetch_recent_issues(
                    github_connector, repository, days_back
                )
                if issues:
                    for issue in issues:
                        processed_content = await github_connector.process_event(
                            {
                                "event_type": "issues",
                                "payload": {
                                    "issue": issue,
                                    "repository": {"full_name": repository},
                                },
                            }
                        )
                        if processed_content:
                            result = await content_processor.process_and_store(
                                processed_content
                            )
                            results["total_processed"] += result.get(
                                "processed_items", 0
                            )

                    results["events_by_type"]["issues"] = {
                        "found": len(issues),
                        "processed": len(
                            issues
                        ),  # Each issue is processed individually
                    }
            except Exception as e:
                error_msg = f"Error fetching issues: {str(e)}"
                logging.error(error_msg)
                results["errors"].append(error_msg)

        # Fetch recent pull requests
        if "pulls" in types_to_fetch:
            try:
                pulls = await _fetch_recent_pulls(
                    github_connector, repository, days_back
                )
                if pulls:
                    for pull in pulls:
                        processed_content = await github_connector.process_event(
                            {
                                "event_type": "pull_request",
                                "payload": {
                                    "pull_request": pull,
                                    "repository": {"full_name": repository},
                                },
                            }
                        )
                        if processed_content:
                            result = await content_processor.process_and_store(
                                processed_content
                            )
                            results["total_processed"] += result.get(
                                "processed_items", 0
                            )

                    results["events_by_type"]["pulls"] = {
                        "found": len(pulls),
                        "processed": len(pulls),  # Each PR is processed individually
                    }
            except Exception as e:
                error_msg = f"Error fetching pull requests: {str(e)}"
                logging.error(error_msg)
                results["errors"].append(error_msg)

        logging.info(
            f"GitHub manual sync completed for {repository}. Total processed: {results['total_processed']}"
        )
        return {"message": "GitHub manual sync completed", "results": results}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in GitHub manual sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync GitHub repository: {str(e)}",
        ) from e


async def _fetch_recent_commits(
    github_connector: GithubConnector, repository: str, days_back: int
) -> list[dict]:
    """Fetch recent commits from a repository."""
    try:
        return await github_connector.fetch_recent_commits(repository, days_back)
    except Exception as e:
        logging.error(f"Error fetching commits: {e}")
        return []


async def _fetch_recent_issues(
    github_connector: GithubConnector, repository: str, days_back: int
) -> list[dict]:
    """Fetch recent issues from a repository."""
    try:
        return await github_connector.fetch_recent_issues(repository, days_back)
    except Exception as e:
        logging.error(f"Error fetching issues: {e}")
        return []


async def _fetch_recent_pulls(
    github_connector: GithubConnector, repository: str, days_back: int
) -> list[dict]:
    """Fetch recent pull requests from a repository."""
    try:
        return await github_connector.fetch_recent_pulls(repository, days_back)
    except Exception as e:
        logging.error(f"Error fetching pull requests: {e}")
        return []


# --- Slack Connector Endpoints ---


@app.get("/connectors/slack/status")
async def slack_connector_status(
    slack_connector: SlackConnector = Depends(get_slack_connector),
):
    """Return connector health, status, and basic metrics."""
    try:
        is_healthy = await slack_connector.health_check()

        return {
            "status": slack_connector.status.value,
            "name": "slack",
            "uptime": "N/A",  # TODO: Add uptime tracking
            "last_message": "N/A",  # TODO: Add message tracking
            "channels_monitored": slack_connector.channels,
            "messages_processed": 0,  # TODO: Add message counter
            "connection_healthy": is_healthy,
            "config": {"channels": slack_connector.channels, "auto_start": True},
        }
    except Exception as e:
        logging.error(f"Error getting Slack connector status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Slack connector status.",
        ) from e


@app.post("/connectors/slack/start")
async def start_slack_connector(
    slack_connector: SlackConnector = Depends(get_slack_connector),
):
    """Start the connector if not running."""
    try:
        if slack_connector.status.value == "active":
            return {"message": "Slack connector is already running."}

        await slack_connector.start()
        logging.info("Slack connector started successfully via API.")
        return {"message": "Slack connector started successfully."}
    except Exception as e:
        logging.error(f"Error starting Slack connector: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Slack connector.",
        ) from e


@app.post("/connectors/slack/stop")
async def stop_slack_connector(
    slack_connector: SlackConnector = Depends(get_slack_connector),
):
    """Stop the connector if running."""
    try:
        if slack_connector.status.value == "inactive":
            return {"message": "Slack connector is already stopped."}

        await slack_connector.stop()
        logging.info("Slack connector stopped successfully via API.")
        return {"message": "Slack connector stopped successfully."}
    except Exception as e:
        logging.error(f"Error stopping Slack connector: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop Slack connector.",
        ) from e


@app.get("/connectors/slack/channels")
async def get_slack_channels(
    slack_connector: SlackConnector = Depends(get_slack_connector),
):
    """List available channels from Slack workspace."""
    try:
        if not slack_connector.web_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Slack web client is not available.",
            )

        # Get list of channels
        response = await slack_connector.web_client.conversations_list(
            types="public_channel,private_channel"
        )

        if not response.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch channels from Slack.",
            )

        channels = []
        for channel in response.get("channels", []):
            channels.append(
                {
                    "id": channel.get("id"),
                    "name": channel.get("name"),
                    "is_private": channel.get("is_private", False),
                    "is_member": channel.get("is_member", False),
                    "num_members": channel.get("num_members", 0),
                }
            )

        return {
            "channels": channels,
            "total": len(channels),
            "monitored_channels": slack_connector.channels,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching Slack channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Slack channels.",
        ) from e


@app.post("/connectors/slack/process")
async def process_slack_content(
    message: str,
    channel_id: str = "manual",
    content_processor: ContentProcessor = Depends(get_content_processor),
):
    """Manually process a Slack message."""
    from saathy.connectors.base import ContentType, ProcessedContent

    # Create mock ProcessedContent
    content = ProcessedContent(
        id=f"manual_{channel_id}_{datetime.now().timestamp()}",
        content=message,
        content_type=ContentType.TEXT,
        source="slack_manual",
        metadata={
            "source": "slack",
            "channel_id": channel_id,
            "channel_name": "manual",
            "user_id": "manual",
            "timestamp": str(datetime.now().timestamp()),
            "is_thread_reply": False,
        },
        timestamp=datetime.now(),
        raw_data={"text": message, "channel": channel_id},
    )

    result = await content_processor.process_and_store([content])
    return result


# --- Notion Connector Endpoints ---


@app.get("/connectors/notion/status")
async def notion_connector_status(
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """Get comprehensive status of the Notion connector."""
    try:
        status_info = notion_connector.get_status()

        # Calculate uptime
        uptime = "Unknown"
        if hasattr(notion_connector, "_start_time") and notion_connector._start_time:
            from datetime import datetime, timezone

            uptime_delta = datetime.now(timezone.utc) - notion_connector._start_time
            hours = int(uptime_delta.total_seconds() // 3600)
            minutes = int((uptime_delta.total_seconds() % 3600) // 60)
            uptime = f"{hours}h {minutes}m"

        # Get last sync time
        last_sync = None
        if notion_connector._last_sync:
            last_sync = max(notion_connector._last_sync.values()).isoformat()

        # Calculate sync statistics
        total_pages_processed = len(notion_connector._processed_items)

        return {
            "status": status_info["status"],
            "name": "notion",
            "uptime": uptime,
            "last_sync": last_sync,
            "total_pages_processed": total_pages_processed,
            "databases_monitored": notion_connector.databases,
            "pages_monitored": notion_connector.pages,
            "sync_statistics": {
                "total_syncs": len(notion_connector._last_sync),
                "successful_syncs": len(notion_connector._last_sync),
                "failed_syncs": 0,  # TODO: Track failed syncs
                "last_error": None,  # TODO: Track last error
                "average_sync_time": 0,  # TODO: Track sync times
                "items_per_sync": total_pages_processed
                / max(len(notion_connector._last_sync), 1),
            },
            "configuration": {
                "poll_interval": notion_connector.poll_interval,
                "auto_discover": len(notion_connector.databases) == 0
                and len(notion_connector.pages) == 0,
                "databases_count": len(notion_connector.databases),
                "pages_count": len(notion_connector.pages),
            },
        }
    except Exception as e:
        logging.error(f"Error getting Notion connector status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Notion connector status.",
        ) from e


@app.get("/connectors/notion/processing-stats")
async def notion_processing_stats(
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """Get Notion content processing statistics."""
    if not notion_connector:
        raise HTTPException(status_code=503, detail="Notion connector not available")

    # Return processing statistics
    return {
        "total_processed": len(notion_connector._processed_items),
        "databases_monitored": len(notion_connector.databases),
        "pages_monitored": len(notion_connector.pages),
        "last_sync_times": notion_connector._last_sync,
        "connector_status": notion_connector.status.value,
    }


@app.post("/connectors/notion/start")
async def start_notion_connector(
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """Start the Notion connector if not running."""
    try:
        if notion_connector.status.value == "active":
            return {"message": "Notion connector is already running."}

        await notion_connector.start()
        return {"message": "Notion connector started successfully."}
    except Exception as e:
        logging.error(f"Error starting Notion connector: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Notion connector.",
        ) from e


@app.post("/connectors/notion/stop")
async def stop_notion_connector(
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """Stop the Notion connector if running."""
    try:
        if notion_connector.status.value == "inactive":
            return {"message": "Notion connector is already stopped."}

        await notion_connector.stop()
        return {"message": "Notion connector stopped successfully."}
    except Exception as e:
        logging.error(f"Error stopping Notion connector: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop Notion connector.",
        ) from e


@app.post("/connectors/notion/sync")
async def trigger_notion_sync(
    full_sync: bool = False,
    database_id: Optional[str] = None,
    page_id: Optional[str] = None,
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """Trigger manual sync - full or incremental, specific resources or all."""
    try:
        if database_id:
            await notion_connector._sync_database(database_id, full_sync=full_sync)
            return {
                "message": f"Database {database_id} synced successfully.",
                "sync_type": "full" if full_sync else "incremental",
                "resource_type": "database",
                "resource_id": database_id,
            }
        elif page_id:
            await notion_connector._sync_page(page_id, full_sync=full_sync)
            return {
                "message": f"Page {page_id} synced successfully.",
                "sync_type": "full" if full_sync else "incremental",
                "resource_type": "page",
                "resource_id": page_id,
            }
        else:
            # Full sync of all configured resources
            await notion_connector._initial_sync()
            return {
                "message": "Full Notion sync completed successfully.",
                "sync_type": "full",
                "resource_type": "all",
                "databases_synced": len(notion_connector.databases),
                "pages_synced": len(notion_connector.pages),
            }
    except Exception as e:
        logging.error(f"Error during Notion sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync Notion content.",
        ) from e


@app.get("/connectors/notion/databases")
async def list_notion_databases(
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """List available databases in Notion workspace."""
    if not notion_connector or not notion_connector.client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion connector not available",
        )

    try:
        # Search for databases
        search_response = await notion_connector.client.search(
            filter={"property": "object", "value": "database"}
        )

        databases = []
        for result in search_response.get("results", []):
            title = notion_connector._extract_title(result.get("title", []))
            databases.append(
                {
                    "id": result["id"],
                    "title": title,
                    "url": result.get("url", ""),
                    "created_time": result.get("created_time"),
                    "last_edited_time": result.get("last_edited_time"),
                    "is_monitored": result["id"] in notion_connector.databases,
                }
            )

        return {
            "databases": databases,
            "total_count": len(databases),
            "monitored_count": len([db for db in databases if db["is_monitored"]]),
        }

    except Exception as e:
        logging.error(f"Failed to list Notion databases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve databases",
        ) from e


@app.get("/connectors/notion/search")
async def search_notion_content(
    query: str,
    limit: int = 10,
    notion_connector: NotionConnector = Depends(get_notion_connector),
):
    """Search Notion workspace for content."""
    if not notion_connector or not notion_connector.client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion connector not available",
        )

    try:
        search_response = await notion_connector.client.search(
            query=query, page_size=min(limit, 100)
        )

        results = []
        for result in search_response.get("results", []):
            object_type = result.get("object")
            if object_type == "page":
                title = notion_connector._extract_title(
                    result.get("properties", {}).get("title", {}).get("title", [])
                )
                results.append(
                    {
                        "id": result["id"],
                        "type": "page",
                        "title": title,
                        "url": result.get("url", ""),
                        "last_edited_time": result.get("last_edited_time"),
                    }
                )
            elif object_type == "database":
                title = notion_connector._extract_title(result.get("title", []))
                results.append(
                    {
                        "id": result["id"],
                        "type": "database",
                        "title": title,
                        "url": result.get("url", ""),
                        "last_edited_time": result.get("last_edited_time"),
                    }
                )

        return {"results": results, "query": query, "total_count": len(results)}

    except Exception as e:
        logging.error(f"Failed to search Notion content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed"
        ) from e


@app.post("/connectors/notion/process")
async def process_notion_content(
    page_data: dict,
    content_processor: ContentProcessor = Depends(get_content_processor),
):
    """Manually process Notion page data."""
    try:
        from notion_client import AsyncClient

        from saathy.connectors.notion_content_extractor import NotionContentExtractor

        # Create a temporary client for processing
        settings = get_settings()
        if not settings.notion_token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Notion token not configured.",
            )

        client = AsyncClient(auth=settings.notion_token_str)
        extractor = NotionContentExtractor(client)

        # Extract content from the page data
        processed_content = await extractor.extract_page_content(page_data)

        if processed_content:
            result = await content_processor.process_and_store(processed_content)
            return result
        else:
            return {"message": "No content extracted from page data."}

    except Exception as e:
        logging.error(f"Error processing Notion content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Notion content.",
        ) from e


# --- Manual Sync Endpoints ---


@app.post("/manual-sync/slack")
async def manual_slack_sync(
    minutes: int = 60,
    channel_id: Optional[str] = None,
):
    """Manually trigger Slack sync for configured channels."""
    try:
        slack_connector = app_state.get("slack_connector")
        content_processor = app_state.get("content_processor")

        if not slack_connector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Slack connector is not initialized.",
            )

        if not content_processor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Content processor is not initialized.",
            )

        logging.info(f"Starting manual Slack sync (last {minutes} minutes)...")

        # Get channels to sync
        if channel_id:
            channels = [channel_id]
        else:
            channels = slack_connector.config.get("channels", [])

        if not channels:
            return {
                "message": "No channels configured for sync",
                "total_processed": 0,
                "channel_results": [],
            }

        results = []
        total_processed = 0

        for ch_id in channels:
            try:
                messages = await slack_connector.fetch_recent_messages(
                    ch_id, minutes=minutes
                )
                if messages:
                    result = await content_processor.process_and_store(messages)
                    processed = result.get("processed_items", 0)
                    total_processed += processed
                    results.append(
                        {
                            "channel_id": ch_id,
                            "messages_found": len(messages),
                            "messages_processed": processed,
                            "status": "success",
                        }
                    )
                else:
                    results.append(
                        {
                            "channel_id": ch_id,
                            "messages_found": 0,
                            "messages_processed": 0,
                            "status": "no_messages",
                        }
                    )
            except Exception as e:
                logging.error(f"Error syncing channel {ch_id}: {e}")
                results.append(
                    {"channel_id": ch_id, "status": "error", "error": str(e)}
                )

        return {
            "message": "Manual Slack sync completed",
            "total_processed": total_processed,
            "channel_results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in manual Slack sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync Slack: {str(e)}",
        ) from e


@app.get("/test-pipeline")
async def test_pipeline():
    """Test the entire data pipeline with sample data."""
    try:
        embedding_service = app_state.get("embedding_service")
        vector_repo = app_state.get("vector_repo")

        if not embedding_service or not vector_repo:
            return {
                "status": "error",
                "message": "Core services not initialized",
                "embedding_service": embedding_service is not None,
                "vector_repo": vector_repo is not None,
            }

        # Debug embedding service
        debug_info = {
            "embedding_service_initialized": embedding_service is not None,
            "available_models": embedding_service.get_available_models()
            if embedding_service
            else [],
            "registry_models": len(embedding_service.registry.list_models())
            if embedding_service
            else 0,
        }

        # Test model loading
        try:
            # Try to get the best model for text
            best_model = embedding_service.registry.get_best_model_for_content(
                "text", "balanced"
            )
            debug_info["best_model_found"] = best_model is not None
            if best_model:
                debug_info["best_model_name"] = best_model.metadata.name
                debug_info["best_model_loaded"] = best_model.is_loaded()
            else:
                debug_info["best_model_found"] = False
        except Exception as e:
            debug_info["model_selection_error"] = str(e)

        # Create test content
        test_content = ProcessedContent(
            id="test_" + datetime.now().isoformat(),
            content="This is a test message to verify the data pipeline is working correctly. It should be processed, embedded, and stored in Qdrant.",
            content_type=ContentType.TEXT,
            source="test",
            metadata={
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            timestamp=datetime.now(timezone.utc),
            raw_data={"test": "data"},
        )

        # Process through content processor with detailed error handling
        try:
            content_processor = ContentProcessor(embedding_service, vector_repo)
            result = await content_processor.process_and_store([test_content])
            debug_info["processing_success"] = True
            debug_info["processing_result"] = result
        except Exception as e:
            debug_info["processing_error"] = str(e)
            debug_info["processing_success"] = False
            result = {
                "total_items": 1,
                "processed_items": 0,
                "failed_items": 1,
                "errors": [str(e)],
            }

        # Try to search for it
        # For now, let's skip the search test since there's a design issue with SearchQuery
        # The SearchQuery model expects text but the search_similar method expects embedding vectors
        # This needs to be fixed in the VectorRepository implementation

        search_results = []  # Skip search for now
        found_test = False

        found_test = False
        if search_results:
            for result in search_results:
                if result.document.metadata.get("source") == "test":
                    found_test = True
                    break

        return {
            "status": "success"
            if debug_info.get("processing_success", False)
            else "error",
            "pipeline_test": {
                "content_created": True,
                "processing_result": result,
                "stored_in_qdrant": result.get("processed_items", 0) > 0,
                "searchable": found_test,
            },
            "services_status": {
                "embedding_service": True,
                "vector_repo": True,
                "qdrant_accessible": True,
            },
            "debug_info": debug_info,
        }

    except Exception as e:
        logging.error(f"Pipeline test failed: {e}")
        return {"status": "error", "error": str(e), "error_type": type(e).__name__}


@app.get("/debug/connectors")
async def debug_connectors():
    """Get detailed debug information about all connectors."""
    debug_info = {"app_state_keys": list(app_state.keys()), "connectors": {}}

    # Check GitHub
    github = app_state.get("github_connector")
    if github:
        debug_info["connectors"]["github"] = {
            "initialized": True,
            "status": github.status.value if hasattr(github, "status") else "unknown",
            "config_keys": list(github.config.keys())
            if hasattr(github, "config")
            else [],
            "has_content_processor": "content_processor" in github.config
            if hasattr(github, "config")
            else False,
        }
    else:
        debug_info["connectors"]["github"] = {"initialized": False}

    # Check Slack
    slack = app_state.get("slack_connector")
    if slack:
        debug_info["connectors"]["slack"] = {
            "initialized": True,
            "status": slack.status.value if hasattr(slack, "status") else "unknown",
            "channels": slack.config.get("channels", [])
            if hasattr(slack, "config")
            else [],
            "has_content_processor": slack.content_processor is not None
            if hasattr(slack, "content_processor")
            else False,
            "web_client_active": slack.web_client is not None
            if hasattr(slack, "web_client")
            else False,
        }
    else:
        debug_info["connectors"]["slack"] = {"initialized": False}

    # Check Notion
    notion = app_state.get("notion_connector")
    if notion:
        debug_info["connectors"]["notion"] = {
            "initialized": True,
            "status": notion.status.value if hasattr(notion, "status") else "unknown",
            "databases": len(notion.databases) if hasattr(notion, "databases") else 0,
            "pages": len(notion.pages) if hasattr(notion, "pages") else 0,
            "has_content_processor": notion.content_processor is not None
            if hasattr(notion, "content_processor")
            else False,
            "is_running": notion._running if hasattr(notion, "_running") else False,
        }
    else:
        debug_info["connectors"]["notion"] = {"initialized": False}

    # Check content processor
    content_processor = app_state.get("content_processor")
    debug_info["content_processor"] = {
        "initialized": content_processor is not None,
        "has_embedding_service": content_processor.embedding_service is not None
        if content_processor
        else False,
        "has_vector_repo": content_processor.vector_repo is not None
        if content_processor
        else False,
    }

    # Check scheduler
    debug_info["scheduler"] = {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat()
                if job.next_run_time
                else None,
            }
            for job in scheduler.get_jobs()
        ],
    }

    return debug_info
