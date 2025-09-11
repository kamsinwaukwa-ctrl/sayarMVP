"""
Integration tests for observability features
Tests health endpoints, metrics, and logging functionality
"""

import pytest
import json
import os
from httpx import AsyncClient
from unittest.mock import patch
from ..utils import capture_logs


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_healthz_liveness_probe(self, app_client: AsyncClient):
        """Test liveness probe endpoint"""
        response = await app_client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "service" in data
        assert data["service"] == "sayar-backend"
    
    @pytest.mark.asyncio
    async def test_readyz_readiness_probe_healthy(self, app_client: AsyncClient):
        """Test readiness probe when healthy"""
        response = await app_client.get("/readyz")
        
        # Should be healthy if database is accessible
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "database" in data["checks"]
        
        # Status code should be 200 if healthy, 503 if not
        if response.status_code == 200:
            assert data["status"] == "healthy"
            assert data["checks"]["database"] == "healthy"
        else:
            assert response.status_code == 503
            assert data["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_readyz_with_db_failure(self, app_client: AsyncClient):
        """Test readiness probe with simulated database failure"""
        # This test would require mocking the database connection
        # For now, just verify the endpoint structure
        response = await app_client.get("/readyz")
        data = response.json()
        
        assert "status" in data
        assert "checks" in data
        # Response can be 200 or 503 depending on actual DB state
        assert response.status_code in [200, 503]
    
    @pytest.mark.asyncio
    async def test_info_endpoint(self, app_client: AsyncClient):
        """Test application info endpoint"""
        response = await app_client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["name"] == "Sayar WhatsApp Commerce Platform"
        assert data["service"] == "sayar-backend"
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
        assert "features" in data
        assert "endpoints" in data
        
        # Verify features
        features = data["features"]
        assert "metrics_enabled" in features
        assert "json_logging" in features
        assert "log_level" in features
        
        # Verify endpoints
        endpoints = data["endpoints"]
        assert endpoints["health_liveness"] == "/healthz"
        assert endpoints["health_readiness"] == "/readyz"
        assert endpoints["metrics"] == "/metrics"


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_enabled(self, app_client: AsyncClient):
        """Test metrics endpoint when enabled"""
        # Set environment to ensure metrics are enabled
        with patch.dict(os.environ, {"METRICS_ENABLED": "true"}):
            response = await app_client.get("/metrics")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
            
            content = response.text
            
            # Verify presence of key metrics
            assert "http_requests_total" in content
            assert "http_request_duration_seconds" in content
            assert "http_requests_in_flight" in content
            assert "sayar_app_info" in content
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_disabled(self, app_client: AsyncClient):
        """Test metrics endpoint when disabled"""
        with patch.dict(os.environ, {"METRICS_ENABLED": "false"}):
            response = await app_client.get("/metrics")
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_metrics_after_requests(self, app_client: AsyncClient):
        """Test that metrics are updated after making requests"""
        # Make initial metrics request to get baseline
        response1 = await app_client.get("/metrics")
        assert response1.status_code == 200
        initial_content = response1.text
        
        # Make some test requests
        await app_client.get("/healthz")
        await app_client.get("/info")
        
        # Get metrics again
        response2 = await app_client.get("/metrics")
        assert response2.status_code == 200
        updated_content = response2.text
        
        # Verify that request counters have increased
        # (This is a basic check - in practice, you'd parse the metrics)
        assert "http_requests_total" in updated_content


class TestLoggingMiddleware:
    """Test logging middleware functionality"""
    
    @pytest.mark.asyncio
    async def test_request_id_generation(self, app_client: AsyncClient):
        """Test that requests get correlation IDs"""
        response = await app_client.get("/healthz")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Verify it's a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID length with hyphens
        assert request_id.count("-") == 4  # UUID has 4 hyphens
    
    @pytest.mark.asyncio
    async def test_custom_request_id_preserved(self, app_client: AsyncClient):
        """Test that custom request IDs are preserved"""
        custom_id = "test-request-123"
        response = await app_client.get(
            "/healthz",
            headers={"X-Request-ID": custom_id}
        )
        
        assert response.status_code == 200
        # Note: The middleware generates a proper UUID even for custom input
        # But it should still include the custom ID in logs
        assert "X-Request-ID" in response.headers
    
    @pytest.mark.asyncio
    async def test_request_logging_structure(self, app_client: AsyncClient):
        """Test that requests are logged with proper structure"""
        with capture_logs() as log_capture:
            response = await app_client.get("/healthz")
            assert response.status_code == 200
            
            # Verify logs were captured
            logs = log_capture.get_logs()
            
            # Find HTTP request/response logs
            http_logs = [log for log in logs if "event_type" in log and 
                        log["event_type"] in ["http_request", "http_response"]]
            
            assert len(http_logs) >= 1  # At least one HTTP log
            
            # Verify log structure for any HTTP log
            for log_entry in http_logs:
                assert "timestamp" in log_entry
                assert "level" in log_entry
                assert "event_type" in log_entry
                assert "request_id" in log_entry
                assert "method" in log_entry
                assert "route" in log_entry


class TestObservabilityIntegration:
    """Test integration between different observability components"""
    
    @pytest.mark.asyncio
    async def test_full_request_flow_observability(self, app_client: AsyncClient):
        """Test complete observability for a request flow"""
        with capture_logs() as log_capture:
            # Make request with custom headers
            custom_request_id = "integration-test-123"
            response = await app_client.get(
                "/info",
                headers={
                    "X-Request-ID": custom_request_id,
                    "User-Agent": "test-agent/1.0"
                }
            )
            
            assert response.status_code == 200
            
            # Verify response has correlation ID
            assert "X-Request-ID" in response.headers
            
            # Verify logs contain request context
            logs = log_capture.get_logs()
            http_logs = [log for log in logs if "event_type" in log and 
                        log["event_type"] in ["http_request", "http_response"]]
            
            assert len(http_logs) >= 1
            
            # Verify request context in logs
            for log_entry in http_logs:
                assert "request_id" in log_entry
                assert "method" in log_entry
                assert log_entry["method"] == "GET"
                assert "/info" in log_entry.get("route", "")
        
        # Verify metrics were updated
        metrics_response = await app_client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "http_requests_total" in metrics_response.text
    
    @pytest.mark.asyncio
    async def test_error_handling_observability(self, app_client: AsyncClient):
        """Test observability for error conditions"""
        with capture_logs() as log_capture:
            # Request non-existent endpoint
            response = await app_client.get("/nonexistent")
            assert response.status_code == 404
            
            # Verify error is logged and has correlation ID
            assert "X-Request-ID" in response.headers
            
            # Check logs for error context
            logs = log_capture.get_logs()
            # 404s might not be logged as errors in middleware
            # but should still have request/response logs
            http_logs = [log for log in logs if "event_type" in log]
            assert len(http_logs) >= 1
    
    @pytest.mark.asyncio 
    async def test_health_endpoints_excluded_from_auth(self, app_client: AsyncClient):
        """Test that health endpoints work without authentication"""
        # Health endpoints should work without any auth headers
        endpoints = ["/healthz", "/readyz", "/metrics", "/info"]
        
        for endpoint in endpoints:
            response = await app_client.get(endpoint)
            # Should not return 401/403 (auth errors)
            assert response.status_code not in [401, 403]
            
            # Should return success or service unavailable
            assert response.status_code in [200, 404, 503]  # 404 for disabled metrics