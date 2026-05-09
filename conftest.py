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


@pytest.fixture(scope="function")
async def postgis_db_url(postgres_container):
    """Create a PostGIS-enabled database for integration tests.

    Sets up PostGIS and hstore extensions, plus the planet_osm_* tables
    and data_version table.

    Yields:
        str: Database URL for the PostGIS test container
    """
    database_url = postgres_container["database_url"]

    conn = await asyncpg.connect(database_url)
    try:
        # Enable PostGIS and hstore extensions
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS hstore")

        # Create data_version table
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

        # Create planet_osm_* tables (simplified schema matching osm2pgsql output)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS planet_osm_point (
                osm_id BIGINT PRIMARY KEY,
                name TEXT,
                amenity TEXT,
                leisure TEXT,
                sport TEXT,
                barrier TEXT,
                highway TEXT,
                access TEXT,
                way geometry(Point, 3857)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS planet_osm_line (
                osm_id BIGINT PRIMARY KEY,
                name TEXT,
                amenity TEXT,
                leisure TEXT,
                sport TEXT,
                barrier TEXT,
                highway TEXT,
                railway TEXT,
                access TEXT,
                way geometry(LineString, 3857)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS planet_osm_polygon (
                osm_id BIGINT PRIMARY KEY,
                name TEXT,
                amenity TEXT,
                leisure TEXT,
                sport TEXT,
                barrier TEXT,
                highway TEXT,
                access TEXT,
                parking TEXT,
                way geometry(Polygon, 3857)
            )
        """)
    finally:
        await conn.close()

    yield database_url


@pytest.fixture(scope="function")
async def postgis_connection(postgis_db_url):
    """Provide a PostGIS-enabled database connection for integration tests.

    Args:
        postgis_db_url: Database URL from postgis_db_url fixture

    Yields:
        asyncpg.Connection: Database connection with PostGIS extensions
    """
    conn = await asyncpg.connect(postgis_db_url)
    try:
        yield conn
    finally:
        await conn.close()
