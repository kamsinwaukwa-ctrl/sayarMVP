"""
Integration tests for rate limiting functionality.
"""
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rate_limiting import RateLimitConfig, MerchantRateLimitConfig
from src.utils.rate_limiter import get_rate_limiter, MemoryStore
from src.utils.wa_rate_limiter import check_wa_rate_limit
from src.workers.job_handlers import handle_wa_send
from src.models.errors import RateLimitedError, RetryableError

pytestmark = pytest.mark.asyncio

# Using fixtures from conftest.py

async def test_rate_limit_middleware(
    client: AsyncClient,
    merchant_token: str
):
    """Test rate limiting middleware with authenticated requests."""
    # Make requests up to the limit
    responses = []
    for _ in range(60):  # Default limit is 60/minute
        response = await client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        responses.append(response)
    
    # All should succeed
    assert all(r.status_code == 200 for r in responses)
    
    # Headers should be present
    assert "X-RateLimit-Limit" in responses[-1].headers
    assert "X-RateLimit-Remaining" in responses[-1].headers
    assert "X-RateLimit-Reset" in responses[-1].headers
    
    # Next request should fail
    response = await client.get(
        "/api/v1/merchants/me",
        headers={"Authorization": f"Bearer {merchant_token}"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    
    # Error response should follow BE-007 format
    error_data = response.json()
    assert error_data["ok"] is False
    assert error_data["error"]["code"] == "RATE_LIMITED"
    assert "retry_after" in error_data["error"]["details"]

async def test_ip_based_rate_limiting(client: AsyncClient):
    """Test rate limiting for unauthenticated requests."""
    # Make requests to login endpoint (stricter limit)
    responses = []
    for _ in range(30):  # Login limit is 30/minute
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"}
        )
        responses.append(response)
    
    # Should see 429 after limit exceeded
    assert any(r.status_code == 429 for r in responses)
    
    # Headers should indicate rate limit
    last_response = responses[-1]
    assert "X-RateLimit-Limit" in last_response.headers
    assert "X-RateLimit-Remaining" in last_response.headers
    assert int(last_response.headers["X-RateLimit-Remaining"]) == 0

async def test_whatsapp_rate_limiting():
    """Test WhatsApp message rate limiting."""
    merchant_id = "test-merchant"
    wa_limit = 10  # Low limit for testing
    
    # Reset rate limiter state
    get_rate_limiter()._reset_bucket(f"wa:merchant:{merchant_id}")
    
    # Send messages up to burst limit
    burst_limit = wa_limit // 4  # 25% burst limit
    for i in range(burst_limit):
        try:
            await check_wa_rate_limit(merchant_id, wa_limit)
        except RateLimitedError as e:
            assert False, f"Should not be rate limited on request {i}"
    
    # Next message should be rate limited
    with pytest.raises(RateLimitedError) as exc:
        await check_wa_rate_limit(merchant_id, wa_limit)
    
    assert exc.value.details["retry_after"] > 0
    assert datetime.fromisoformat(exc.value.details["reset_time"]) > datetime.now(timezone.utc)

async def test_wa_worker_rate_limiting(mocker):
    """Test rate limiting in WhatsApp worker."""
    merchant_id = "test-merchant"
    wa_limit = 5  # Low limit for testing
    
    # Mock WhatsApp API calls
    mocker.patch("src.integrations.whatsapp.WhatsAppIntegration.make_request", return_value={})
    
    # Reset rate limiter state
    get_rate_limiter()._reset_bucket(f"wa:merchant:{merchant_id}")
    
    # Send messages up to burst limit
    burst_limit = wa_limit // 4  # 25% burst limit
    for _ in range(burst_limit):
        await handle_wa_send(
            merchant_id=merchant_id,
            payload={
                "to": "+2348012345678",
                "type": "text",
                "content": {"text": "Test message"}
            },
            wa_rate_limit_per_hour=wa_limit
        )
    
    # Next message should raise RetryableError
    with pytest.raises(RetryableError) as exc:
        await handle_wa_send(
            merchant_id=merchant_id,
            payload={
                "to": "+2348012345678",
                "type": "text",
                "content": {"text": "Test message"}
            },
            wa_rate_limit_per_hour=wa_limit
        )
    
    assert exc.value.next_run_at is not None
    assert exc.value.next_run_at > datetime.now(timezone.utc)

async def test_rate_limit_api_endpoints(
    client: AsyncClient,
    admin_token: str,
    merchant_token: str
):
    """Test rate limit configuration API endpoints."""
    # Test getting own limits
    response = await client.get(
        "/api/v1/rate-limits/me",
        headers={"Authorization": f"Bearer {merchant_token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "api_rate_limit_per_minute" in data
    assert "wa_rate_limit_per_hour" in data
    
    # Test admin getting merchant limits
    merchant_id = "test-merchant"
    response = await client.get(
        f"/api/v1/rate-limits/{merchant_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Test admin updating limits
    new_config = {
        "merchant_id": merchant_id,
        "api_rate_limit_per_minute": 120,
        "api_burst_limit": 30,
        "wa_rate_limit_per_hour": 1500,
        "rate_limit_enabled": True
    }
    response = await client.patch(
        f"/api/v1/rate-limits/{merchant_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_config
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["api_rate_limit_per_minute"] == 120
    
    # Test admin resetting limits
    response = await client.post(
        f"/api/v1/rate-limits/{merchant_id}/reset",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify reset worked by checking new request
    response = await client.get(
        "/api/v1/merchants/me",
        headers={"Authorization": f"Bearer {merchant_token}"}
    )
    assert response.status_code == 200
    assert int(response.headers["X-RateLimit-Remaining"]) > 0

async def test_concurrent_rate_limiting(
    client: AsyncClient,
    merchant_token: str
):
    """Test rate limiting under concurrent load."""
    # Make concurrent requests
    async def make_request():
        return await client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
    
    # Create 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)
    
    # Should see mix of 200s and 429s
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)
    
    assert success_count <= 60  # Default limit
    assert rate_limited_count > 0  # Some should be rate limited
    assert success_count + rate_limited_count == 100
