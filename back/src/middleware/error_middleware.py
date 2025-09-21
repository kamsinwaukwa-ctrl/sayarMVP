"""
Error middleware for Sayar WhatsApp Commerce Platform
Global error handling with request correlation and standardized responses
"""

import traceback
from uuid import UUID
from typing import Optional

import json
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder for UUID objects"""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

from ..models.errors import ErrorCode, ErrorResponse
from ..utils.error_handling import map_exception_to_response
from ..utils.logger import log, log_error, new_request_id
from ..utils.metrics import record_error


class ErrorMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware
    
    Features:
    - Request correlation ID generation/propagation
    - Standardized error response formatting
    - Comprehensive error logging with context
    - Metrics collection for errors
    """
    
    def __init__(
        self,
        app: ASGIApp,
        request_id_header: str = "X-Request-ID",
        include_debug_info: bool = False
    ):
        super().__init__(app)
        self.request_id_header = request_id_header
        self.include_debug_info = include_debug_info
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle any errors"""
        
        # Get request ID from state (set by logging middleware)
        request_uuid = getattr(request.state, "request_id", None)
        
        # Add request ID to request headers for downstream handlers
        request.headers.__dict__["_list"].append(
            (self.request_id_header.encode(), str(request_uuid).encode())
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.request_id_header] = str(request_uuid)
            
            # Handle FastAPI's built-in error responses
            if response.status_code >= 400:
                detail = "Not Found"
                
                # Try to get error details from response
                if isinstance(response, JSONResponse):
                    try:
                        data = response.body.decode()
                        import json
                        json_data = json.loads(data)
                        if "detail" in json_data:
                            detail = json_data["detail"]
                    except:
                        pass
                elif isinstance(response, StreamingResponse):
                    # For streaming responses, use status code to determine message
                    if response.status_code == 404:
                        detail = "Not Found"
                    elif response.status_code == 429:
                        detail = "Too Many Requests"
                    elif response.status_code == 403:
                        detail = "Forbidden"
                    elif response.status_code == 401:
                        detail = "Unauthorized"
                
                error_response = map_exception_to_response(
                    HTTPException(status_code=response.status_code, detail=detail),
                    request_uuid
                )
                return JSONResponse(
                    content={
                        "ok": False,
                        "error": {
                            **error_response.error.model_dump(),
                            "request_id": str(request_uuid)
                        },
                        "timestamp": error_response.timestamp.isoformat()
                    },
                    status_code=response.status_code,
                    headers={
                        self.request_id_header: str(request_uuid),
                        "Content-Type": "application/json"
                    }
                )
            
            return response
            
        except Exception as exc:
            # Handle the exception and return standardized error response
            return await self._handle_exception(exc, request, request_uuid)
    
    async def _handle_exception(
        self,
        exc: Exception,
        request: Request,
        request_id: UUID
    ) -> JSONResponse:
        """
        Handle exception and return standardized JSON error response
        
        Args:
            exc: The exception that occurred
            request: FastAPI request object
            request_id: Request correlation ID
            
        Returns:
            JSONResponse with standardized error format
        """
        # Log the error with full context
        log_error(
            "unhandled_exception",
            f"Unhandled exception in {request.method} {request.url.path}",
            exception=exc,
            request_id=str(request_id),
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=self._get_client_ip(request)
        )
        
        # Map exception to standardized error response
        error_response = map_exception_to_response(exc, request_id)
        
        # Determine HTTP status code from error code
        status_code = self._get_status_code_from_error_code(error_response.error.code)
        
        # Record metrics
        record_error(str(error_response.error.code), "middleware")
        
        # Add debug information if enabled (development only)
        if self.include_debug_info:
            # Add traceback to error details (be careful not to leak sensitive info)
            if error_response.error.details:
                error_response.error.details.debug_trace = traceback.format_exc()
            else:
                from ..models.errors import ErrorDetails
                error_response.error.details = ErrorDetails(
                    reason=error_response.error.message,
                    debug_trace=traceback.format_exc()
                )
        
        # Create JSON response with custom UUID encoder
        content = {
            "ok": False,
            "error": error_response.error.model_dump(),
            "timestamp": error_response.timestamp.isoformat()
        }
        response = JSONResponse(
            content=json.loads(json.dumps(content, cls=UUIDEncoder)),
            status_code=status_code,
            headers={
                self.request_id_header: str(request_id),
                "Content-Type": "application/json"
            }
        )
        
        # Log the error response
        log.info(
            f"Error response sent for {request.method} {request.url.path}",
            extra={
                "event_type": "error_response",
                "request_id": str(request_id),
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "error_code": error_response.error.code.value,
                "error_message": error_response.error.message
            }
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request"""
        # Check for forwarded headers first (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP if multiple are present
            return forwarded_for.split(",")[0].strip()
        
        # Check other common forwarded headers
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    def _get_status_code_from_error_code(self, error_code: ErrorCode) -> int:
        """
        Map error codes to HTTP status codes
        
        Args:
            error_code: Application error code
            
        Returns:
            HTTP status code
        """
        status_mapping = {
            ErrorCode.VALIDATION_ERROR: 400,
            ErrorCode.AUTHENTICATION_FAILED: 401,
            ErrorCode.AUTHORIZATION_FAILED: 403,
            ErrorCode.MERCHANT_NOT_FOUND: 404,
            ErrorCode.DUPLICATE_RESOURCE: 409,
            ErrorCode.RATE_LIMIT_EXCEEDED: 429,
            ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
            ErrorCode.SERVICE_UNAVAILABLE: 503,
            ErrorCode.INTERNAL_ERROR: 500,
        }
        
        return status_mapping.get(error_code, 500)


def get_request_id(request: Request) -> Optional[UUID]:
    """
    Get request ID from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request UUID if available
    """
    return getattr(request.state, 'request_id', None)


def create_error_middleware(
    request_id_header: str = "X-Request-ID",
    include_debug_info: bool = False
) -> type:
    """
    Factory function to create error middleware with configuration
    
    Args:
        request_id_header: Header name for request correlation ID
        include_debug_info: Whether to include debug information in responses
        
    Returns:
        Configured error middleware class
    """
    class ConfiguredErrorMiddleware(ErrorMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(
                app,
                request_id_header=request_id_header,
                include_debug_info=include_debug_info
            )
    
    return ConfiguredErrorMiddleware
