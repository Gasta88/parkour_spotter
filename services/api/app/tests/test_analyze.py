"""Tests for analyze endpoint."""

import asyncio
import asyncpg
import pytest
from fastapi.testclient import TestClient

import app.main as app_module
from app.main import create_app


@pytest.fixture
def client(postgis_db_url, monkeypatch):
    """Create a test client with PostGIS database URL configured."""
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", postgis_db_url)

    app_module.app = create_app()

    with TestClient(app_module.app) as test_client:
        yield test_client


def test_analyze_returns_200(client) -> None:
    """Test that POST /analyze returns 200 with valid request."""
    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "cells" in data
    assert isinstance(data["cells"], list)


def test_analyze_response_schema(client) -> None:
    """Test that response matches expected schema with features field."""
    response = client.post(
        "/analyze",
        json={
            "lat": 45.4408,
            "lon": 12.3155,
            "radius_km": 5.0,
        },
    )

    data = response.json()
    assert "data_version" in data
    assert "query_time_ms" in data

    # Cells may be empty if no OSM data loaded, but schema should be valid
    for cell in data["cells"]:
        assert "h3_index" in cell
        assert "score" in cell
        assert "centroid" in cell
        assert "lat" in cell["centroid"]
        assert "lon" in cell["centroid"]
        assert "features" in cell
        assert isinstance(cell["features"], dict)


def test_analyze_missing_fields_returns_422(client) -> None:
    """Test that missing fields return 422."""
    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
        },
    )

    assert response.status_code == 422


def test_analyze_invalid_lat_returns_422(client) -> None:
    """Test that invalid latitude returns 422."""
    response = client.post(
        "/analyze",
        json={
            "lat": 100,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    assert response.status_code == 422


def test_analyze_radius_too_large_returns_422(client) -> None:
    """Test that radius > 10 returns 422."""
    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 15,
        },
    )

    assert response.status_code == 422


def test_analyze_empty_db_returns_none_data_version(client) -> None:
    """Test that POST /analyze returns data_version=None when data_version table is empty."""
    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data_version"] is None


def test_analyze_single_version_returns_correct_metadata(
    client, postgis_db_url
) -> None:
    """Test that POST /analyze returns correct data_version metadata with single row."""

    async def insert_data():
        conn = await asyncpg.connect(postgis_db_url)
        try:
            from datetime import datetime, timezone

            inserted_at = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO data_version (loaded_at, osm_source_url, osm_file_hash, file_size_mb, row_counts)
                VALUES ($1, $2, $3, $4, $5)
                """,
                inserted_at,
                "https://example.com/data.osm.pbf",
                "abc123hash",
                12.5,
                '{"nodes": 1000, "ways": 500}',
            )
        finally:
            await conn.close()

    asyncio.run(insert_data())

    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data_version"] is not None
    assert data["data_version"]["osm_source_url"] == "https://example.com/data.osm.pbf"
    assert data["data_version"]["file_size_mb"] == 12.5


def test_analyze_multiple_versions_returns_latest(client, postgis_db_url) -> None:
    """Test that POST /analyze returns the latest data_version when multiple rows exist."""
    from datetime import datetime, timezone, timedelta

    async def insert_data():
        conn = await asyncpg.connect(postgis_db_url)
        try:
            older_time = datetime.now(timezone.utc) - timedelta(days=1)
            newer_time = datetime.now(timezone.utc)

            await conn.execute(
                """
                INSERT INTO data_version (loaded_at, osm_source_url, osm_file_hash, file_size_mb, row_counts)
                VALUES ($1, $2, $3, $4, $5)
                """,
                older_time,
                "https://example.com/old.osm.pbf",
                "oldhash",
                10.0,
                '{"nodes": 500, "ways": 250}',
            )

            await conn.execute(
                """
                INSERT INTO data_version (loaded_at, osm_source_url, osm_file_hash, file_size_mb, row_counts)
                VALUES ($1, $2, $3, $4, $5)
                """,
                newer_time,
                "https://example.com/new.osm.pbf",
                "newhash",
                15.0,
                '{"nodes": 1500, "ways": 750}',
            )
        finally:
            await conn.close()

    asyncio.run(insert_data())

    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data_version"] is not None
    assert data["data_version"]["osm_source_url"] == "https://example.com/new.osm.pbf"
    assert data["data_version"]["file_size_mb"] == 15.0


def test_analyze_idempotency_skips_reload_within_interval(
    client, postgis_db_url
) -> None:
    """Test that data_version query returns same hash within refresh interval (idempotency)."""
    from datetime import datetime, timezone

    async def insert_data():
        conn = await asyncpg.connect(postgis_db_url)
        try:
            recent_time = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO data_version (loaded_at, osm_source_url, osm_file_hash, file_size_mb, row_counts)
                VALUES ($1, $2, $3, $4, $5)
                """,
                recent_time,
                "https://example.com/data.osm.pbf",
                "same_hash_123",
                12.5,
                '{"nodes": 1000, "ways": 500}',
            )
        finally:
            await conn.close()

    asyncio.run(insert_data())

    response1 = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    response2 = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 5,
        },
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    assert data1["data_version"] is not None
    assert data2["data_version"] is not None
    assert (
        data1["data_version"]["osm_file_hash"] == data2["data_version"]["osm_file_hash"]
    )


def test_analyze_with_seeded_osm_data(client, postgis_db_url) -> None:
    """Test that POST /analyze returns cells with feature breakdown when OSM data exists."""

    async def seed_data():
        conn = await asyncpg.connect(postgis_db_url)
        try:
            # Insert a wall feature
            await conn.execute(
                """
                INSERT INTO planet_osm_line (osm_id, barrier, way)
                VALUES (
                    1000,
                    'wall',
                    ST_SetSRID(ST_MakePoint(12.31, 45.44), 4326)
                )
                """
            )
            # Insert a bench feature
            await conn.execute(
                """
                INSERT INTO planet_osm_point (osm_id, amenity, way)
                VALUES (
                    2000,
                    'bench',
                    ST_SetSRID(ST_MakePoint(12.31, 45.44), 4326)
                )
                """
            )
        finally:
            await conn.close()

    asyncio.run(seed_data())

    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
            "lon": 12.31,
            "radius_km": 0.5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "cells" in data

    # Check that at least some cells have features
    cells_with_features = [
        c
        for c in data["cells"]
        if c.get("features")
        and any(f.get("count", 0) > 0 for f in c["features"].values())
    ]
    assert len(cells_with_features) > 0

    # Clean up
    async def cleanup():
        conn = await asyncpg.connect(postgis_db_url)
        try:
            await conn.execute("DELETE FROM planet_osm_line WHERE osm_id = 1000")
            await conn.execute("DELETE FROM planet_osm_point WHERE osm_id = 2000")
        finally:
            await conn.close()

    asyncio.run(cleanup())
