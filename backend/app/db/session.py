"""
Database Session Configuration

Handles async database connections and session management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create declarative base for models
Base = declarative_base()


def get_database_url() -> str:
    """
    Get the database URL from settings.
    
    Returns:
        Database URL string
    """
    if settings.DATABASE_URL:
        # Ensure the URL uses the async driver
        url = settings.DATABASE_URL
        
        # Convert postgresql:// to postgresql+asyncpg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        
        return url
    
    # Build URL from components
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def create_engine():
    """
    Create async database engine.
    
    Returns:
        AsyncEngine instance
    """
    database_url = get_database_url()
    
    logger.info(f"Creating async database engine for: {database_url.split('@')[0]}@...")
    
    # Create async engine with proper configuration
    engine = create_async_engine(
        database_url,
        echo=settings.DB_ECHO,
        future=True,
        # Use NullPool for async to avoid connection issues
        poolclass=NullPool,
        # Alternative: Use AsyncAdaptedQueuePool with proper settings
        # poolclass=AsyncAdaptedQueuePool,
        # pool_size=20,
        # max_overflow=10,
        # pool_pre_ping=True,
        # pool_recycle=3600,
    )
    
    return engine


# Create engine
engine = create_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Yields:
        AsyncSession instance
        
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database - create all tables.
    
    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they're registered
        from app.models.user import User
        from app.models.transaction import Transaction
        from app.models.alert import Alert
        # from app.models.upload import Upload
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Database tables created successfully")


async def drop_db():
    """
    Drop all database tables.
    
    ⚠️ WARNING: This will delete all data!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    logger.warning("All database tables dropped")


async def close_db():
    """
    Close database connections.
    
    Call this on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")

async def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    
__all__ = [
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "Base",
    "init_db",
    "drop_db",
    "close_db",
    "check_db_connection",  # Add this line
]