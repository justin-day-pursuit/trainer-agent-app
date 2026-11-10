"""
Health Check and Service Connectivity Tests.

Confirms that FastAPI starts up cleanly and returns the expected status payloads.
"""

import pytest


@pytest.mark.parametrize("_acceptance_case", [None], ids=["AC-DEPLOY-4"])
def test_root_health_endpoint_returns_status_ok(client, _acceptance_case):
    """
    Verifies that Render's GET /health probe receives the required status body.

    The named parameter keeps the deployment acceptance ID visible in pytest output.
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
