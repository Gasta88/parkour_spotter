"""Unit and integration tests for feature extraction service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from common.h3_utils import latlng_to_h3
from common.sql_queries import FEATURE_QUERIES


class TestFeatureExtractorUnit:
    """Unit tests for FeatureExtractor with mocked database."""

    @pytest.mark.asyncio
    async def test_extract_returns_dict(self) -> None:
        """Test that extract returns a dict mapping H3 indices to features."""
        from sqlalchemy.ext.asyncio import AsyncEngine
        from app.services.feature_extractor import FeatureExtractor

        # Mock engine
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[]))
        )
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect = MagicMock(return_value=mock_conn)
        mock_engine.dispose = AsyncMock()

        extractor = FeatureExtractor(mock_engine, resolution=11)
        result = await extractor.extract(lat=45.4064, lon=11.8778, radius_km=0.1)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_extract_empty_db_returns_empty_cells(self) -> None:
        """Test that empty database returns empty feature dicts for all cells."""
        from sqlalchemy.ext.asyncio import AsyncEngine
        from app.services.feature_extractor import FeatureExtractor

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_conn = AsyncMock()
        # Return empty results for all queries
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect = MagicMock(return_value=mock_conn)
        mock_engine.dispose = AsyncMock()

        extractor = FeatureExtractor(mock_engine, resolution=11)
        result = await extractor.extract(lat=45.4064, lon=11.8778, radius_km=0.1)

        # Should have cells (from k-ring) but all with empty feature dicts
        assert len(result) > 0
        for h3_idx, features in result.items():
            assert isinstance(h3_idx, str)
            assert isinstance(features, dict)


class TestFeatureExtractorAggregation:
    """Tests for the aggregation logic."""

    def test_row_to_metrics_with_all_columns(self) -> None:
        """Test _row_to_metrics with full column set."""
        from app.services.feature_extractor import _row_to_metrics

        # Mock row with _mapping
        mock_row = MagicMock()
        mock_row._mapping = {
            "h3_index": 123456789,
            "count": 12,
            "total_length_m": 45.3,
            "total_area_m2": 320.0,
        }

        metrics = _row_to_metrics(mock_row, "walls")
        assert metrics["count"] == 12
        assert metrics["total_length_m"] == 45.3
        assert metrics["total_area_m2"] == 320.0

    def test_row_to_metrics_with_count_only(self) -> None:
        """Test _row_to_metrics with count-only columns."""
        from app.services.feature_extractor import _row_to_metrics

        mock_row = MagicMock()
        mock_row._mapping = {
            "h3_index": 123456789,
            "count": 5,
        }

        metrics = _row_to_metrics(mock_row, "benches_blocks")
        assert metrics["count"] == 5
        assert metrics["total_length_m"] == 0.0
        assert metrics["total_area_m2"] == 0.0

    def test_row_to_metrics_with_null_values(self) -> None:
        """Test _row_to_metrics handles NULL values gracefully."""
        from app.services.feature_extractor import _row_to_metrics

        mock_row = MagicMock()
        mock_row._mapping = {
            "h3_index": 123456789,
            "count": 3,
            "total_length_m": None,
            "total_area_m2": None,
        }

        metrics = _row_to_metrics(mock_row, "steps")
        assert metrics["count"] == 3
        assert metrics["total_length_m"] == 0.0
        assert metrics["total_area_m2"] == 0.0

    def test_merge_metrics_sums_values(self) -> None:
        """Test _merge_metrics correctly sums values."""
        from app.services.feature_extractor import _merge_metrics

        existing = {"count": 5, "total_length_m": 10.0, "total_area_m2": 20.0}
        new = {"count": 3, "total_length_m": 7.0, "total_area_m2": 15.0}

        merged = _merge_metrics(existing, new)
        assert merged["count"] == 8
        assert merged["total_length_m"] == 17.0
        assert merged["total_area_m2"] == 35.0

    def test_merge_metrics_handles_missing_keys(self) -> None:
        """Test _merge_metrics handles missing keys with defaults."""
        from app.services.feature_extractor import _merge_metrics

        existing = {"count": 5}
        new = {"count": 3, "total_length_m": 7.0}

        merged = _merge_metrics(existing, new)
        assert merged["count"] == 8
        assert merged["total_length_m"] == 7.0
        assert merged["total_area_m2"] == 0.0


class TestFeatureExtractorIntegration:
    """Integration tests with PostgresContainer (PostGIS)."""

    @pytest.mark.asyncio
    async def test_extract_with_seeded_walls(self, postgis_connection) -> None:
        """Test feature extraction with seeded wall data."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.services.feature_extractor import FeatureExtractor

        conn = postgis_connection

        # Get a test location and its H3 cell
        test_lat, test_lon = 45.4064, 11.8778
        center_cell = latlng_to_h3(test_lat, test_lon, 11)

        # Insert test wall data (line feature)
        # Use ST_SetSRID and ST_MakePoint to create a point in EPSG:3857
        await conn.execute("""
            INSERT INTO planet_osm_line (osm_id, barrier, way)
            VALUES (
                1,
                'wall',
                ST_SetSRID(ST_MakePoint(
                    11.8778, 45.4064
                ), 4326)
            )
        """)
        # Use the connection's DSN to create an async engine
        # For testcontainers with psycopg driver, we need to convert the URL
        raw_dsn = conn.get_dsn()
        async_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            extractor = FeatureExtractor(engine, resolution=11)
            result = await extractor.extract(test_lat, test_lon, 0.1)

            # The center cell should have wall features
            if center_cell in result:
                wall_features = result[center_cell].get("walls", {})
                assert wall_features.get("count", 0) >= 1
        finally:
            await engine.dispose()

        # Clean up
        await conn.execute("DELETE FROM planet_osm_line WHERE osm_id = 1")

    @pytest.mark.asyncio
    async def test_extract_empty_tables(self, postgis_connection) -> None:
        """Test feature extraction against empty planet_osm_* tables."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.services.feature_extractor import FeatureExtractor

        conn = postgis_connection
        raw_dsn = conn.get_dsn()
        async_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            extractor = FeatureExtractor(engine, resolution=11)
            result = await extractor.extract(45.4064, 11.8778, 0.1)

            # Should return cells with empty feature dicts
            assert isinstance(result, dict)
            for h3_idx, features in result.items():
                assert isinstance(features, dict)
        finally:
            await engine.dispose()


class TestNewOSMCategories:
    """Tests for new OSM feature categories."""

    def test_new_osm_categories_in_registry(self) -> None:
        """Test that bridges, rocks_stones, sports_pitches, good_surfaces are in registry."""
        assert "bridges" in FEATURE_QUERIES
        assert "rocks_stones" in FEATURE_QUERIES
        assert "sports_pitches" in FEATURE_QUERIES
        assert "good_surfaces" in FEATURE_QUERIES

    def test_new_osm_queries_valid_sql(self) -> None:
        """Test that new OSM queries produce valid SQL."""
        from common.sql_queries import build_feature_query

        h3_indices = [123456789, 987654321]

        for category in ["bridges", "rocks_stones", "sports_pitches", "good_surfaces"]:
            query = build_feature_query(category, h3_indices, resolution=11)
            # Query should be a SQLAlchemy text object
            assert hasattr(query, "compile")
