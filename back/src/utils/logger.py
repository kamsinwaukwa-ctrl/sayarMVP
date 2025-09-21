"""
Logger utility for Sayar WhatsApp Commerce Platform
Provides correlation IDs, header redaction, and structured logging helpers
"""

import uuid
import re
from typing import Dict, Any, Optional
from ..config.logging import build_logger

# Headers that should be redacted in logs
REDACT_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "bearer",
    "jwt",
}

REDACT_VALUE = "[REDACTED]"

# Global logger instance
log = build_logger("sayar")


def get_logger(name: str = "sayar"):
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (defaults to "sayar")

    Returns:
        Logger instance configured with project settings
    """
    return build_logger(name)


def new_request_id(value: Optional[str] = None) -> str:
    """
    Generate or validate a request/correlation ID

    Args:
        value: Optional existing request ID to validate

    Returns:
        Valid UUID string for request correlation
    """
    if value:
        try:
            # Validate and normalize existing UUID
            return str(uuid.UUID(value))
        except (ValueError, TypeError):
            # If invalid, generate new one
            pass

    return str(uuid.uuid4())


def redact_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive headers for logging

    Args:
        headers: Dictionary of HTTP headers

    Returns:
        Dictionary with sensitive values redacted
    """
    redacted = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in REDACT_HEADERS:
            redacted[key] = REDACT_VALUE
        elif any(
            sensitive in key_lower for sensitive in ["token", "secret", "key", "auth"]
        ):
            redacted[key] = REDACT_VALUE
        else:
            redacted[key] = value
    return redacted


def redact_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive query parameters for logging

    Args:
        params: Dictionary of query parameters

    Returns:
        Dictionary with sensitive values redacted
    """
    redacted = {}
    for key, value in params.items():
        key_lower = key.lower()
        if any(
            sensitive in key_lower
            for sensitive in ["token", "secret", "key", "auth", "password"]
        ):
            redacted[key] = REDACT_VALUE
        else:
            redacted[key] = value
    return redacted


def log_event(event_type: str, message: str, **kwargs):
    """
    Log a structured event with standardized fields

    Args:
        event_type: Type of event (e.g., 'http_request', 'payment_webhook')
        message: Human-readable message
        **kwargs: Additional context fields
    """
    extra = {"event_type": event_type, **kwargs}
    log.info(message, extra=extra)


def log_error(
    event_type: str, message: str, exception: Optional[Exception] = None, **kwargs
):
    """
    Log an error event with standardized fields

    Args:
        event_type: Type of error event
        message: Human-readable error message
        exception: Exception instance (optional)
        **kwargs: Additional context fields
    """
    extra = {"event_type": event_type, **kwargs}

    if exception:
        log.exception(message, extra=extra, exc_info=exception)
    else:
        log.error(message, extra=extra)


# Convenience functions for common events
def log_http_request(request_id: str, method: str, path: str, **kwargs):
    """Log HTTP request start"""
    log_event(
        "http_request",
        f"{method} {path}",
        request_id=request_id,
        trace_id=request_id,
        method=method,
        path=path,
        **kwargs,
    )


def log_http_response(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
):
    """Log HTTP response completion"""
    log_event(
        "http_response",
        f"{method} {path} -> {status_code} ({duration_ms}ms)",
        request_id=request_id,
        trace_id=request_id,
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_auth_event(
    event_type: str,
    request_id: str,
    user_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    **kwargs,
):
    """Log authentication-related events"""
    log_event(
        event_type,
        f"Auth event: {event_type}",
        request_id=request_id,
        trace_id=request_id,
        user_id=user_id,
        merchant_id=merchant_id,
        **kwargs,
    )


def log_business_event(event_type: str, request_id: str, merchant_id: str, **kwargs):
    """Log business domain events"""
    log_event(
        event_type,
        f"Business event: {event_type}",
        request_id=request_id,
        trace_id=request_id,
        merchant_id=merchant_id,
        **kwargs,
    )
