"""
Rate limiting models and types for Sayar platform.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RateLimitType(str, Enum):
    """Type of rate limit being applied."""

    API = "api"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "requests_per_minute": 60.0,
                "burst_limit": 15,
                "window_size": 60,
            }
        }
    )

    requests_per_minute: float = Field(
        60.0, ge=0, description="Number of requests allowed per minute"
    )
    burst_limit: int = Field(15, ge=0, description="Maximum burst size allowed")
    window_size: int = Field(60, ge=1, description="Time window in seconds")


class RateLimitInfo(BaseModel):
    """Information about current rate limit status."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "limit": 60.0,
                "remaining": 59,
                "reset_time": "2024-01-27T12:00:00Z",
                "retry_after": None,
            }
        }
    )

    limit: float = Field(..., description="Total limit for the current window")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset_time: datetime = Field(..., description="When the current window resets")
    retry_after: Optional[int] = Field(
        None, description="Seconds until next request is allowed"
    )


class RateLimitResponse(BaseModel):
    """Standard rate limit error response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ok": False,
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Rate limit exceeded",
                    "details": {"retry_after": 60},
                },
                "timestamp": "2024-01-27T12:00:00Z",
            }
        }
    )

    ok: bool = Field(False, description="Operation success status")
    error: Dict[str, Any] = Field(
        ..., description="Error details following BE-007 APIError shape"
    )
    timestamp: datetime = Field(..., description="When the error occurred")


class MerchantRateLimitConfig(BaseModel):
    """Merchant-specific rate limit configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_id": "123e4567-e89b-12d3-a456-426614174000",
                "api_rate_limit_per_minute": 60,
                "api_burst_limit": 15,
                "wa_rate_limit_per_hour": 1000,
                "rate_limit_enabled": True,
            }
        }
    )

    merchant_id: str = Field(..., description="UUID of the merchant")
    api_rate_limit_per_minute: int = Field(
        60, ge=0, description="API requests allowed per minute"
    )
    api_burst_limit: int = Field(15, ge=0, description="API burst capacity")
    wa_rate_limit_per_hour: int = Field(
        1000, ge=0, description="WhatsApp messages per hour"
    )
    rate_limit_enabled: bool = Field(
        True, description="Whether rate limiting is enabled"
    )
