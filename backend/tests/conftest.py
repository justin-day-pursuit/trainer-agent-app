"""
Pytest Test Configuration and Fixtures.

Configures test clients and mock dependencies for backend automated tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    Provides a synchronous TestClient to make test requests against the FastAPI app.
    """
    with TestClient(app) as test_client:
        yield test_client
