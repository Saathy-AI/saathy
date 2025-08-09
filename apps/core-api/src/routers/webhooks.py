"""Webhook endpoints for external platform integrations."""

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Header, Request, status
from fastapi.responses import Response

from ..dependencies import (
    ConnectorManagerDep,
    VectorStoreDep,
    EmbeddingDep,
    SettingsDep,
)

router = APIRouter()


def verify_github_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str
) -> bool:
    """Verify GitHub webhook signature."""
    if not signature_header:
        return False
    
    hash_algorithm, github_signature = signature_header.split("=", 1)
    if hash_algorithm != "sha256":
        return False
    
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = mac.hexdigest()
    
    return hmac.compare_digest(expected_signature, github_signature)


def verify_slack_signature(
    timestamp: str,
    signature: str,
    body: bytes,
    signing_secret: str
) -> bool:
    """Verify Slack request signature."""
    if not timestamp or not signature:
        return False
    
    # Create the base string
    base_string = f"v0:{timestamp}:{body.decode('utf-8')}"
    
    # Create HMAC SHA256
    mac = hmac.new(
        signing_secret.encode("utf-8"),
        msg=base_string.encode("utf-8"),
        digestmod=hashlib.sha256
    )
    expected_signature = f"v0={mac.hexdigest()}"
    
    return hmac.compare_digest(expected_signature, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    connector_manager: ConnectorManagerDep,
    vector_store: VectorStoreDep,
    embedding_service: EmbeddingDep,
    settings: SettingsDep,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
) -> Response:
    """
    Handle GitHub webhook events.
    
    Processes push events, pull requests, issues, and other repository events.
    """
    # Get request body
    body = await request.body()
    
    # Verify signature
    if settings.github_webhook_secret:
        if not verify_github_signature(
            body,
            x_hub_signature_256 or "",
            settings.get_secret_value(settings.github_webhook_secret)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
    
    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Get GitHub connector
    connector = await connector_manager.get_connector("github")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub connector not available"
        )
    
    # Process event based on type
    event_data = {
        "event_type": x_github_event,
        "delivery_id": x_github_delivery,
        "payload": payload,
    }
    
    try:
        # Process through connector
        contents = await connector.process_event(event_data)
        
        # Generate embeddings and store
        for content in contents:
            embedding = await embedding_service.embed(content.content)
            content.embedding = embedding
            await vector_store.upsert([content])
        
        return Response(
            content=json.dumps({
                "status": "success",
                "processed": len(contents),
                "event": x_github_event,
                "delivery_id": x_github_delivery,
            }),
            media_type="application/json",
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        # Log error but return 200 to prevent GitHub from retrying
        return Response(
            content=json.dumps({
                "status": "error",
                "message": str(e),
                "event": x_github_event,
            }),
            media_type="application/json",
            status_code=status.HTTP_200_OK
        )


@router.post("/slack")
async def slack_webhook(
    request: Request,
    connector_manager: ConnectorManagerDep,
    settings: SettingsDep,
    x_slack_request_timestamp: Optional[str] = Header(None),
    x_slack_signature: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Handle Slack webhook events and slash commands.
    
    Processes messages, app mentions, and slash commands.
    """
    # Get request body
    body = await request.body()
    
    # Verify signature
    if settings.slack_signing_secret:
        if not verify_slack_signature(
            x_slack_request_timestamp or "",
            x_slack_signature or "",
            body,
            settings.get_secret_value(settings.slack_signing_secret)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
    
    # Parse payload
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
    else:
        # URL-encoded payload (for slash commands)
        from urllib.parse import parse_qs
        parsed = parse_qs(body.decode("utf-8"))
        payload = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    
    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    
    # Get Slack connector
    connector = await connector_manager.get_connector("slack")
    if not connector:
        return {"ok": False, "error": "Slack connector not available"}
    
    # Process event
    try:
        await connector.process_event(payload)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/notion")
async def notion_webhook(
    request: Request,
    connector_manager: ConnectorManagerDep,
    vector_store: VectorStoreDep,
    embedding_service: EmbeddingDep,
    settings: SettingsDep,
) -> Response:
    """
    Handle Notion webhook events.
    
    Note: Notion doesn't have official webhooks yet, this is for future compatibility
    or custom integration with Notion automation tools.
    """
    # Get request body
    body = await request.body()
    
    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Get Notion connector
    connector = await connector_manager.get_connector("notion")
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion connector not available"
        )
    
    # Process event
    try:
        contents = await connector.process_event(payload)
        
        # Generate embeddings and store
        for content in contents:
            embedding = await embedding_service.embed(content.content)
            content.embedding = embedding
            await vector_store.upsert([content])
        
        return Response(
            content=json.dumps({
                "status": "success",
                "processed": len(contents),
            }),
            media_type="application/json",
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Notion event: {str(e)}"
        )