"""Database connection and session management."""

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session_maker() as session:
        yield session
