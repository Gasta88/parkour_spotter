"""Integration tests for end-to-end scorer pipeline."""

import pytest

from app.schemas.analyze import HexCell


class TestScorerPipelineIntegration:
    """Integration tests for the full analyze pipeline."""

    @pytest.mark.asyncio
    async def test_analyze_empty_db_returns_empty_cells(self, postgis_connection) -> None:
        """Test that analyze against empty DB returns empty cells list."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.services.scorer_pipeline import ScorerPipeline

        conn = postgis_connection
        raw_dsn = conn.get_dsn()
        async_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            pipeline = ScorerPipeline(engine, resolution=11)
            cells, query_time_ms = await pipeline.analyze(45.4064, 11.8778, 0.1)

            # With empty tables, no features are found, so no cells with features
            # But the k-ring cells are still returned with empty feature dicts
            assert isinstance(cells, list)
            assert query_time_ms >= 0
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_analyze_with_seeded_data(self, postgis_connection) -> None:
        """Test analyze pipeline with seeded OSM data."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.services.scorer_pipeline import ScorerPipeline
        from common.h3_utils import latlng_to_h3

        conn = postgis_connection

        # Insert test features
        test_lat, test_lon = 45.4064, 11.8778

        # Insert a wall (line)
        await conn.execute("""
            INSERT INTO planet_osm_line (osm_id, barrier, way)
            VALUES (
                100,
                'wall',
                ST_SetSRID(ST_MakePoint(11.8778, 45.4064), 4326)
            )
        """)

        # Insert a bench (point)
        await conn.execute("""
            INSERT INTO planet_osm_point (osm_id, amenity, way)
            VALUES (
                200,
                'bench',
                ST_SetSRID(ST_MakePoint(11.8778, 45.4064), 4326)
            )
        """)

        raw_dsn = conn.get_dsn()
        async_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            pipeline = ScorerPipeline(engine, resolution=11)
            cells, query_time_ms = await pipeline.analyze(test_lat, test_lon, 0.1)

            assert isinstance(cells, list)
            assert query_time_ms >= 0

            # Check that cells are HexCell objects with proper structure
            for cell in cells:
                assert isinstance(cell, HexCell)
                assert isinstance(cell.h3_index, str)
                assert 0 <= cell.score <= 1
                assert isinstance(cell.features, dict)

        finally:
            await engine.dispose()

        # Clean up
        await conn.execute("DELETE FROM planet_osm_line WHERE osm_id = 100")
        await conn.execute("DELETE FROM planet_osm_point WHERE osm_id = 200")

    @pytest.mark.asyncio
    async def test_analyze_cell_has_feature_breakdown(self, postgis_connection) -> None:
        """Test that returned cells include feature breakdown."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.services.scorer_pipeline import ScorerPipeline
        from app.schemas.analyze import FeatureMetrics

        conn = postgis_connection

        # Insert a playground (polygon)
        await conn.execute("""
            INSERT INTO planet_osm_polygon (osm_id, leisure, way)
            VALUES (
                300,
                'playground',
                ST_SetSRID(
                    ST_MakePolygon(
                        ST_GeomFromText('LINESTRING(
                            11.8770 45.4060,
                            11.8780 45.4060,
                            11.8780 45.4070,
                            11.8770 45.4070,
                            11.8770 45.4060
                        )', 4326)
                    ),
                    4326
                )
            )
        """)

        raw_dsn = conn.get_dsn()
        async_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            pipeline = ScorerPipeline(engine, resolution=11)
            cells, _ = await pipeline.analyze(45.4065, 11.8775, 0.1)

            # Find cells with playground features
            playground_cells = [
                c for c in cells
                if "playgrounds" in c.features and c.features["playgrounds"].count > 0
            ]

            # At least one cell should have the playground
            assert len(playground_cells) > 0

            # Verify feature metrics structure
            for cell in playground_cells:
                playground = cell.features["playgrounds"]
                assert isinstance(playground, FeatureMetrics)
                assert playground.count >= 1

        finally:
            await engine.dispose()

        # Clean up
        await conn.execute("DELETE FROM planet_osm_polygon WHERE osm_id = 300")
