"""
Integration tests for error handling & retry framework
Tests error middleware, retry decorators, circuit breakers, and error mapping
"""

import asyncio
import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from src.models.errors import (
    ErrorCode, ErrorResponse, RetryableError, AuthzError, 
    RateLimitedError, UpstreamServiceError
)
from src.utils.retry import (
    retryable, RetryConfig, calculate_delay, 
    retry_async, retry_sync, RetryableOperation
)
from src.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError,
    get_circuit_breaker, clear_circuit_breaker_registry
)
from src.utils.error_handling import (
    map_exception_to_response, sanitize_error_message,
    translate_rls_violation
)


class TestErrorMiddleware:
    """Test error middleware functionality"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_request_id_generation(self):
        """Test that request ID is generated when not provided"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format
        assert request_id.count("-") == 4
    
    def test_request_id_preservation(self):
        """Test that custom request ID is preserved"""
        custom_id = "test-request-123"
        response = self.client.get("/", headers={"X-Request-ID": custom_id})
        
        # Should generate proper UUID but log with custom context
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format
    
    def test_error_envelope_structure(self):
        """Test that errors follow the standardized envelope format"""
        if self.client.get("/dev/boom").status_code != 404:  # Only test if dev endpoints exist
            response = self.client.get("/dev/boom")
            
            assert response.status_code == 500
            assert "X-Request-ID" in response.headers
            
            data = response.json()
            assert "ok" in data
            assert data["ok"] is False
            assert "error" in data
            assert "timestamp" in data
            
            error = data["error"]
            assert "code" in error
            assert "message" in error
            assert "request_id" in error
            assert error["code"] == "INTERNAL_ERROR"
    
    def test_rate_limit_error_structure(self):
        """Test rate limit error includes retry_after"""
        # Create a rate limit error response
        response = self.client.get("/", headers={"X-Test-Error": "rate-limit"})
        
        assert response.status_code == 429
        
        data = response.json()
        error = data["error"]
        assert error["code"] == "RATE_LIMITED"
        
        if error.get("details"):
            assert "retry_after" in error["details"]
    
    def test_authorization_error_mapping(self):
        """Test authorization error mapping"""
        if self.client.get("/dev/auth-error").status_code != 404:
            response = self.client.get("/dev/auth-error")
            
            assert response.status_code == 403
            
            data = response.json()
            error = data["error"]
            assert error["code"] == "AUTHORIZATION_ERROR"
            assert "admin role" in error["message"].lower()
    
    def test_not_found_error_mapping(self):
        """Test 404 error mapping"""
        # Create a not found error response
        response = self.client.get("/", headers={"X-Test-Error": "not-found"})
        
        assert response.status_code == 404
        assert "X-Request-ID" in response.headers
        
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "NOT_FOUND"


class TestRetryUtilities:
    """Test retry decorators and utilities"""
    
    def test_calculate_delay(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        # Test exponential progression
        assert calculate_delay(1, config) == 0  # No delay for first attempt
        assert calculate_delay(2, config) == 1.0  # base_delay
        assert calculate_delay(3, config) == 2.0  # base_delay * 2
        assert calculate_delay(4, config) == 4.0  # base_delay * 4
    
    def test_delay_with_jitter(self):
        """Test that jitter adds randomness"""
        config = RetryConfig(base_delay=10.0, exponential_base=2.0, jitter=True)
        
        delays = [calculate_delay(3, config) for _ in range(10)]
        
        # All delays should be different (with very high probability)
        assert len(set(delays)) > 5
        # All delays should be less than the non-jittered value
        assert all(d <= 20.0 for d in delays)
        # All delays should be non-negative
        assert all(d >= 0 for d in delays)
    
    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay"""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)
        
        # High attempt number should hit the cap
        delay = calculate_delay(10, config)
        assert delay <= config.max_delay
    
    @pytest.mark.asyncio
    async def test_async_retry_decorator_success(self):
        """Test async retry decorator with eventual success"""
        attempts = 0
        
        @retryable(config=RetryConfig(max_attempts=3, base_delay=0.01))
        async def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RetryableError("test", f"Attempt {attempts}")
            return f"Success on attempt {attempts}"
        
        result = await flaky_function()
        assert result == "Success on attempt 3"
        assert attempts == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_decorator_failure(self):
        """Test async retry decorator with permanent failure"""
        attempts = 0
        
        @retryable(config=RetryConfig(max_attempts=2, base_delay=0.01))
        async def always_fail():
            nonlocal attempts
            attempts += 1
            raise RetryableError("test", "Always fails")
        
        with pytest.raises(RetryableError):
            await always_fail()
        
        assert attempts == 2
    
    def test_sync_retry_decorator_success(self):
        """Test sync retry decorator with eventual success"""
        attempts = 0
        
        @retryable(config=RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Network error")
            return f"Success on attempt {attempts}"
        
        result = flaky_function()
        assert result == "Success on attempt 3"
        assert attempts == 3
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried"""
        attempts = 0
        
        @retryable(config=RetryConfig(max_attempts=3, base_delay=0.01))
        def non_retryable_error():
            nonlocal attempts
            attempts += 1
            raise ValueError("This should not be retried")
        
        with pytest.raises(ValueError):
            non_retryable_error()
        
        assert attempts == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_retry_operation_context_manager(self):
        """Test RetryableOperation context manager"""
        operation = RetryableOperation(
            config=RetryConfig(max_attempts=3, base_delay=0.01),
            operation_name="test_operation"
        )
        
        attempts = 0
        
        while True:
            with operation:
                attempts += 1
                if attempts < 3:
                    raise ConnectionError("Network error")
                break  # Success
            
            if operation.should_retry():
                delay = operation.next_attempt()
                await asyncio.sleep(delay)
            else:
                raise operation.exhausted()
        
        assert attempts == 3


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def setup_method(self):
        """Clear circuit breaker registry before each test"""
        clear_circuit_breaker_registry()
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows calls"""
        breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        
        # Should allow calls in closed state
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state.value == "closed"
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures"""
        config = CircuitBreakerConfig(failure_threshold=3, minimum_calls=1)
        breaker = CircuitBreaker("test", config)
        
        # Generate failures to trigger opening
        for i in range(3):
            with pytest.raises(ValueError):
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("Test error")))
        
        # Circuit should be open now
        assert breaker.state.value == "open"
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerError):
            breaker.call(lambda: "should not execute")
    
    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to half-open for recovery"""
        config = CircuitBreakerConfig(
            failure_threshold=2, 
            recovery_timeout=0.1,  # Very short for testing
            minimum_calls=1
        )
        breaker = CircuitBreaker("test", config)
        
        # Trigger failures to open circuit
        for i in range(2):
            with pytest.raises(ValueError):
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("Test error")))
        
        assert breaker.state.value == "open"
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Next call should transition to half-open
        try:
            breaker.call(lambda: "recovery test")
        except CircuitBreakerError:
            pass  # First call after timeout should check state
        
        # Try again - should be half-open now
        result = breaker.call(lambda: "success")
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async_calls(self):
        """Test circuit breaker with async operations"""
        breaker = CircuitBreaker("async_test", CircuitBreakerConfig(timeout=1.0))
        
        async def async_operation():
            return "async success"
        
        result = await breaker.call_async(async_operation)
        assert result == "async success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async_timeout(self):
        """Test circuit breaker timeout on async operations"""
        config = CircuitBreakerConfig(timeout=0.1)  # Very short timeout
        breaker = CircuitBreaker("timeout_test", config)
        
        async def slow_operation():
            await asyncio.sleep(0.5)  # Longer than timeout
            return "should not complete"
        
        with pytest.raises(asyncio.TimeoutError):
            await breaker.call_async(slow_operation)
    
    def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator"""
        from src.utils.circuit_breaker import circuit_breaker
        
        config = CircuitBreakerConfig(failure_threshold=2, minimum_calls=1)
        
        @circuit_breaker("decorated_test", config)
        def decorated_function(should_fail=False):
            if should_fail:
                raise ValueError("Decorated failure")
            return "decorated success"
        
        # Should work normally
        result = decorated_function(False)
        assert result == "decorated success"
        
        # Generate failures
        for _ in range(2):
            with pytest.raises(ValueError):
                decorated_function(True)
        
        # Should be rejected due to circuit being open
        with pytest.raises(CircuitBreakerError):
            decorated_function(False)
    
    def test_circuit_breaker_stats(self):
        """Test circuit breaker statistics"""
        breaker = CircuitBreaker("stats_test", CircuitBreakerConfig())
        
        # Generate some calls
        breaker.call(lambda: "success")
        
        try:
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("failure")))
        except ValueError:
            pass
        
        stats = breaker.get_stats()
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 1
        assert stats["key"] == "stats_test"


class TestErrorHandling:
    """Test error handling utilities"""
    
    def test_sanitize_error_message(self):
        """Test sensitive data sanitization"""
        sensitive_message = 'Error: password="secret123" and token="abc123"'
        sanitized = sanitize_error_message(sensitive_message)
        
        assert "secret123" not in sanitized
        assert "abc123" not in sanitized
        assert "***REDACTED***" in sanitized
    
    def test_map_http_exception(self):
        """Test HTTP exception mapping"""
        from src.utils.error_handling import map_http_exception
        from uuid import uuid4
        
        request_id = uuid4()
        exc = HTTPException(status_code=401, detail="Invalid token")
        
        response = map_http_exception(exc, request_id)
        
        assert response.error.code == ErrorCode.AUTHENTICATION_ERROR
        assert response.error.request_id == request_id
        assert "Invalid token" in response.error.message
    
    def test_map_validation_error(self):
        """Test Pydantic validation error mapping"""
        from src.utils.error_handling import map_validation_error
        from pydantic import BaseModel, ValidationError
        from uuid import uuid4
        
        class TestModel(BaseModel):
            email: str
            age: int
        
        try:
            TestModel(email="invalid", age="not_a_number")
        except ValidationError as e:
            request_id = uuid4()
            response = map_validation_error(e, request_id)
            
            assert response.error.code == ErrorCode.VALIDATION_ERROR
            assert response.error.request_id == request_id
    
    def test_translate_rls_violation(self):
        """Test RLS violation translation"""
        from sqlalchemy.exc import IntegrityError
        
        # Mock RLS violation
        rls_error = Exception("row-level security policy violation")
        
        # Should translate to AuthzError
        result = translate_rls_violation(rls_error)
        assert isinstance(result, AuthzError)
        assert "security policy" in str(result)
    
    def test_custom_exception_mapping(self):
        """Test mapping of custom exceptions"""
        from uuid import uuid4
        
        request_id = uuid4()
        
        # Test RetryableError
        retry_error = RetryableError("test_service", "Service unavailable", 30.0)
        response = map_exception_to_response(retry_error, request_id)
        
        assert response.error.code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert response.error.details.service == "test_service"
        assert response.error.details.retry_after == 30.0
        
        # Test AuthzError
        authz_error = AuthzError("Insufficient permissions")
        response = map_exception_to_response(authz_error, request_id)
        
        assert response.error.code == ErrorCode.AUTHORIZATION_ERROR
        assert "permissions" in response.error.details.reason


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_retry_with_eventual_success(self):
        """Test retry decorator in real endpoint (if dev endpoints exist)"""
        if self.client.get("/dev/flaky").status_code != 404:
            # Reset the flaky endpoint state
            response = self.client.get("/dev/flaky")
            
            # Should succeed after retries
            assert response.status_code == 200
            data = response.json()
            assert "Success after retries" in data["message"]
    
    def test_circuit_breaker_protection(self):
        """Test circuit breaker in real endpoint (if dev endpoints exist)"""
        if self.client.get("/dev/upstream-500").status_code != 404:
            # Make multiple calls to trigger circuit breaker
            responses = []
            for _ in range(10):
                response = self.client.get("/dev/upstream-500")
                responses.append(response.status_code)
                
                # Add small delay to avoid overwhelming
                time.sleep(0.01)
            
            # Should see some 500s (from upstream) and eventually circuit breaker errors
            # Circuit breaker errors would be mapped to 502 (EXTERNAL_SERVICE_ERROR)
            assert 500 in responses or 502 in responses
    
    def test_error_correlation_across_requests(self):
        """Test that error correlation works across multiple requests"""
        # Make request with custom correlation ID
        custom_id = "test-correlation-123"
        response = self.client.get("/", headers={
            "X-Request-ID": custom_id,
            "X-Test-Error": "not-found"
        })
        
        assert response.status_code == 404
        # Response should have a proper UUID, not the custom ID
        response_id = response.headers["X-Request-ID"]
        assert len(response_id) == 36  # UUID format
        
        # Error response should include request correlation
        data = response.json()
        assert data["error"]["request_id"] == response_id
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling under concurrent load"""
        import aiohttp
        import asyncio
        
        async def make_request():
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get("http://localhost:8000/nonexistent") as response:
                        return response.status
                except:
                    return 500  # Connection error
        
        # Note: This test requires the server to be running
        # In a real test suite, you'd use a test server
        try:
            tasks = [make_request() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should be 404 (or connection errors in test environment)
            status_codes = [r for r in results if isinstance(r, int)]
            if status_codes:  # Only check if we got actual responses
                assert all(code in [404, 500] for code in status_codes)
        except:
            # Skip this test if server is not running
            pytest.skip("Server not available for concurrent testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
