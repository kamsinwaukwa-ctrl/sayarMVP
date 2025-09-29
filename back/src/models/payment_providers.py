"""
Pydantic models for payment provider verification endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum
from decimal import Decimal


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


class SyncStatus(str, Enum):
    """Sync status with payment provider"""

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"


class SettlementSchedule(str, Enum):
    """Settlement schedule options"""

    AUTO = "AUTO"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    MANUAL = "MANUAL"


# Request Models


class SubaccountUpdateRequest(BaseModel):
    """Request model for updating subaccount details (partial update allowed)"""

    business_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_code: Optional[str] = Field(None, min_length=1)
    account_number: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r'^\d{10}$')
    percentage_charge: Optional[Decimal] = Field(None, ge=0, le=100)
    settlement_schedule: Optional[SettlementSchedule] = None

    @validator('account_number')
    def validate_account_number(cls, v):
        if v is not None and (not v.isdigit() or len(v) != 10):
            raise ValueError('Account number must be exactly 10 digits')
        return v


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
    """Response model for payment provider configuration - simplified, no credentials"""

    id: UUID
    provider_type: PaymentProviderType
    environment: PaymentEnvironment
    active: bool
    created_at: datetime
    updated_at: datetime

    # Subaccount metadata (cached from provider)
    subaccount_code: Optional[str] = None
    bank_code: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_last4: Optional[str] = None  # Non-sensitive, last 4 digits only
    percentage_charge: Optional[Decimal] = None
    settlement_schedule: Optional[SettlementSchedule] = None

    # Sync status (Paystack is source of truth)
    sync_status: SyncStatus
    last_synced_with_provider: Optional[datetime] = None
    sync_error: Optional[str] = None

    class Config:
        from_attributes = True


class SubaccountUpdateResponse(BaseModel):
    """Response model for subaccount updates with partial success handling"""

    success: bool
    partial_success: bool = False  # True if Paystack succeeded but DB sync pending
    message: str
    subaccount_code: Optional[str] = None
    sync_status: Optional[SyncStatus] = None
    updated_fields: Optional[List[str]] = None  # Fields that were successfully updated

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class VerificationResult(BaseModel):
    """Result of credential verification"""

    success: bool
    provider_type: PaymentProviderType
    environment: PaymentEnvironment
    verification_status: VerificationStatus
    error_message: Optional[str] = None
    verified_at: Optional[datetime] = None
    config_id: Optional[UUID] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PaymentProviderListResponse(BaseModel):
    """Response model for listing payment providers"""

    providers: List[PaymentProviderConfigResponse]
    total_count: int


# Settlement Schedule Enum


class SettlementSchedule(str, Enum):
    """Settlement schedule options"""

    AUTO = 'AUTO'
    WEEKLY = 'WEEKLY'
    MONTHLY = 'MONTHLY'
    MANUAL = 'MANUAL'


# Error Models


class PaymentProviderError(BaseModel):
    """Payment provider specific error"""

    code: str
    message: str
    provider: PaymentProviderType
    details: Optional[Dict[str, Any]] = None


# New Models for Bank Operations


class Bank(BaseModel):
    """Bank model for dropdown selection"""

    name: str
    code: str
    slug: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    active: bool = True


class BankListResponse(BaseModel):
    """Response model for banks list"""

    banks: List[Bank]
    total_count: int
    cached: bool = False


class AccountResolutionRequest(BaseModel):
    """Request model for account resolution"""

    account_number: str = Field(..., min_length=10, max_length=10, pattern=r'^\d{10}$')
    bank_code: str = Field(..., min_length=1)

    @validator('account_number')
    def validate_account_number(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Account number must be exactly 10 digits')
        return v


class AccountResolutionResponse(BaseModel):
    """Response model for account resolution"""

    success: bool
    data: Optional[Dict[str, str]] = None  # {account_number, account_name}
    error_message: Optional[str] = None


class SubaccountRequest(BaseModel):
    """Request model for subaccount creation"""

    business_name: str = Field(..., min_length=1, max_length=100)
    bank_code: str = Field(..., min_length=1)
    account_number: str = Field(..., min_length=10, max_length=10, pattern=r'^\d{10}$')
    percentage_charge: Decimal = Field(default=Decimal('2.0'), ge=0, le=100)
    settlement_schedule: Optional[str] = Field(default='AUTO')

    @validator('account_number')
    def validate_account_number(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Account number must be exactly 10 digits')
        return v


class SubaccountResponse(BaseModel):
    """Response model for subaccount creation"""

    success: bool
    subaccount_code: Optional[str] = None
    account_name: Optional[str] = None
    account_last4: Optional[str] = None
    business_name: Optional[str] = None
    bank_name: Optional[str] = None
    percentage_charge: Optional[Decimal] = None
    settlement_schedule: Optional[str] = None
    error_message: Optional[str] = None
