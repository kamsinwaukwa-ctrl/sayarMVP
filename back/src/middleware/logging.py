"""
Logging middleware for Sayar WhatsApp Commerce Platform
Provides request/response logging, metrics collection, and correlation IDs
"""

import time
import os
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from ..utils.logger import log, new_request_id, redact_headers, log_http_response, log_error
from ..utils.metrics import (
    HTTP_REQUESTS_TOTAL, 
    HTTP_REQUEST_DURATION_SECONDS, 
    HTTP_REQUESTS_IN_FLIGHT,
    record_error
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging and metrics collection
    """
    
    def __init__(self, app, request_id_header: str = None):
        super().__init__(app)
        self.request_id_header = request_id_header or os.getenv("REQUEST_ID_HEADER", "X-Request-ID")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and response with logging and metrics
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response with added correlation headers
        """
        # Generate or extract request ID for correlation
        request_id = new_request_id(request.headers.get(self.request_id_header))
        
        # Get route template for low-cardinality metrics
        route_template = self._get_route_template(request)
        
        # Store request context for handlers
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()
        
        # Log request start
        self._log_request_start(request, request_id, route_template)
        
        # Track in-flight requests
        HTTP_REQUESTS_IN_FLIGHT.labels(route=route_template).inc()
        
        try:
            # Process request
            response: Response = await call_next(request)
            
            # Calculate duration
            duration_seconds = time.perf_counter() - request.state.start_time
            duration_ms = round(duration_seconds * 1000, 2)
            
            # Add correlation header to response
            response.headers[self.request_id_header] = request_id
            
            # Record metrics
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                route=route_template,
                status_code=str(response.status_code)
            ).inc()
            
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                route=route_template
            ).observe(duration_seconds)
            
            # Log successful response
            self._log_response_success(
                request, request_id, route_template, 
                response.status_code, duration_ms
            )
            
            return response
            
        except Exception as e:
            # Calculate duration for failed request
            duration_seconds = time.perf_counter() - request.state.start_time
            duration_ms = round(duration_seconds * 1000, 2)
            
            # Record error metrics
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                route=route_template,
                status_code="500"
            ).inc()
            
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                route=route_template
            ).observe(duration_seconds)
            
            record_error("unhandled_exception", "http_middleware")
            
            # Log unhandled exception
            self._log_unhandled_exception(
                request, request_id, route_template, 
                duration_ms, e
            )
            
            # Re-raise exception to be handled by FastAPI
            raise
            
        finally:
            # Always decrement in-flight counter
            HTTP_REQUESTS_IN_FLIGHT.labels(route=route_template).dec()
    
    def _get_route_template(self, request: Request) -> str:
        """
        Extract route template for low-cardinality metrics
        
        Args:
            request: HTTP request
            
        Returns:
            Route template or path
        """
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            return route.path
        return request.url.path
    
    def _log_request_start(self, request: Request, request_id: str, route_template: str):
        """Log request start with context"""
        # Redact sensitive headers
        safe_headers = redact_headers(dict(request.headers))
        
        # Get request context
        merchant_id = getattr(request.state, "merchant_id", None)
        user_id = getattr(request.state, "user_id", None)
        idempotency_key = request.headers.get("Idempotency-Key")
        
        log.info(
            f"Request started: {request.method} {route_template}",
            extra={
                "event_type": "http_request",
                "request_id": request_id,
                "trace_id": request_id,
                "method": request.method,
                "route": route_template,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "headers": safe_headers,
                "merchant_id": merchant_id,
                "user_id": user_id,
                "idempotency_key": idempotency_key,
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
            }
        )
    
    def _log_response_success(
        self, 
        request: Request, 
        request_id: str, 
        route_template: str, 
        status_code: int, 
        duration_ms: float
    ):
        """Log successful response"""
        # Get request context
        merchant_id = getattr(request.state, "merchant_id", None)
        user_id = getattr(request.state, "user_id", None)
        
        log.info(
            f"Request completed: {request.method} {route_template} -> {status_code} ({duration_ms}ms)",
            extra={
                "event_type": "http_response",
                "request_id": request_id,
                "trace_id": request_id,
                "method": request.method,
                "route": route_template,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "merchant_id": merchant_id,
                "user_id": user_id,
                "client_ip": self._get_client_ip(request),
            }
        )
    
    def _log_unhandled_exception(
        self, 
        request: Request, 
        request_id: str, 
        route_template: str, 
        duration_ms: float, 
        exception: Exception
    ):
        """Log unhandled exception"""
        # Get request context
        merchant_id = getattr(request.state, "merchant_id", None)
        user_id = getattr(request.state, "user_id", None)
        
        log.exception(
            f"Unhandled exception: {request.method} {route_template} -> 500 ({duration_ms}ms)",
            extra={
                "event_type": "error_unhandled",
                "request_id": request_id,
                "trace_id": request_id,
                "method": request.method,
                "route": route_template,
                "duration_ms": duration_ms,
                "merchant_id": merchant_id,
                "user_id": user_id,
                "client_ip": self._get_client_ip(request),
                "error_type": type(exception).__name__,
                "error_message": str(exception),
            },
            exc_info=exception
        )
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP from request headers
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check common headers for client IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get first IP in case of comma-separated list
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to client from request scope
        client = request.client
        return client.host if client else None