"""Database utilities for async SQLAlchemy with PostgreSQL."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Args:
        database_url: PostgreSQL connection URL

    Returns:
        AsyncEngine instance
    """
    return create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )


def create_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory.

    Args:
        engine: Async SQLAlchemy engine

    Returns:
        Async session factory
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
