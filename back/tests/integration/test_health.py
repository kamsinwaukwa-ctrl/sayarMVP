"""
Integration tests for health check endpoints
"""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(test_client: TestClient):
    """Test root endpoint returns correct response"""
    response = test_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Sayar WhatsApp Commerce API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"


def test_health_check_endpoint(test_client: TestClient):
    """Test health check endpoint"""
    response = test_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sayar-backend"
    assert "timestamp" in data


def test_api_health_check_endpoint(test_client: TestClient):
    """Test API v1 health check endpoint"""
    response = test_client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"
    assert "timestamp" in data
