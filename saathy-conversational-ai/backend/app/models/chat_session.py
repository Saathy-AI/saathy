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

    class Config:
        from_attributes = True


class ChatSession(BaseModel):
    """Pydantic model for chat sessions"""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    conversation_turns: list[ChatTurn] = Field(default_factory=list)
    context_state: dict = Field(default_factory=dict)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """Input model for new chat messages"""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat messages"""

    session_id: str
    message: str
    context_sources: list[dict] = Field(default_factory=list)
    retrieval_strategy: str = "hybrid"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
