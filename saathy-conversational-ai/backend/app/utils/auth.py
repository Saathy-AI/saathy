"""
Authentication utilities for the conversational AI system.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import logging

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Security scheme
security = HTTPBearer(auto_error=False)


class AuthManager:
    """Authentication manager for handling user authentication."""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create a new access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get the current authenticated user from the token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User information from token
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        # For development, allow requests without authentication
        logger.warning("No authentication credentials provided, using default user")
        return {
            "user_id": "test_user_123",
            "username": "test_user",
            "email": "test@example.com",
            "is_authenticated": False
        }
    
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user_id,
        "username": payload.get("username", "unknown"),
        "email": payload.get("email", ""),
        "is_authenticated": True
    }


def create_test_token(user_id: str = "test_user_123") -> str:
    """
    Create a test token for development purposes.
    
    Args:
        user_id: User ID for the token
        
    Returns:
        JWT token string
    """
    data = {
        "sub": user_id,
        "username": "test_user",
        "email": "test@example.com"
    }
    return auth_manager.create_access_token(data)


def get_user_from_header(authorization: Optional[str] = None) -> dict:
    """
    Extract user information from authorization header.
    For development, returns a default user if no valid token is provided.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        User information dictionary
    """
    if not authorization or not authorization.startswith("Bearer "):
        return {
            "user_id": "test_user_123",
            "username": "test_user",
            "email": "test@example.com",
            "is_authenticated": False
        }
    
    token = authorization.replace("Bearer ", "")
    payload = auth_manager.verify_token(token)
    
    if payload is None:
        return {
            "user_id": "test_user_123",
            "username": "test_user",
            "email": "test@example.com",
            "is_authenticated": False
        }
    
    return {
        "user_id": payload.get("sub", "test_user_123"),
        "username": payload.get("username", "test_user"),
        "email": payload.get("email", "test@example.com"),
        "is_authenticated": True
    }
