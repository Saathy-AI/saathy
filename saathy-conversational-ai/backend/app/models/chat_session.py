import enum
import uuid
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ENDED = "ended"


class ChatSessionDB(Base):
    """Database model for chat sessions"""

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    context_state = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    # Relationships
    turns = relationship(
        "ChatTurnDB", back_populates="session", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)


class ChatTurnDB(Base):
    """Database model for chat turns"""

    __tablename__ = "chat_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    context_used = Column(JSON, default=dict)
    retrieval_strategy = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)

    # Relationships
    session = relationship("ChatSessionDB", back_populates="turns")


# Pydantic models for API
class ChatTurn(BaseModel):
    """Pydantic model for chat turns"""

    user_message: str
    assistant_response: str
    timestamp: datetime
    context_used: dict = Field(default_factory=dict)
    retrieval_strategy: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ConversationTurn(ChatTurn):
    """Compatibility alias used in tests"""

    pass


class ChatSession(BaseModel):
    """Pydantic model for chat sessions supporting v1 and v2 shapes"""

    id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    conversation_turns: list[ChatTurn] = Field(default_factory=list)
    context_state: dict = Field(default_factory=dict)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def __init__(self, **data):
        # Synchronize id and session_id
        sid = data.get("session_id") or data.get("id") or str(uuid.uuid4())
        data["session_id"] = sid
        data["id"] = sid
        super().__init__(**data)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """Input model for new chat messages (v1/v2 compatible)"""

    message: Optional[str] = None  # v1
    content: Optional[str] = None  # v2
    session_id: Optional[str] = None

    def get_text(self) -> str:
        return self.content or self.message or ""


class ChatResponse(BaseModel):
    """Response model for chat messages (v1/v2 compatible)"""

    # v1 fields
    session_id: Optional[str] = None
    message: Optional[str] = None
    context_sources: list[dict] = Field(default_factory=list)
    retrieval_strategy: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # v2 fields
    response: Optional[str] = None
    context_used: list[dict] = Field(default_factory=list)
    metadata: Optional[dict] = None
