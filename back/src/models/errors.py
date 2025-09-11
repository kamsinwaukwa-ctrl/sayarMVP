"""
Error models for Sayar WhatsApp Commerce Platform
Defines error enums, details, and response envelopes for consistent error handling
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for consistent error classification"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorDetails(BaseModel):
    """Detailed error information with optional context"""
    field: Optional[str] = Field(None, description="Field name for validation errors")
    reason: str = Field(..., description="Human-readable reason for the error")
    value: Optional[Any] = Field(None, description="Invalid value that caused the error")
    service: Optional[str] = Field(None, description="External service that failed")
    retry_after: Optional[float] = Field(None, description="Seconds to wait before retrying")
    debug_trace: Optional[str] = Field(None, description="Debug traceback (development only)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "field": "email",
                    "reason": "Invalid email format",
                    "value": "invalid-email"
                },
                {
                    "reason": "Requires admin role"
                },
                {
                    "service": "paystack",
                    "reason": "Payment gateway unavailable",
                    "retry_after": 30.0
                }
            ]
        }
    }


class APIError(BaseModel):
    """Structured API error with code, message, and optional details"""
    code: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[ErrorDetails] = Field(None, description="Additional error context")
    request_id: UUID = Field(..., description="Request correlation ID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {
                        "field": "email",
                        "reason": "Invalid email format",
                        "value": "invalid-email"
                    },
                    "request_id": "a42b0b6a-1234-5678-9abc-123456789abc"
                },
                {
                    "code": "AUTHORIZATION_ERROR",
                    "message": "Forbidden",
                    "details": {
                        "reason": "Requires admin role"
                    },
                    "request_id": "a42b0b6a-1234-5678-9abc-123456789abc"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response envelope for all API errors"""
    ok: bool = Field(False, description="Always false for error responses")
    error: APIError = Field(..., description="Error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ok": False,
                "error": {
                    "code": "AUTHORIZATION_ERROR",
                    "message": "Forbidden",
                    "details": {
                        "reason": "Requires admin role"
                    },
                    "request_id": "a42b0b6a-1234-5678-9abc-123456789abc"
                },
                "timestamp": "2025-01-27T10:00:00Z"
            }
        }
    }


# Custom exception classes for structured error handling
class RetryableError(Exception):
    """Exception for operations that should be retried"""
    def __init__(self, message: str, next_run_at: Optional[datetime] = None):
        self.message = message
        self.next_run_at = next_run_at
        super().__init__(message)


class RateLimitedError(RetryableError):
    """Exception for rate-limited operations"""
    def __init__(self, message: str, details: Dict[str, Any]):
        self.details = details
        super().__init__(message=message, next_run_at=None)


class UpstreamServiceError(Exception):
    """Exception for upstream service failures"""
    def __init__(self, service: str, status_code: int, body: str):
        self.service = service
        self.status_code = status_code
        self.body = body
        super().__init__(f"[{service}] HTTP {status_code}: {body}")


class AuthzError(Exception):
    """Exception for authorization failures (403)"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Authorization failed: {reason}")


class AuthnError(Exception):
    """Exception for authentication failures (401)"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Authentication failed: {reason}")


class NotFoundError(Exception):
    """Exception for resource not found errors (404)"""
    def __init__(self, resource: str, identifier: Any):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} not found: {identifier}")


class ValidationError(Exception):
    """Exception for validation errors (400)"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(f"Validation error: {message}")