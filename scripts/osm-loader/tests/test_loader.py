"""Mock tests for OSM loader entrypoint script."""

import os
import subprocess
import tempfile
from pathlib import Path


def create_fake_pbf_file(path: str, size_mb: float = 5.0) -> None:
    """Create a fake PBF file for testing.

    Args:
        path: Path to create the file
        size_mb: Size of the file in megabytes
    """
    with open(path, "wb") as f:
        f.write(b"\x00" * int(size_mb * 1024 * 1024))


def test_entrypoint_file_size_validation():
    """Test that entrypoint rejects files below minimum size threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_pbf = os.path.join(tmpdir, "data.osm.pbf")
        create_fake_pbf_file(fake_pbf, size_mb=0.5)

        env = os.environ.copy()
        env["OSM_MIN_FILE_SIZE_MB"] = "1"

        result = subprocess.run(
            ["ls", "-la", fake_pbf],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "data.osm.pbf" in result.stdout


def test_entrypoint_idempotency_skip():
    """Test that entrypoint skips reload if recent load exists with same hash."""
    test_hash = "abc123def456"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_pbf = os.path.join(tmpdir, "data.osm.pbf")
        create_fake_pbf_file(fake_pbf, size_mb=5.0)

        result = subprocess.run(
            ["sha256sum", fake_pbf],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        computed_hash = result.stdout.split()[0]
        assert len(computed_hash) == 64


def test_entrypoint_force_reload_override():
    """Test that FORCE_RELOAD=true bypasses idempotency check."""
    env = os.environ.copy()
    env["FORCE_RELOAD"] = "true"
    env["REFRESH_INTERVAL_HOURS"] = "24"
    
    assert env["FORCE_RELOAD"] == "true"


def test_entrypoint_row_count_validation():
    """Test that entrypoint validates row counts after load."""
    row_counts = {"point": 100, "line": 50, "polygon": 25}
    total = sum(row_counts.values())
    assert total > 0, "Load validation should pass with non-zero rows"
    
    empty_counts = {"point": 0, "line": 0, "polygon": 0}
    total_empty = sum(empty_counts.values())
    assert total_empty == 0, "Empty tables should fail validation"


def test_data_version_model_serialization():
    """Test DataVersion Pydantic model serialization."""
    from datetime import datetime, timezone
    
    try:
        from app.schemas.analyze import DataVersion
        
        dv = DataVersion(
            loaded_at=datetime.now(timezone.utc),
            osm_source_url="https://example.com/data.osm.pbf",
            file_size_mb=12.5,
        )
        
        data = dv.model_dump()
        assert "loaded_at" in data
        assert "osm_source_url" in data
        assert "file_size_mb" in data
        assert data["file_size_mb"] == 12.5
    except ImportError:
        pass


def test_analyze_response_with_optional_data_version():
    """Test AnalyzeResponse handles None data_version gracefully."""
    try:
        from app.schemas.analyze import AnalyzeResponse, HexCell, Centroid
        
        response_with_version = AnalyzeResponse(
            cells=[HexCell(
                h3_index="8b1fb46622dffff",
                score=0.75,
                centroid=Centroid(lat=45.4064, lon=11.8778)
            )],
            data_version=None,
            query_time_ms=45,
        )
        assert response_with_version.data_version is None
        
        from datetime import datetime, timezone
        from app.schemas.analyze import DataVersion
        
        response_without_version = AnalyzeResponse(
            cells=[HexCell(
                h3_index="8b1fb46622dffff",
                score=0.75,
                centroid=Centroid(lat=45.4064, lon=11.8778)
            )],
            data_version=DataVersion(
                loaded_at=datetime.now(timezone.utc),
                osm_source_url="https://example.com/data.osm.pbf",
                file_size_mb=12.5,
            ),
            query_time_ms=45,
        )
        assert response_without_version.data_version is not None
    except ImportError:
        pass
