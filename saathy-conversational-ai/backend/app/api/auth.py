from fastapi import Header, HTTPException
from typing import Optional

async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Get current user from auth token"""
    # In production, verify JWT token and extract user_id
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # For demo purposes, extract user from header
    # Format: "Bearer <user_id>"
    if authorization.startswith("Bearer "):
        user_id = authorization.replace("Bearer ", "")
        return user_id
    
    # Default test user
    return "test_user_123"