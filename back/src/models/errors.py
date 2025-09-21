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
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    MERCHANT_NOT_FOUND = "MERCHANT_NOT_FOUND"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    # WhatsApp specific error codes
    WHATSAPP_CREDENTIALS_NOT_FOUND = "WHATSAPP_CREDENTIALS_NOT_FOUND"
    WHATSAPP_VERIFICATION_FAILED = "WHATSAPP_VERIFICATION_FAILED"
    # Cloudinary specific error codes
    CLOUDINARY_NOT_CONFIGURED = "CLOUDINARY_NOT_CONFIGURED"
    CLOUDINARY_HEALTHCHECK_FAILED = "CLOUDINARY_HEALTHCHECK_FAILED"
    CLOUDINARY_UPLOAD_FAILED = "CLOUDINARY_UPLOAD_FAILED"
    CLOUDINARY_DELETE_FAILED = "CLOUDINARY_DELETE_FAILED"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    UNSUPPORTED_IMAGE_TYPE = "UNSUPPORTED_IMAGE_TYPE"
    IMAGE_DIMENSIONS_TOO_SMALL = "IMAGE_DIMENSIONS_TOO_SMALL"
    WEBHOOK_SIGNATURE_INVALID = "WEBHOOK_SIGNATURE_INVALID"


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


class APIError(Exception):
    """Structured API error exception with code, message, and optional details"""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for HTTP responses"""
        return {
            "ok": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }


class ErrorInfo(BaseModel):
    """Error information for API responses"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Error details")


class ErrorResponse(BaseModel):
    """Standard error response envelope for all API errors"""
    ok: bool = Field(False, description="Always false for error responses")
    error: ErrorInfo = Field(..., description="Error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ok": False,
                "error": {
                    "code": "AUTHORIZATION_FAILED",
                    "message": "Forbidden",
                    "details": {
                        "reason": "Requires admin role"
                    }
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