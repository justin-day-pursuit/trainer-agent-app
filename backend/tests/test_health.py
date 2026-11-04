"""
Health Check and Service Connectivity Tests.

Confirms that FastAPI starts up cleanly and returns the expected status payloads.
"""


def test_root_health_endpoint(client):
    """
    Verifies that GET /health responds with 200 OK and expected structure.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data


def test_api_v1_health_endpoint(client):
    """
    Verifies that GET /api/v1/health responds with 200 OK.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
