"""
Error handling utilities for Sayar WhatsApp Commerce Platform
Provides exception mapping, sanitization, and DB error translation
"""

import re
import traceback
from typing import Dict, Any, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, DataError
from asyncpg.exceptions import (
    UniqueViolationError,
    ForeignKeyViolationError,
    CheckViolationError,
    NotNullViolationError
)

from ..models.errors import (
    ErrorCode, ErrorDetails, APIError, ErrorResponse,
    RetryableError, RateLimitedError, UpstreamServiceError,
    AuthzError, AuthnError
)
from ..utils.logger import log_error


# Sensitive data patterns to redact
SENSITIVE_PATTERNS = [
    r'password["\s]*[:=]["\s]*[^"\s,}]+',  # password fields
    r'token["\s]*[:=]["\s]*[^"\s,}]+',     # token fields
    r'key["\s]*[:=]["\s]*[^"\s,}]+',       # key fields
    r'secret["\s]*[:=]["\s]*[^"\s,}]+',    # secret fields
    r'authorization["\s]*[:=]["\s]*[^"\s,}]+',  # auth headers
    r'\b[0-9]{13,19}\b',                   # credit card numbers
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # emails (partial)
]

REDACTION_PLACEHOLDER = "***REDACTED***"


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error message by removing sensitive information
    
    Args:
        message: Raw error message
        
    Returns:
        Sanitized error message
    """
    sanitized = message
    
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, REDACTION_PLACEHOLDER, sanitized, flags=re.IGNORECASE)
    
    # Limit message length to prevent log flooding
    if len(sanitized) > 500:
        sanitized = sanitized[:497] + "..."
    
    return sanitized


def sanitize_error_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize error details by removing sensitive values
    
    Args:
        details: Raw error details
        
    Returns:
        Sanitized error details
    """
    sanitized = {}
    
    for key, value in details.items():
        if isinstance(value, str):
            # Check if key or value contains sensitive data
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in ['password', 'token', 'secret', 'key', 'auth']):
                sanitized[key] = REDACTION_PLACEHOLDER
            else:
                sanitized[key] = sanitize_error_message(value)
        elif isinstance(value, (dict, list)):
            # Don't recurse deeply to avoid complex sanitization
            sanitized[key] = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        else:
            sanitized[key] = value
    
    return sanitized


def create_error_response(
    code: ErrorCode,
    message: str,
    details: Optional[ErrorDetails] = None,
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Create standardized error response
    
    Args:
        code: Error code
        message: Error message
        details: Optional error details
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    # Sanitize message
    sanitized_message = sanitize_error_message(message)
    
    # Create API error
    api_error = APIError(
        code=code,
        message=sanitized_message,
        details=details,
        request_id=request_id
    )
    
    return ErrorResponse(
        error=api_error,
        timestamp=datetime.now(timezone.utc)
    )


def map_http_exception(
    exc: HTTPException,
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Map FastAPI HTTPException to standardized error response
    
    Args:
        exc: HTTPException to map
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    status_code = exc.status_code
    detail = str(exc.detail) if exc.detail else "HTTP error"
    
    # Map status codes to error codes
    if status_code == 400:
        code = ErrorCode.VALIDATION_ERROR
    elif status_code == 401:
        code = ErrorCode.AUTHENTICATION_ERROR
    elif status_code == 403:
        code = ErrorCode.AUTHORIZATION_ERROR
    elif status_code == 404:
        code = ErrorCode.NOT_FOUND
    elif status_code == 409:
        code = ErrorCode.CONFLICT
    elif status_code == 429:
        code = ErrorCode.RATE_LIMITED
    elif status_code >= 500:
        code = ErrorCode.INTERNAL_ERROR
    else:
        code = ErrorCode.INTERNAL_ERROR
    
    # Extract retry_after from headers if present
    retry_after = None
    if hasattr(exc, 'headers') and exc.headers:
        retry_after_header = exc.headers.get('Retry-After')
        if retry_after_header:
            try:
                retry_after = float(retry_after_header)
            except (ValueError, TypeError):
                pass
    
    details = None
    if retry_after:
        details = ErrorDetails(
            reason=detail,
            retry_after=retry_after
        )
    else:
        details = ErrorDetails(reason=detail)
    
    return create_error_response(code, detail, details, request_id)


def map_validation_error(
    exc: ValidationError,
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Map Pydantic ValidationError to standardized error response
    
    Args:
        exc: ValidationError to map
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    errors = exc.errors()
    
    if len(errors) == 1:
        # Single validation error
        error = errors[0]
        field = ".".join(str(loc) for loc in error['loc'])
        message = error['msg']
        
        details = ErrorDetails(
            field=field,
            reason=message,
            value=error.get('input')
        )
        
        return create_error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Validation error in field '{field}': {message}",
            details,
            request_id
        )
    else:
        # Multiple validation errors
        error_list = []
        for error in errors:
            field = ".".join(str(loc) for loc in error['loc'])
            error_list.append(f"{field}: {error['msg']}")
        
        details = ErrorDetails(
            reason=f"Multiple validation errors: {'; '.join(error_list)}"
        )
        
        return create_error_response(
            ErrorCode.VALIDATION_ERROR,
            "Multiple validation errors",
            details,
            request_id
        )


def map_database_error(
    exc: Exception,
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Map database exceptions to standardized error responses
    
    Args:
        exc: Database exception to map
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    # Handle SQLAlchemy exceptions
    if isinstance(exc, IntegrityError):
        # Check for specific constraint violations
        if isinstance(exc.orig, UniqueViolationError):
            details = ErrorDetails(
                reason="Resource already exists",
                value=str(exc.orig).split('"')[1] if '"' in str(exc.orig) else None
            )
            return create_error_response(
                ErrorCode.CONFLICT,
                "Unique constraint violation",
                details,
                request_id
            )
        elif isinstance(exc.orig, ForeignKeyViolationError):
            details = ErrorDetails(
                reason="Referenced resource does not exist"
            )
            return create_error_response(
                ErrorCode.VALIDATION_ERROR,
                "Foreign key constraint violation",
                details,
                request_id
            )
        elif isinstance(exc.orig, NotNullViolationError):
            # Extract column name from error message
            column = str(exc.orig).split('"')[1] if '"' in str(exc.orig) else "unknown"
            details = ErrorDetails(
                field=column,
                reason="Field is required"
            )
            return create_error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Required field '{column}' is missing",
                details,
                request_id
            )
        elif isinstance(exc.orig, CheckViolationError):
            details = ErrorDetails(
                reason="Data constraint violation"
            )
            return create_error_response(
                ErrorCode.VALIDATION_ERROR,
                "Check constraint violation",
                details,
                request_id
            )
    
    elif isinstance(exc, DataError):
        details = ErrorDetails(
            reason="Invalid data format or type"
        )
        return create_error_response(
            ErrorCode.VALIDATION_ERROR,
            "Data format error",
            details,
            request_id
        )
    
    # Generic database error
    details = ErrorDetails(
        reason="Database operation failed"
    )
    return create_error_response(
        ErrorCode.INTERNAL_ERROR,
        "Database error",
        details,
        request_id
    )


def map_custom_exception(
    exc: Exception,
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Map custom application exceptions to standardized error responses
    
    Args:
        exc: Custom exception to map
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    if isinstance(exc, AuthnError):
        details = ErrorDetails(reason=exc.reason)
        return create_error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "Authentication failed",
            details,
            request_id
        )
    
    elif isinstance(exc, AuthzError):
        details = ErrorDetails(reason=exc.reason)
        return create_error_response(
            ErrorCode.AUTHORIZATION_ERROR,
            str(exc),
            details,
            request_id
        )
    
    elif isinstance(exc, RateLimitedError):
        details = ErrorDetails(
            service=exc.service,
            reason="Rate limit exceeded",
            retry_after=exc.retry_after
        )
        return create_error_response(
            ErrorCode.RATE_LIMITED,
            f"Rate limited by {exc.service}",
            details,
            request_id
        )
    
    elif isinstance(exc, RetryableError):
        details = ErrorDetails(
            service=exc.service,
            reason=exc.message,
            retry_after=exc.retry_after
        )
        return create_error_response(
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            f"Service temporarily unavailable: {exc.service}",
            details,
            request_id
        )
    
    elif isinstance(exc, UpstreamServiceError):
        details = ErrorDetails(
            service=exc.service,
            reason=f"HTTP {exc.status_code}: {sanitize_error_message(exc.body)}"
        )
        
        # Determine error code based on upstream status
        if exc.status_code >= 500:
            code = ErrorCode.EXTERNAL_SERVICE_ERROR
        elif exc.status_code == 429:
            code = ErrorCode.RATE_LIMITED
        else:
            code = ErrorCode.EXTERNAL_SERVICE_ERROR
        
        return create_error_response(
            code,
            f"Upstream service error: {exc.service}",
            details,
            request_id
        )
    
    # Unknown exception
    details = ErrorDetails(
        reason=f"Unexpected error: {type(exc).__name__}"
    )
    return create_error_response(
        ErrorCode.INTERNAL_ERROR,
        "Internal server error",
        details,
        request_id
    )


def map_exception_to_response(
    exc: Exception,
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Map any exception to standardized error response
    
    Args:
        exc: Exception to map
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    # Log the original exception for debugging
    log_error(
        "exception_mapping",
        f"Mapping exception to error response: {type(exc).__name__}",
        exception=exc,
        request_id=str(request_id) if request_id else None
    )
    
    # Map based on exception type
    if isinstance(exc, HTTPException):
        return map_http_exception(exc, request_id)
    elif isinstance(exc, ValidationError):
        return map_validation_error(exc, request_id)
    elif isinstance(exc, (IntegrityError, DataError)):
        return map_database_error(exc, request_id)
    elif isinstance(exc, (AuthnError, AuthzError, RetryableError, RateLimitedError, UpstreamServiceError)):
        return map_custom_exception(exc, request_id)
    else:
        # Check if it's an AuthError from our auth service
        if hasattr(exc, '__class__') and exc.__class__.__name__ == 'AuthError':
            # Handle AuthError similar to AuthnError
            details = ErrorDetails(reason=str(exc))
            return create_error_response(
                ErrorCode.VALIDATION_ERROR,
                "Authentication service error",
                details,
                request_id
            )
        return map_custom_exception(exc, request_id)


def translate_rls_violation(exc: Exception) -> AuthzError:
    """
    Translate RLS (Row Level Security) violations to authorization errors
    
    Args:
        exc: Database exception that might be RLS violation
        
    Returns:
        AuthzError if RLS violation detected
        
    Raises:
        Original exception if not RLS violation
    """
    error_message = str(exc)
    
    # Check for RLS policy violations
    if any(pattern in error_message.lower() for pattern in [
        'row-level security',
        'rls',
        'policy',
        'permission denied for table',
        'insufficient privilege'
    ]):
        return AuthzError("Access denied by security policy")
    
    # Check for tenant isolation violations
    if 'merchant_id' in error_message.lower():
        return AuthzError("Access denied: resource not in your tenant")
    
    # Not an RLS violation
    raise exc


def handle_business_logic_error(
    operation: str,
    error_details: Dict[str, Any],
    request_id: Optional[UUID] = None
) -> ErrorResponse:
    """
    Handle business logic errors with contextual information
    
    Args:
        operation: Business operation that failed
        error_details: Details about the failure
        request_id: Request correlation ID
        
    Returns:
        Standardized error response
    """
    # Sanitize error details
    sanitized_details = sanitize_error_details(error_details)
    
    # Create appropriate error details
    details = ErrorDetails(
        reason=sanitized_details.get('reason', f'{operation} failed'),
        **{k: v for k, v in sanitized_details.items() if k != 'reason'}
    )
    
    # Determine error code based on operation
    if 'not found' in sanitized_details.get('reason', '').lower():
        code = ErrorCode.NOT_FOUND
    elif 'conflict' in sanitized_details.get('reason', '').lower():
        code = ErrorCode.CONFLICT
    elif 'validation' in sanitized_details.get('reason', '').lower():
        code = ErrorCode.VALIDATION_ERROR
    else:
        code = ErrorCode.INTERNAL_ERROR
    
    return create_error_response(
        code,
        f"Business logic error in {operation}",
        details,
        request_id
    )
