"""Tests for health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    """Test that GET /health returns 200."""
    response = client.get("/health")

    assert response.status_code == 200


def test_health_response_schema() -> None:
    """Test that response matches expected schema."""
    response = client.get("/health")

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "api"
    assert "version" in data
