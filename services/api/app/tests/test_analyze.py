"""Tests for analyze endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_returns_200() -> None:
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
    assert len(data["cells"]) > 0


def test_analyze_response_schema() -> None:
    """Test that response matches expected schema."""
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

    cell = data["cells"][0]
    assert "h3_index" in cell
    assert "score" in cell
    assert "centroid" in cell
    assert "lat" in cell["centroid"]
    assert "lon" in cell["centroid"]


def test_analyze_missing_fields_returns_422() -> None:
    """Test that missing fields return 422."""
    response = client.post(
        "/analyze",
        json={
            "lat": 45.44,
        },
    )

    assert response.status_code == 422


def test_analyze_invalid_lat_returns_422() -> None:
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


def test_analyze_radius_too_large_returns_422() -> None:
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
