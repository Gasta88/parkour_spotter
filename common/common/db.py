"""Database utilities for async SQLAlchemy with PostgreSQL."""

from contextlib import asynccontextmanager

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


@asynccontextmanager
async def get_raw_connection(engine: AsyncEngine):
    """Yield a raw asyncpg connection from the SQLAlchemy engine.

    This is needed for executing raw SQL queries that use PostGIS/h3-pg
    extensions which may not be fully supported through the SQLAlchemy ORM.

    Usage:
        async with get_raw_connection(engine) as conn:
            rows = await conn.fetch("SELECT ...")

    Args:
        engine: Async SQLAlchemy engine

    Yields:
        asyncpg.Connection: Raw database connection
    """
    async with engine.connect() as conn:
        raw_conn = await conn.get_raw_connection()
        yield raw_conn
