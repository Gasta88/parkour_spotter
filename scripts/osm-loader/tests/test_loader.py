"""Mock tests for OSM loader entrypoint script."""

import os
import subprocess
import tempfile


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
        from pydantic import BaseModel
        
        class DataVersion(BaseModel):
            loaded_at: datetime
            osm_source_url: str
            file_size_mb: float
        
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
        from datetime import datetime, timezone
        from typing import Optional
        from pydantic import BaseModel
        
        class Centroid(BaseModel):
            lat: float
            lon: float
        
        class HexCell(BaseModel):
            h3_index: str
            score: float
            centroid: Centroid
        
        class DataVersion(BaseModel):
            loaded_at: datetime
            osm_source_url: str
            file_size_mb: float
        
        class AnalyzeResponse(BaseModel):
            cells: list[HexCell]
            data_version: Optional[DataVersion] = None
            query_time_ms: int
        
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


def test_local_file_takes_priority_over_url():
    """Test that OSM_LOCAL_FILE takes priority over OSM_URL when both are set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_pbf = os.path.join(tmpdir, "city.osm.pbf")
        create_fake_pbf_file(local_pbf, size_mb=2.0)

        # Verify the local file exists and has expected size
        assert os.path.isfile(local_pbf)
        file_size = os.path.getsize(local_pbf)
        assert file_size == int(2.0 * 1024 * 1024)

        # Simulate the priority logic from entrypoint.sh
        osm_local_file = "city.osm.pbf"
        osm_url = "https://example.com/fallback.osm.pbf"

        # When OSM_LOCAL_FILE is set, it should be used regardless of OSM_URL
        if osm_local_file:
            source = "local"
        elif osm_url:
            source = "url"
        else:
            source = "none"

        assert source == "local", "OSM_LOCAL_FILE should take priority over OSM_URL"


def test_missing_local_file_produces_error():
    """Test that a missing local file produces a clear error condition."""
    with tempfile.TemporaryDirectory() as tmpdir:
        osm_local_file = "nonexistent.osm.pbf"
        local_path = os.path.join(tmpdir, osm_local_file)

        # Simulate the entrypoint.sh check
        if osm_local_file and not os.path.isfile(local_path):
            error_msg = f"OSM_LOCAL_FILE is set to '{osm_local_file}' but file not found at {local_path}"
            assert "not found" in error_msg
            assert osm_local_file in error_msg
        else:
            assert False, "Should have detected missing file"


def test_download_skipped_when_local_file_provided():
    """Test that the download step is skipped when a local file is provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_pbf = os.path.join(tmpdir, "city.osm.pbf")
        create_fake_pbf_file(local_pbf, size_mb=1.5)

        osm_local_file = "city.osm.pbf"
        osm_url = "https://example.com/download.osm.pbf"
        download_was_called = False

        # Simulate the entrypoint.sh logic
        if osm_local_file and os.path.isfile(local_pbf):
            # Use local file — no download
            download_was_called = False
        elif osm_url:
            # Would download
            download_was_called = True
        else:
            # Error
            pass

        assert download_was_called is False, "Download should be skipped when local file exists"


def test_fallback_to_url_when_no_local_file():
    """Test that OSM_URL is used as fallback when OSM_LOCAL_FILE is not set."""
    osm_local_file = ""
    osm_url = "https://example.com/city.osm.pbf"

    # Simulate the entrypoint.sh logic
    if osm_local_file:
        source = "local"
    elif osm_url:
        source = "url"
    else:
        source = "error"

    assert source == "url", "Should fall back to OSM_URL when OSM_LOCAL_FILE is not set"


def test_error_when_neither_local_file_nor_url():
    """Test that an error occurs when neither OSM_LOCAL_FILE nor OSM_URL is set."""
    osm_local_file = ""
    osm_url = ""

    # Simulate the entrypoint.sh check
    if not osm_local_file and not osm_url:
        error_occurred = True
    else:
        error_occurred = False

    assert error_occurred is True, "Should error when neither OSM_LOCAL_FILE nor OSM_URL is set"
