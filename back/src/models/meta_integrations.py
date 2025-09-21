"""
Pydantic models for Meta Commerce Catalog integration credentials and responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


class MetaIntegrationStatus(str, Enum):
    """Meta integration status enumeration"""

    PENDING = "pending"
    VERIFIED = "verified"
    INVALID = "invalid"
    EXPIRED = "expired"


class MetaIntegrationError(Exception):
    """Custom exception for Meta integration errors"""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class MetaCredentialsRequest(BaseModel):
    """Request model for storing Meta credentials"""

    catalog_id: str = Field(
        ..., min_length=1, max_length=255, description="Meta Commerce Catalog ID"
    )
    system_user_token: str = Field(
        ..., min_length=50, description="Meta system user access token"
    )
    app_id: str = Field(..., min_length=1, max_length=255, description="Meta App ID")
    waba_id: Optional[str] = Field(
        None, max_length=255, description="WhatsApp Business Account ID"
    )

    @validator("system_user_token")
    def validate_token_format(cls, v):
        if not v.startswith(("EAAA", "EAA")):
            raise ValueError("Invalid Meta access token format")
        return v

    @validator("catalog_id")
    def validate_catalog_id(cls, v):
        if not v.isdigit():
            raise ValueError("Catalog ID must be numeric")
        return v

    @validator("app_id")
    def validate_app_id(cls, v):
        if not v.isdigit():
            raise ValueError("App ID must be numeric")
        return v


class MetaCatalogOnlyRequest(BaseModel):
    """Simplified request model for storing only catalog_id (reuses WhatsApp credentials)"""

    catalog_id: str = Field(
        ..., min_length=1, max_length=255, description="Meta Commerce Catalog ID"
    )

    @validator("catalog_id")
    def validate_catalog_id(cls, v):
        if not v.isdigit():
            raise ValueError("Catalog ID must be numeric")
        return v


class MetaCredentialsResponse(BaseModel):
    """Response model for credential storage/update"""

    success: bool
    message: str
    status: MetaIntegrationStatus
    catalog_name: Optional[str] = None
    verification_timestamp: Optional[datetime] = None


class MetaVerificationDetails(BaseModel):
    """Detailed verification information"""

    token_valid: bool
    catalog_accessible: bool
    permissions_valid: bool


class MetaIntegrationStatusResponse(BaseModel):
    """Response model for integration status"""

    status: MetaIntegrationStatus
    catalog_id: Optional[str] = None
    catalog_name: Optional[str] = None
    app_id: Optional[str] = None
    waba_id: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    verification_details: Optional[MetaVerificationDetails] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    last_error_at: Optional[datetime] = None
    message: Optional[str] = None

    @classmethod
    def not_configured(cls):
        """Create response for not configured state"""
        return cls(
            status=MetaIntegrationStatus.PENDING,
            message="Meta credentials not set up for this merchant",
        )

    @classmethod
    def invalid_credentials(cls, error: str, error_code: str, last_error_at: datetime):
        """Create response for invalid credentials state"""
        return cls(
            status=MetaIntegrationStatus.INVALID,
            error=error,
            error_code=error_code,
            last_error_at=last_error_at,
        )


class MetaTokenRotateRequest(BaseModel):
    """Request model for token rotation"""

    system_user_token: str = Field(
        ..., min_length=50, description="New Meta system user access token"
    )

    @validator("system_user_token")
    def validate_token_format(cls, v):
        if not v.startswith(("EAAA", "EAA")):
            raise ValueError("Invalid Meta access token format")
        return v


class MetaIntegrationDB(BaseModel):
    """Database model for Meta integrations"""

    id: UUID
    merchant_id: UUID
    catalog_id: str
    system_user_token_encrypted: str
    app_id: str
    waba_id: Optional[str]
    status: MetaIntegrationStatus
    catalog_name: Optional[str]
    last_verified_at: Optional[datetime]
    last_error: Optional[str]
    error_code: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MetaCredentialsForWorker(BaseModel):
    """Decrypted credentials for sync worker"""

    catalog_id: str
    system_user_token: str
    app_id: str
    waba_id: Optional[str]
    status: MetaIntegrationStatus
    last_verified_at: Optional[datetime]

    def is_usable(self) -> bool:
        """Check if credentials are in a usable state"""
        return self.status == MetaIntegrationStatus.VERIFIED


# SQLAlchemy model for database operations
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class MetaIntegration(Base):
    """Meta integration SQLAlchemy model"""

    __tablename__ = "meta_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)

    # Meta Commerce Catalog credentials (encrypted)
    catalog_id = Column(String(255), nullable=False)
    system_user_token_encrypted = Column(Text, nullable=False)
    app_id = Column(String(255), nullable=False)
    waba_id = Column(String(255))

    # Verification status tracking
    status = Column(String(50), nullable=False, default="pending")
    catalog_name = Column(String(255))
    last_verified_at = Column(DateTime)
    last_error = Column(Text)
    error_code = Column(String(100))

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("merchant_id", name="uq_meta_integrations_merchant"),
    )
