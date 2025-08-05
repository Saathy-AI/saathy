"""FastAPI application instance."""

import hashlib
import hmac
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Request, status

from saathy import __version__
from saathy.config import Settings, get_settings
from saathy.connectors import GithubConnector, NotionConnector, SlackConnector
from saathy.connectors.content_processor import ContentProcessor
from saathy.embedding.service import EmbeddingService, get_embedding_service
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
        None,
    ],
] = {}


def get_notion_config(settings: Settings) -> dict[str, any]:
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load settings and initialize connectors before the app starts, and clean up on shutdown."""
    settings = get_settings()

    # Initialize services as None - will be created lazily when needed
    app_state["settings"] = settings
    app_state["vector_repo"] = None
    app_state["embedding_service"] = None

    # Initialize GitHub connector if configured
    if settings.github_webhook_secret_str and settings.github_token_str:
        logging.info("GitHub connector is configured, initializing.")
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
        await github_connector.start()
        app_state["github_connector"] = github_connector
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
            await notion_connector.start()
            app_state["notion_connector"] = notion_connector
            logging.info("Notion connector initialized and started successfully.")
        except Exception as e:
            app_state["notion_connector"] = None
            logging.error(f"Failed to initialize Notion connector: {e}")
    else:
        app_state["notion_connector"] = None
        logging.warning(
            "Notion connector not configured. Skipping initialization. "
            "Provide NOTION_TOKEN to enable it."
        )

    # Initialize embedding service
    try:
        embedding_service = await get_embedding_service()
        app_state["embedding_service"] = embedding_service
        logging.info("Embedding service initialized successfully.")
    except Exception as e:
        app_state["embedding_service"] = None
        logging.error(f"Failed to initialize embedding service: {e}")

    yield

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

        qdrant_client = QdrantClientWrapper(
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
    content_processor: ContentProcessor = Depends(get_content_processor),
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

    # Process and store content using the content processor
    if processed_content:
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
    github_connector: GithubConnector = Depends(get_github_connector),
):
    """Trigger a manual repository sync (placeholder)."""
    logging.info(
        f"Manual sync requested for repository: {repository} "
        f"for connector {github_connector.name}. This feature is not yet implemented."
    )
    # In a real implementation, this would trigger the sync logic.
    return {"message": "Manual sync acknowledged. Feature is under development."}


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
