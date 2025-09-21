"""
Pydantic models for payment provider verification endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class PaymentProviderType(str, Enum):
    """Supported payment provider types"""

    PAYSTACK = "paystack"
    KORAPAY = "korapay"


class PaymentEnvironment(str, Enum):
    """Payment environment types"""

    TEST = "test"
    LIVE = "live"


class VerificationStatus(str, Enum):
    """Verification status options"""

    PENDING = "pending"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"


# Request Models


class PaystackCredentialsRequest(BaseModel):
    """Request model for Paystack credential verification"""

    secret_key: str = Field(..., min_length=1, description="Paystack secret key")
    public_key: Optional[str] = Field(
        None, description="Paystack public key (optional)"
    )
    environment: PaymentEnvironment = Field(
        PaymentEnvironment.TEST, description="Environment (test/live)"
    )

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if not v.startswith("sk_"):
            raise ValueError("Secret key must start with sk_")
        return v

    @validator("public_key")
    def validate_public_key(cls, v):
        if v and not v.startswith("pk_"):
            raise ValueError("Public key must start with pk_")
        return v


class KorapayCredentialsRequest(BaseModel):
    """Request model for Korapay credential verification"""

    public_key: str = Field(..., min_length=1, description="Korapay public key")
    secret_key: str = Field(..., min_length=1, description="Korapay secret key")
    webhook_secret: Optional[str] = Field(
        None, description="Webhook secret for signature verification"
    )
    environment: PaymentEnvironment = Field(
        PaymentEnvironment.TEST, description="Environment (test/live)"
    )

    @validator("public_key")
    def validate_public_key(cls, v):
        if not v.startswith("pk_"):
            raise ValueError("Public key must start with pk_")
        return v

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if not v.startswith("sk_"):
            raise ValueError("Secret key must start with sk_")
        return v


# Response Models


class PaymentProviderConfigResponse(BaseModel):
    """Response model for payment provider configuration"""

    id: UUID
    provider_type: PaymentProviderType
    environment: PaymentEnvironment
    verification_status: VerificationStatus
    last_verified_at: Optional[datetime]
    verification_error: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VerificationResult(BaseModel):
    """Result of credential verification"""

    success: bool
    provider_type: PaymentProviderType
    environment: PaymentEnvironment
    verification_status: VerificationStatus
    error_message: Optional[str] = None
    verified_at: Optional[datetime] = None
    config_id: Optional[UUID] = None


class PaymentProviderListResponse(BaseModel):
    """Response model for listing payment providers"""

    providers: List[PaymentProviderConfigResponse]
    total_count: int


# Error Models


class PaymentProviderError(BaseModel):
    """Payment provider specific error"""

    code: str
    message: str
    provider: PaymentProviderType
    details: Optional[Dict[str, Any]] = None
