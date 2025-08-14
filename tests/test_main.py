import pytest
from fastapi.testclient import TestClient

def test_root_endpoint(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "University Matcher API"
    assert data["version"] == "1.0.0"

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_cors_headers(client: TestClient):
    """Test that CORS headers are properly set."""
    # Test CORS headers by making a request with Origin header
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # CORS headers should be present when Origin is set
    assert "access-control-allow-origin" in response.headers