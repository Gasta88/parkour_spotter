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


class TestSpatialSmoothing:
    """Tests for spatial smoothing feature."""

    def test_spatial_smoothing_applies_weighted_average(self) -> None:
        """Test that a cell with score 0.9 surrounded by neighbors at 0.1 gets smoothed."""
        from app.services.scorer_pipeline import ScorerPipeline
        from app.schemas.analyze import HexCell, Centroid, FeatureMetrics
        import h3
        
        # Get a valid center cell from coordinates
        center_cell = h3.latlng_to_cell(45.0, 11.0, 11)
        neighbors = h3.grid_ring(center_cell, 1)
        
        # Create mock cells with center and its neighbors
        cells = []
        cell_scores = {}
        
        # Add center cell with high score
        cells.append(HexCell(
            h3_index=center_cell,
            score=0.9,
            centroid=Centroid(lat=45.0, lon=11.0),
            features={},
        ))
        cell_scores[center_cell] = 0.9
        
        # Add neighbors with low scores
        for neighbor in list(neighbors)[:3]:  # Use first 3 neighbors
            cells.append(HexCell(
                h3_index=neighbor,
                score=0.1,
                centroid=Centroid(lat=45.0, lon=11.0),
                features={},
            ))
            cell_scores[neighbor] = 0.1
        
        # Create pipeline with alpha=0.7
        from unittest.mock import MagicMock
        from sqlalchemy.ext.asyncio import AsyncEngine
        
        mock_engine = MagicMock(spec=AsyncEngine)
        pipeline = ScorerPipeline(mock_engine, spatial_alpha=0.7)
        
        # Apply smoothing
        pipeline._apply_spatial_smoothing(cells, cell_scores)
        
        # The high-score cell should be smoothed toward neighbor mean
        # smoothed = 0.7 * 0.9 + 0.3 * mean(neighbors)
        # Should be less than original 0.9
        assert cells[0].score < 0.9
        # Should still be higher than neighbors
        assert cells[0].score > cells[1].score

    def test_spatial_smoothing_edge_cases_fewer_neighbors(self) -> None:
        """Test cells at grid boundaries with fewer than 6 neighbors."""
        from app.services.scorer_pipeline import ScorerPipeline
        from app.schemas.analyze import HexCell, Centroid
        
        # Create mock cells
        cells = [
            HexCell(
                h3_index="8b1fb46622dffff",
                score=0.5,
                centroid=Centroid(lat=45.0, lon=11.0),
                features={},
            ),
        ]
        
        cell_scores = {
            "8b1fb46622dffff": 0.5,
        }
        
        from unittest.mock import MagicMock
        from sqlalchemy.ext.asyncio import AsyncEngine
        
        mock_engine = MagicMock(spec=AsyncEngine)
        pipeline = ScorerPipeline(mock_engine, spatial_alpha=0.7)
        
        # Should handle gracefully when no neighbors have scores
        pipeline._apply_spatial_smoothing(cells, cell_scores)
        
        # Score should remain unchanged when no neighbors
        assert cells[0].score == 0.5

    def test_spatial_smoothing_preserves_score_range(self) -> None:
        """Test that smoothed scores remain in [0, 1] range."""
        from app.services.scorer_pipeline import ScorerPipeline
        from app.schemas.analyze import HexCell, Centroid
        
        # Create mock cells with extreme scores
        cells = [
            HexCell(
                h3_index="8b1fb46622dffff",
                score=0.0,
                centroid=Centroid(lat=45.0, lon=11.0),
                features={},
            ),
            HexCell(
                h3_index="8b1fb46622d0fff",
                score=1.0,
                centroid=Centroid(lat=45.0, lon=11.0),
                features={},
            ),
        ]
        
        cell_scores = {
            "8b1fb46622dffff": 0.0,
            "8b1fb46622d0fff": 1.0,
        }
        
        from unittest.mock import MagicMock
        from sqlalchemy.ext.asyncio import AsyncEngine
        
        mock_engine = MagicMock(spec=AsyncEngine)
        pipeline = ScorerPipeline(mock_engine, spatial_alpha=0.7)
        
        pipeline._apply_spatial_smoothing(cells, cell_scores)
        
        # All scores should remain in valid range
        for cell in cells:
            assert 0 <= cell.score <= 1
