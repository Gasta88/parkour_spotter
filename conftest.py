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

    Creates the data_version, spots_annotated, saved_search, cell_feature,
    model, model_evaluation, and training_run tables and yields the DATABASE_URL.
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
                success BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS spots_annotated (
                id SERIAL PRIMARY KEY,
                h3_index VARCHAR(16) NOT NULL UNIQUE,
                rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 5),
                notes TEXT DEFAULT '',
                human_score DOUBLE PRECISION,
                features JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_search (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                lat DOUBLE PRECISION NOT NULL,
                lon DOUBLE PRECISION NOT NULL,
                radius_m DOUBLE PRECISION NOT NULL,
                cell_count INTEGER NOT NULL,
                score_distribution JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cell_feature (
                id SERIAL PRIMARY KEY,
                h3_index VARCHAR(16) NOT NULL,
                osm_file_hash TEXT NOT NULL,
                walls_count INTEGER DEFAULT 0 NOT NULL,
                walls_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                rails_count INTEGER DEFAULT 0 NOT NULL,
                rails_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                gaps_count INTEGER DEFAULT 0 NOT NULL,
                gaps_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                stairs_count INTEGER DEFAULT 0 NOT NULL,
                stairs_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                vaults_count INTEGER DEFAULT 0 NOT NULL,
                vaults_total_area_m2 DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                open_spaces_count INTEGER DEFAULT 0 NOT NULL,
                open_spaces_total_area_m2 DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                h3_res8_parent VARCHAR(15) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (h3_index, osm_file_hash)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS model (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_type TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                feature_list TEXT[],
                hyperparameters JSONB,
                is_active BOOLEAN DEFAULT FALSE NOT NULL,
                status TEXT DEFAULT 'pending' NOT NULL,
                artifact_path TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (name, version)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS model_evaluation (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_id UUID NOT NULL REFERENCES model(id) ON DELETE CASCADE,
                accuracy DOUBLE PRECISION,
                precision DOUBLE PRECISION,
                recall DOUBLE PRECISION,
                f1_score DOUBLE PRECISION,
                roc_auc DOUBLE PRECISION,
                confusion_matrix JSONB,
                feature_importance JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS training_run (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_id UUID NOT NULL REFERENCES model(id) ON DELETE CASCADE,
                evaluation_id UUID REFERENCES model_evaluation(id) ON DELETE SET NULL,
                train_test_split JSONB,
                status TEXT DEFAULT 'running' NOT NULL,
                error_message TEXT,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
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
    and all application tables.

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
                success BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create spots_annotated table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS spots_annotated (
                id SERIAL PRIMARY KEY,
                h3_index VARCHAR(16) NOT NULL UNIQUE,
                rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 5),
                notes TEXT DEFAULT '',
                human_score DOUBLE PRECISION,
                features JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create saved_search table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_search (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                lat DOUBLE PRECISION NOT NULL,
                lon DOUBLE PRECISION NOT NULL,
                radius_m DOUBLE PRECISION NOT NULL,
                cell_count INTEGER NOT NULL,
                score_distribution JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create cell_feature table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cell_feature (
                id SERIAL PRIMARY KEY,
                h3_index VARCHAR(16) NOT NULL,
                osm_file_hash TEXT NOT NULL,
                walls_count INTEGER DEFAULT 0 NOT NULL,
                walls_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                rails_count INTEGER DEFAULT 0 NOT NULL,
                rails_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                gaps_count INTEGER DEFAULT 0 NOT NULL,
                gaps_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                stairs_count INTEGER DEFAULT 0 NOT NULL,
                stairs_total_length_m DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                vaults_count INTEGER DEFAULT 0 NOT NULL,
                vaults_total_area_m2 DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                open_spaces_count INTEGER DEFAULT 0 NOT NULL,
                open_spaces_total_area_m2 DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                h3_res8_parent VARCHAR(15) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (h3_index, osm_file_hash)
            )
        """)

        # Create model table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS model (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_type TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                feature_list TEXT[],
                hyperparameters JSONB,
                is_active BOOLEAN DEFAULT FALSE NOT NULL,
                status TEXT DEFAULT 'pending' NOT NULL,
                artifact_path TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (name, version)
            )
        """)

        # Create model_evaluation table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS model_evaluation (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_id UUID NOT NULL REFERENCES model(id) ON DELETE CASCADE,
                accuracy DOUBLE PRECISION,
                precision DOUBLE PRECISION,
                recall DOUBLE PRECISION,
                f1_score DOUBLE PRECISION,
                roc_auc DOUBLE PRECISION,
                confusion_matrix JSONB,
                feature_importance JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create training_run table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS training_run (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_id UUID NOT NULL REFERENCES model(id) ON DELETE CASCADE,
                evaluation_id UUID REFERENCES model_evaluation(id) ON DELETE SET NULL,
                train_test_split JSONB,
                status TEXT DEFAULT 'running' NOT NULL,
                error_message TEXT,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
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
