"""Unit tests for Pydantic feature schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.analyze import (
    AnalyzeResponse,
    Centroid,
    FeatureMetrics,
    HexCell,
)


class TestCentroid:
    """Tests for Centroid schema."""

    def test_valid_centroid(self) -> None:
        """Test creating a valid Centroid."""
        c = Centroid(lat=45.4064, lon=11.8778)
        assert c.lat == 45.4064
        assert c.lon == 11.8778

    def test_centroid_serialization(self) -> None:
        """Test Centroid serializes to dict."""
        c = Centroid(lat=45.4064, lon=11.8778)
        d = c.model_dump()
        assert d == {"lat": 45.4064, "lon": 11.8778}


class TestFeatureMetrics:
    """Tests for FeatureMetrics schema."""

    def test_valid_metrics_all_fields(self) -> None:
        """Test creating FeatureMetrics with all fields."""
        m = FeatureMetrics(count=12, total_length_m=45.3, total_area_m2=320.0)
        assert m.count == 12
        assert m.total_length_m == 45.3
        assert m.total_area_m2 == 320.0

    def test_valid_metrics_defaults(self) -> None:
        """Test that FeatureMetrics defaults to zeros."""
        m = FeatureMetrics()
        assert m.count == 0
        assert m.total_length_m == 0.0
        assert m.total_area_m2 == 0.0

    def test_negative_count_rejected(self) -> None:
        """Test that negative count is rejected."""
        with pytest.raises(ValidationError):
            FeatureMetrics(count=-1)

    def test_negative_length_rejected(self) -> None:
        """Test that negative length is rejected."""
        with pytest.raises(ValidationError):
            FeatureMetrics(total_length_m=-1.0)

    def test_negative_area_rejected(self) -> None:
        """Test that negative area is rejected."""
        with pytest.raises(ValidationError):
            FeatureMetrics(total_area_m2=-1.0)

    def test_count_only(self) -> None:
        """Test FeatureMetrics with only count (point features)."""
        m = FeatureMetrics(count=5)
        assert m.count == 5
        assert m.total_length_m == 0.0
        assert m.total_area_m2 == 0.0


class TestHexCell:
    """Tests for HexCell schema."""

    def test_valid_hex_cell(self) -> None:
        """Test creating a valid HexCell."""
        cell = HexCell(
            h3_index="8b1fb46622dffff",
            score=0.72,
            centroid=Centroid(lat=45.4064, lon=11.8778),
        )
        assert cell.h3_index == "8b1fb46622dffff"
        assert cell.score == 0.72
        assert cell.features == {}

    def test_hex_cell_with_features(self) -> None:
        """Test HexCell with feature breakdown."""
        cell = HexCell(
            h3_index="8b1fb46622dffff",
            score=0.72,
            centroid=Centroid(lat=45.4064, lon=11.8778),
            features={
                "walls": FeatureMetrics(count=12, total_length_m=45.3),
                "steps": FeatureMetrics(count=3, total_length_m=18.0),
            },
        )
        assert "walls" in cell.features
        assert cell.features["walls"].count == 12

    def test_hex_cell_score_bounds(self) -> None:
        """Test that score must be in [0, 1]."""
        # Valid scores
        HexCell(
            h3_index="8b1fb46622dffff",
            score=0.0,
            centroid=Centroid(lat=45.4064, lon=11.8778),
        )
        HexCell(
            h3_index="8b1fb46622dffff",
            score=1.0,
            centroid=Centroid(lat=45.4064, lon=11.8778),
        )

    def test_hex_cell_score_too_high(self) -> None:
        """Test that score > 1 is rejected."""
        with pytest.raises(ValidationError):
            HexCell(
                h3_index="8b1fb46622dffff",
                score=1.5,
                centroid=Centroid(lat=45.4064, lon=11.8778),
            )

    def test_hex_cell_score_too_low(self) -> None:
        """Test that score < 0 is rejected."""
        with pytest.raises(ValidationError):
            HexCell(
                h3_index="8b1fb46622dffff",
                score=-0.1,
                centroid=Centroid(lat=45.4064, lon=11.8778),
            )

    def test_hex_cell_serialization(self) -> None:
        """Test HexCell serializes correctly."""
        cell = HexCell(
            h3_index="8b1fb46622dffff",
            score=0.72,
            centroid=Centroid(lat=45.4064, lon=11.8778),
            features={"walls": FeatureMetrics(count=12, total_length_m=45.3)},
        )
        d = cell.model_dump()
        assert d["h3_index"] == "8b1fb46622dffff"
        assert d["score"] == 0.72
        assert d["features"]["walls"]["count"] == 12


class TestAnalyzeResponse:
    """Tests for AnalyzeResponse schema."""

    def test_valid_response(self) -> None:
        """Test creating a valid AnalyzeResponse."""
        resp = AnalyzeResponse(
            cells=[
                HexCell(
                    h3_index="8b1fb46622dffff",
                    score=0.72,
                    centroid=Centroid(lat=45.4064, lon=11.8778),
                )
            ],
            query_time_ms=3200,
        )
        assert len(resp.cells) == 1
        assert resp.query_time_ms == 3200

    def test_response_with_data_version(self) -> None:
        """Test AnalyzeResponse with data_version metadata."""
        from datetime import datetime, timezone

        resp = AnalyzeResponse(
            cells=[],
            data_version={
                "loaded_at": datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
                "osm_source_url": "https://example.com/data.osm.pbf",
                "file_size_mb": 12.5,
            },
            query_time_ms=100,
        )
        assert resp.data_version is not None
        assert resp.data_version.osm_source_url == "https://example.com/data.osm.pbf"

    def test_response_with_none_data_version(self) -> None:
        """Test AnalyzeResponse with data_version=None."""
        resp = AnalyzeResponse(
            cells=[],
            data_version=None,
            query_time_ms=100,
        )
        assert resp.data_version is None

    def test_response_serialization(self) -> None:
        """Test AnalyzeResponse serializes to JSON-compatible dict."""

        resp = AnalyzeResponse(
            cells=[
                HexCell(
                    h3_index="8b1fb46622dffff",
                    score=0.72,
                    centroid=Centroid(lat=45.4064, lon=11.8778),
                    features={
                        "walls": FeatureMetrics(count=12, total_length_m=45.3),
                    },
                )
            ],
            query_time_ms=3200,
        )
        d = resp.model_dump(mode="json")
        assert "cells" in d
        assert "query_time_ms" in d
        assert d["cells"][0]["features"]["walls"]["count"] == 12
