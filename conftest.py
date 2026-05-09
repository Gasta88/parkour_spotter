"""Root-level pytest conftest with PostgreSQL testcontainer fixture."""

import asyncpg
import pytest
import socket


def is_docker_available():
    """Check if Docker daemon is running."""
    try:
        socket.create_connection(("localhost", 2375), timeout=1)
        return True
    except (socket.error, ConnectionRefusedError):
        try:
            socket.create_connection(("127.0.0.1", 2375), timeout=1)
            return True
        except (socket.error, ConnectionRefusedError):
            return False


@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL test container for the test session.
    
    Yields:
        dict: Container info with 'database_url' key
    
    Skips test if Docker is not available.
    """
    from testcontainers.postgres import PostgresContainer
    
    if not is_docker_available():
        pytest.skip("Docker not available - skipping container-based tests")
    
    with PostgresContainer("postgres:15", driver="psycopg") as postgres:
        yield {"database_url": postgres.get_connection_url()}


@pytest.fixture(scope="function")
async def db_url(postgres_container):
    """Create a clean database state for each test function.
    
    Creates the data_version table and yields the DATABASE_URL.
    Overrides the settings.database_url for tests.
    
    Args:
        postgres_container: PostgreSQL container fixture
        
    Yields:
        str: Database URL for the test container
    """
    database_url = postgres_container["database_url"]
    
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS data_version (
                id SERIAL PRIMARY KEY,
                loaded_at TIMESTAMPTZ DEFAULT NOW(),
                osm_source_url TEXT NOT NULL,
                osm_file_hash TEXT NOT NULL,
                file_size_mb REAL NOT NULL,
                row_counts JSONB NOT NULL,
                load_duration_seconds INTEGER,
                success BOOLEAN DEFAULT TRUE
            )
        """)
    finally:
        await conn.close()
    
    yield database_url


@pytest.fixture(scope="function")
async def db_connection(db_url):
    """Provide a database connection for tests that need direct DB access.
    
    Args:
        db_url: Database URL from db_url fixture
        
    Yields:
        asyncpg.Connection: Database connection
    """
    conn = await asyncpg.connect(db_url)
    try:
        yield conn
    finally:
        await conn.close()
