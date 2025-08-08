from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import redis.asyncio as redis
from typing import AsyncGenerator
from config.settings import get_settings

settings = get_settings()

# PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Redis
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=50
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis() -> redis.Redis:
    """Get Redis connection"""
    return redis.Redis(connection_pool=redis_pool)


@asynccontextmanager
async def get_db_context():
    """Context manager for database operations"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()