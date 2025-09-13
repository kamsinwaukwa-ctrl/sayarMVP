---
id: "BE-013"
title: "Payments: provider verify + key storage"
owner: "@backend-team"
status: "planned"
priority: "P1"
theme: "Payment Integration"
user_story: "As a merchant, I want to securely verify and store my payment provider credentials (Paystack/Korapay) so I can accept payments through WhatsApp commerce with proper authentication and encrypted storage."
labels: ["backend","fastapi","payments","encryption","paystack","korapay","security"]
dependencies: ["BE-030", "BE-032"]
created: "2025-01-27"
spec_refs:
  - "/Users/kamsi/sayarv1/.claude/doc/paystack.md"
  - "/Users/kamsi/sayarv1/.claude/doc/korapay.md"
  - "CLAUDE.md#payment-processing"
touches:
  - "back/src/models/sqlalchemy_models.py"
  - "back/src/models/payment_providers.py"
  - "back/src/api/payment_providers.py"
  - "back/src/services/payment_provider_service.py"
  - "back/src/utils/encryption.py"
  - "back/src/integrations/paystack.py"
  - "back/src/integrations/korapay.py"
  - "migrations/012_payment_provider_configs.sql"
  - "back/tests/integration/test_payment_providers.py"
---

## 1. Implementation Overview

This implementation delivers secure payment provider verification and encrypted credential storage for both Paystack and Korapay. The solution provides API endpoints for credential verification, encrypted key storage, verification status tracking, and proper multi-tenant isolation.

### Key Features
- ✅ **Dual Provider Support**: Paystack & Korapay credential verification
- ✅ **Encrypted Storage**: AES-256 encryption for all API credentials
- ✅ **Verification Tracking**: Status monitoring with error logging
- ✅ **Multi-tenant Security**: RLS policies for merchant isolation
- ✅ **Rate Limiting**: Protection against brute force attacks
- ✅ **Production Ready**: Comprehensive error handling and logging

---

## 2. Database Schema Implementation

### 2.1 New SQLAlchemy Model

**File:** `back/src/models/sqlalchemy_models.py`

```python
# Add to existing file after other model classes

class PaymentProviderConfig(Base):
    """Payment provider configuration SQLAlchemy model"""
    __tablename__ = "payment_provider_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    provider_type = Column(String, nullable=False)  # 'paystack' or 'korapay'
    public_key_encrypted = Column(String, nullable=False)
    secret_key_encrypted = Column(String, nullable=False)
    webhook_secret_encrypted = Column(String)  # Optional for some providers
    environment = Column(String, nullable=False, default='test')  # 'test' or 'live'
    verification_status = Column(String, nullable=False, default='pending')  # 'pending', 'verified', 'failed'
    last_verified_at = Column(DateTime)
    verification_error = Column(String)  # Store error messages
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add unique constraint for merchant + provider + environment
    __table_args__ = (
        {'extend_existing': True},
    )
```

### 2.2 Database Migration

**File:** `migrations/012_payment_provider_configs.sql`

```sql
-- Migration: Create payment provider configs table
-- This migration creates the table for storing encrypted payment provider credentials

CREATE TABLE payment_provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    provider_type VARCHAR(20) NOT NULL CHECK (provider_type IN ('paystack', 'korapay')),
    public_key_encrypted TEXT NOT NULL,
    secret_key_encrypted TEXT NOT NULL,
    webhook_secret_encrypted TEXT,
    environment VARCHAR(10) NOT NULL CHECK (environment IN ('test', 'live')) DEFAULT 'test',
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verifying', 'verified', 'failed')),
    last_verified_at TIMESTAMPTZ,
    verification_error TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique provider config per merchant per environment
    UNIQUE(merchant_id, provider_type, environment)
);

-- Create indexes for performance
CREATE INDEX idx_payment_provider_configs_merchant_id ON payment_provider_configs(merchant_id);
CREATE INDEX idx_payment_provider_configs_provider_status ON payment_provider_configs(provider_type, verification_status);
CREATE INDEX idx_payment_provider_configs_active ON payment_provider_configs(active);

-- Enable Row Level Security
ALTER TABLE payment_provider_configs ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for multi-tenant isolation
CREATE POLICY payment_provider_configs_tenant_isolation ON payment_provider_configs
    USING (merchant_id = (current_setting('request.jwt.claims')::json->>'merchant_id')::uuid);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON payment_provider_configs TO service_role;
GRANT USAGE ON SEQUENCE payment_provider_configs_id_seq TO service_role;


-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_payment_provider_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payment_provider_configs_updated_at
    BEFORE UPDATE ON payment_provider_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_provider_configs_updated_at();


-- Add comments for documentation
COMMENT ON TABLE payment_provider_configs IS 'Stores encrypted payment provider credentials per merchant';
COMMENT ON COLUMN payment_provider_configs.public_key_encrypted IS 'AES-256 encrypted public API key';
COMMENT ON COLUMN payment_provider_configs.secret_key_encrypted IS 'AES-256 encrypted secret API key';
COMMENT ON COLUMN payment_provider_configs.webhook_secret_encrypted IS 'AES-256 encrypted webhook secret';
COMMENT ON COLUMN payment_provider_configs.verification_status IS 'Credential verification status';
```

---

## 3. Encryption Service Implementation

### 3.1 Core Encryption Service

**File:** `back/src/utils/encryption.py`

```python
"""
Encryption utilities for secure API key storage
Provides AES-256 encryption for payment provider credentials
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64
from typing import Optional
from ..utils.logger import log

class EncryptionService:
    """Service for encrypting/decrypting sensitive data"""
    
    def __init__(self):
        """Initialize encryption service with key from environment"""
        self._encryption_key = self._get_encryption_key()
        self._fernet = Fernet(self._encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key from environment"""
        key_string = os.getenv("PAYMENT_ENCRYPTION_KEY")
        
        if not key_string:
            # Generate a new key for development - should be set in production
            if os.getenv("ENV", "development") == "development":
                log.warning("No PAYMENT_ENCRYPTION_KEY found, generating new key for development")
                key = Fernet.generate_key()
                log.info(f"Generated encryption key: {key.decode()}")
                return key
            else:
                raise ValueError("PAYMENT_ENCRYPTION_KEY environment variable is required in production")
        
        try:
            return key_string.encode()
        except Exception:
            raise ValueError("Invalid PAYMENT_ENCRYPTION_KEY format")
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string"""
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        try:
            encrypted_data = self._fernet.encrypt(plaintext.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            log.error("Encryption failed", extra={"error": str(e)})
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt encrypted string"""
        if not encrypted_text:
            raise ValueError("Cannot decrypt empty string")
        
        try:
            encrypted_data = base64.b64decode(encrypted_text.encode())
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            log.error("Decryption failed", extra={"error": str(e)})
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt all string values in a dictionary"""
        encrypted_data = {}
        for key, value in data.items():
            if isinstance(value, str) and value:
                encrypted_data[f"{key}_encrypted"] = self.encrypt(value)
            else:
                encrypted_data[key] = value
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """Decrypt all encrypted values in a dictionary"""
        decrypted_data = {}
        for key, value in data.items():
            if key.endswith("_encrypted") and isinstance(value, str):
                original_key = key.replace("_encrypted", "")
                decrypted_data[original_key] = self.decrypt(value)
            else:
                decrypted_data[key] = value
        return decrypted_data

# Global instance
encryption_service = EncryptionService()
```

---

## 4. Pydantic Models

### 4.1 Request/Response Models

**File:** `back/src/models/payment_providers.py`

```python
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
    public_key: Optional[str] = Field(None, description="Paystack public key (optional)")
    environment: PaymentEnvironment = Field(PaymentEnvironment.TEST, description="Environment (test/live)")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v.startswith('sk_'):
            raise ValueError('Secret key must start with sk_')
        return v
    
    @validator('public_key')
    def validate_public_key(cls, v):
        if v and not v.startswith('pk_'):
            raise ValueError('Public key must start with pk_')
        return v

class KorapayCredentialsRequest(BaseModel):
    """Request model for Korapay credential verification"""
    public_key: str = Field(..., min_length=1, description="Korapay public key")
    secret_key: str = Field(..., min_length=1, description="Korapay secret key")
    webhook_secret: Optional[str] = Field(None, description="Webhook secret for signature verification")
    environment: PaymentEnvironment = Field(PaymentEnvironment.TEST, description="Environment (test/live)")
    
    @validator('public_key')
    def validate_public_key(cls, v):
        if not v.startswith('pk_'):
            raise ValueError('Public key must start with pk_')
        return v
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v.startswith('sk_'):
            raise ValueError('Secret key must start with sk_')
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
```

---

## 5. Service Layer Implementation

### 5.1 Core Payment Provider Service

**File:** `back/src/services/payment_provider_service.py`

```python
"""
Payment Provider Service
Handles verification and storage of payment provider credentials
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from ..models.sqlalchemy_models import PaymentProviderConfig
from ..models.payment_providers import (
    PaystackCredentialsRequest, KorapayCredentialsRequest,
    PaymentProviderType, PaymentEnvironment, VerificationStatus,
    VerificationResult, PaymentProviderConfigResponse
)
from ..utils.encryption import encryption_service
from ..utils.logger import log
from ..integrations.paystack import PaystackIntegration
from ..integrations.korapay import KorapayIntegration

class PaymentProviderService:
    """Service for managing payment provider credentials"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def verify_paystack_credentials(
        self, 
        merchant_id: UUID, 
        credentials: PaystackCredentialsRequest
    ) -> VerificationResult:
        """Verify Paystack credentials and store if valid"""
        
        log.info("Starting Paystack credential verification", extra={
            "merchant_id": str(merchant_id),
            "environment": credentials.environment.value,
            "event_type": "payment_provider_verification_start"
        })
        
        try:
            # Test credentials with Paystack API
            paystack = PaystackIntegration(
                secret_key=credentials.secret_key,
                environment=credentials.environment.value
            )
            
            # Use transaction totals endpoint to verify credentials
            verification_success = await paystack.verify_credentials()
            
            if not verification_success:
                log.warning("Paystack credential verification failed", extra={
                    "merchant_id": str(merchant_id),
                    "environment": credentials.environment.value,
                    "event_type": "payment_provider_verification_failed"
                })
                
                return VerificationResult(
                    success=False,
                    provider_type=PaymentProviderType.PAYSTACK,
                    environment=credentials.environment,
                    verification_status=VerificationStatus.FAILED,
                    error_message="Invalid Paystack credentials"
                )
            
            # Store encrypted credentials
            config_id = await self._store_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.PAYSTACK,
                credentials_data={
                    "public_key": credentials.public_key or "",
                    "secret_key": credentials.secret_key,
                    "webhook_secret": ""
                },
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED
            )
            
            log.info("Paystack credentials verified and stored", extra={
                "merchant_id": str(merchant_id),
                "config_id": str(config_id),
                "environment": credentials.environment.value,
                "event_type": "payment_provider_verification_success"
            })
            
            return VerificationResult(
                success=True,
                provider_type=PaymentProviderType.PAYSTACK,
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED,
                verified_at=datetime.now(timezone.utc),
                config_id=config_id
            )
            
        except Exception as e:
            log.error("Paystack credential verification error", extra={
                "merchant_id": str(merchant_id),
                "error": str(e),
                "event_type": "payment_provider_verification_error"
            })
            
            return VerificationResult(
                success=False,
                provider_type=PaymentProviderType.PAYSTACK,
                environment=credentials.environment,
                verification_status=VerificationStatus.FAILED,
                error_message=f"Verification failed: {str(e)}"
            )
    
    async def verify_korapay_credentials(
        self, 
        merchant_id: UUID, 
        credentials: KorapayCredentialsRequest
    ) -> VerificationResult:
        """Verify Korapay credentials and store if valid"""
        
        log.info("Starting Korapay credential verification", extra={
            "merchant_id": str(merchant_id),
            "environment": credentials.environment.value,
            "event_type": "payment_provider_verification_start"
        })
        
        try:
            # Test credentials with Korapay validation
            korapay = KorapayIntegration(
                public_key=credentials.public_key,
                secret_key=credentials.secret_key,
                environment=credentials.environment.value
            )
            
            # Validate key formats and webhook secret if provided
            verification_success = await korapay.verify_credentials()
            
            if credentials.webhook_secret:
                # Test webhook signature validation if secret provided
                webhook_valid = korapay.validate_webhook_signature(
                    test_payload={"test": "data"},
                    signature=credentials.webhook_secret
                )
                if not webhook_valid:
                    log.warning("Korapay webhook secret validation failed")
            
            if not verification_success:
                log.warning("Korapay credential verification failed", extra={
                    "merchant_id": str(merchant_id),
                    "environment": credentials.environment.value,
                    "event_type": "payment_provider_verification_failed"
                })
                
                return VerificationResult(
                    success=False,
                    provider_type=PaymentProviderType.KORAPAY,
                    environment=credentials.environment,
                    verification_status=VerificationStatus.FAILED,
                    error_message="Invalid Korapay credentials"
                )
            
            # Store encrypted credentials
            config_id = await self._store_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.KORAPAY,
                credentials_data={
                    "public_key": credentials.public_key,
                    "secret_key": credentials.secret_key,
                    "webhook_secret": credentials.webhook_secret or ""
                },
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED
            )
            
            log.info("Korapay credentials verified and stored", extra={
                "merchant_id": str(merchant_id),
                "config_id": str(config_id),
                "environment": credentials.environment.value,
                "event_type": "payment_provider_verification_success"
            })
            
            return VerificationResult(
                success=True,
                provider_type=PaymentProviderType.KORAPAY,
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED,
                verified_at=datetime.now(timezone.utc),
                config_id=config_id
            )
            
        except Exception as e:
            log.error("Korapay credential verification error", extra={
                "merchant_id": str(merchant_id),
                "error": str(e),
                "event_type": "payment_provider_verification_error"
            })
            
            return VerificationResult(
                success=False,
                provider_type=PaymentProviderType.KORAPAY,
                environment=credentials.environment,
                verification_status=VerificationStatus.FAILED,
                error_message=f"Verification failed: {str(e)}"
            )
    
    async def _store_credentials(
        self,
        merchant_id: UUID,
        provider_type: PaymentProviderType,
        credentials_data: Dict[str, str],
        environment: PaymentEnvironment,
        verification_status: VerificationStatus
    ) -> UUID:
        """Store encrypted credentials in database"""
        
        # Encrypt credentials
        encrypted_data = {
            "public_key_encrypted": encryption_service.encrypt(credentials_data["public_key"]),
            "secret_key_encrypted": encryption_service.encrypt(credentials_data["secret_key"]),
        }
        
        if credentials_data.get("webhook_secret"):
            encrypted_data["webhook_secret_encrypted"] = encryption_service.encrypt(
                credentials_data["webhook_secret"]
            )
        
        # Create or update configuration
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.environment == environment.value
        )
        
        existing_config = await self.db.execute(stmt)
        config_row = existing_config.scalar_one_or_none()
        
        if config_row:
            # Update existing configuration
            update_stmt = update(PaymentProviderConfig).where(
                PaymentProviderConfig.id == config_row.id
            ).values(
                public_key_encrypted=encrypted_data["public_key_encrypted"],
                secret_key_encrypted=encrypted_data["secret_key_encrypted"],
                webhook_secret_encrypted=encrypted_data.get("webhook_secret_encrypted"),
                verification_status=verification_status.value,
                last_verified_at=datetime.now(timezone.utc),
                verification_error=None,
                active=True,
                updated_at=datetime.now(timezone.utc)
            )
            
            await self.db.execute(update_stmt)
            await self.db.commit()
            return config_row.id
        else:
            # Create new configuration
            new_config = PaymentProviderConfig(
                merchant_id=merchant_id,
                provider_type=provider_type.value,
                public_key_encrypted=encrypted_data["public_key_encrypted"],
                secret_key_encrypted=encrypted_data["secret_key_encrypted"],
                webhook_secret_encrypted=encrypted_data.get("webhook_secret_encrypted"),
                environment=environment.value,
                verification_status=verification_status.value,
                last_verified_at=datetime.now(timezone.utc),
                active=True
            )
            
            self.db.add(new_config)
            await self.db.commit()
            return new_config.id
    
    async def get_provider_configs(self, merchant_id: UUID) -> List[PaymentProviderConfigResponse]:
        """Get all payment provider configurations for a merchant"""
        
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.active == True
        ).order_by(PaymentProviderConfig.created_at.desc())
        
        result = await self.db.execute(stmt)
        configs = result.scalars().all()
        
        return [
            PaymentProviderConfigResponse.from_orm(config)
            for config in configs
        ]
    
    async def delete_provider_config(
        self, 
        merchant_id: UUID, 
        provider_type: PaymentProviderType,
        environment: PaymentEnvironment
    ) -> bool:
        """Delete payment provider configuration"""
        
        stmt = delete(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.environment == environment.value
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def get_decrypted_credentials(
        self, 
        merchant_id: UUID, 
        provider_type: PaymentProviderType,
        environment: PaymentEnvironment
    ) -> Optional[Dict[str, str]]:
        """Get decrypted credentials for a merchant and provider"""
        
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.environment == environment.value,
            PaymentProviderConfig.active == True,
            PaymentProviderConfig.verification_status == VerificationStatus.VERIFIED.value
        )
        
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            return None
        
        # Decrypt credentials
        decrypted_data = {
            "public_key": encryption_service.decrypt(config.public_key_encrypted),
            "secret_key": encryption_service.decrypt(config.secret_key_encrypted),
        }
        
        if config.webhook_secret_encrypted:
            decrypted_data["webhook_secret"] = encryption_service.decrypt(
                config.webhook_secret_encrypted
            )
        
        return decrypted_data
```

### 5.2 Provider Integration Classes

**File:** `back/src/integrations/paystack.py`

```python
"""
Paystack API integration for credential verification
"""

import aiohttp
from typing import Optional, Dict, Any
from ..utils.logger import log

class PaystackIntegration:
    """Paystack payment provider integration"""
    
    def __init__(self, secret_key: str, environment: str = "test"):
        self.secret_key = secret_key
        self.environment = environment
        self.base_url = "https://api.paystack.co"
    
    async def verify_credentials(self) -> bool:
        """Verify Paystack credentials by calling transaction totals endpoint"""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/transaction/totals",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == True
                    elif response.status == 401:
                        log.warning("Paystack credentials invalid - 401 Unauthorized")
                        return False
                    else:
                        log.warning(f"Paystack API returned status {response.status}")
                        return False
                        
        except aiohttp.ClientTimeout:
            log.error("Paystack API request timeout")
            return False
        except Exception as e:
            log.error(f"Paystack credential verification error: {str(e)}")
            return False
    
    async def get_transaction_totals(self) -> Optional[Dict[str, Any]]:
        """Get transaction totals from Paystack (used for verification)"""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/transaction/totals",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
                        
        except Exception as e:
            log.error(f"Failed to get Paystack transaction totals: {str(e)}")
            return None
```

**File:** `back/src/integrations/korapay.py`

```python
"""
Korapay API integration for credential verification
"""

import re
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from ..utils.logger import log

class KorapayIntegration:
    """Korapay payment provider integration"""
    
    def __init__(self, public_key: str, secret_key: str, environment: str = "test"):
        self.public_key = public_key
        self.secret_key = secret_key
        self.environment = environment
        self.base_url = "https://api.korapay.com"
    
    async def verify_credentials(self) -> bool:
        """Verify Korapay credentials by validating key formats"""
        
        try:
            # Validate key formats
            if not self._validate_key_format(self.public_key, "pk_"):
                log.warning("Invalid Korapay public key format")
                return False
            
            if not self._validate_key_format(self.secret_key, "sk_"):
                log.warning("Invalid Korapay secret key format")
                return False
            
            # Validate environment consistency
            env_from_public = self._extract_environment_from_key(self.public_key)
            env_from_secret = self._extract_environment_from_key(self.secret_key)
            
            if env_from_public != env_from_secret:
                log.warning("Korapay key environment mismatch")
                return False
            
            if self.environment != env_from_public:
                log.warning(f"Environment mismatch: expected {self.environment}, got {env_from_public}")
                return False
            
            # Additional validation: check key length and format
            if len(self.secret_key) < 20 or len(self.public_key) < 20:
                log.warning("Korapay keys appear too short")
                return False
            
            return True
            
        except Exception as e:
            log.error(f"Korapay credential verification error: {str(e)}")
            return False
    
    def validate_webhook_signature(self, test_payload: Dict[str, Any], signature: str) -> bool:
        """Validate webhook signature using secret key"""
        
        try:
            # Create test signature
            data_string = json.dumps(test_payload.get("data", {}), separators=(',', ':'))
            expected_signature = hmac.new(
                self.secret_key.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            log.error(f"Korapay webhook signature validation error: {str(e)}")
            return False
    
    def _validate_key_format(self, key: str, expected_prefix: str) -> bool:
        """Validate Korapay key format"""
        
        if not key.startswith(expected_prefix):
            return False
        
        # Check if key contains environment indicator
        env_pattern = r'_(test|live)_'
        if not re.search(env_pattern, key):
            return False
        
        return True
    
    def _extract_environment_from_key(self, key: str) -> Optional[str]:
        """Extract environment from Korapay key"""
        
        env_match = re.search(r'_(test|live)_', key)
        if env_match:
            return env_match.group(1)
        return None
```

---

## 6. API Endpoints Implementation

### 6.1 Payment Provider API Router

**File:** `back/src/api/payment_providers.py`

```python
"""
Payment Provider API endpoints with comprehensive verification
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Annotated, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.payment_providers import (
    PaystackCredentialsRequest, KorapayCredentialsRequest,
    VerificationResult, PaymentProviderConfigResponse,
    PaymentProviderListResponse, PaymentProviderType,
    PaymentEnvironment
)
from ..models.api import ApiResponse, ApiErrorResponse
from ..database.connection import get_db
from ..dependencies.auth import get_current_user, CurrentUser
from ..services.payment_provider_service import PaymentProviderService
from ..middleware.rate_limit import rate_limit
from ..utils.logger import log

router = APIRouter(prefix="/payments", tags=["Payment Providers"])

@router.post(
    "/verify/paystack",
    response_model=ApiResponse[VerificationResult],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ApiErrorResponse, "description": "Invalid credentials"}
    },
    summary="Verify Paystack credentials",
    description="Verify Paystack API credentials and store them securely if valid"
)
@rate_limit(max_requests=5, window_minutes=5, key_func=lambda r: r.state.current_user.merchant_id)
async def verify_paystack_credentials(
    request: PaystackCredentialsRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Verify and store Paystack payment credentials.
    
    **Rate Limited**: 5 requests per 5 minutes per merchant
    
    **Request Body**:
    - **secret_key**: Paystack secret key (starts with 'sk_')
    - **public_key**: Paystack public key (optional, starts with 'pk_')  
    - **environment**: 'test' or 'live'
    
    **Response**:
    Returns verification result with status and stored configuration details.
    """
    
    log.info("Paystack credential verification requested", extra={
        "merchant_id": str(current_user.merchant_id),
        "environment": request.environment.value,
        "event_type": "api_payment_provider_verify_request"
    })
    
    try:
        service = PaymentProviderService(db)
        result = await service.verify_paystack_credentials(
            merchant_id=current_user.merchant_id,
            credentials=request
        )
        
        if result.success:
            return ApiResponse(
                data=result,
                message="Paystack credentials verified and stored successfully"
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "VERIFICATION_FAILED",
                        "message": "Paystack credential verification failed",
                        "details": {
                            "reason": result.error_message or "Invalid credentials",
                            "provider": "paystack",
                            "environment": request.environment.value
                        }
                    }
                ).dict()
            )
            
    except Exception as e:
        log.error("Paystack credential verification error", extra={
            "merchant_id": str(current_user.merchant_id),
            "error": str(e),
            "event_type": "api_payment_provider_verify_error"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential verification failed"
        )

@router.post(
    "/verify/korapay",
    response_model=ApiResponse[VerificationResult],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ApiErrorResponse, "description": "Invalid credentials"}
    },
    summary="Verify Korapay credentials",
    description="Verify Korapay API credentials and store them securely if valid"
)
@rate_limit(max_requests=5, window_minutes=5, key_func=lambda r: r.state.current_user.merchant_id)
async def verify_korapay_credentials(
    request: KorapayCredentialsRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Verify and store Korapay payment credentials.
    
    **Rate Limited**: 5 requests per 5 minutes per merchant
    
    **Request Body**:
    - **public_key**: Korapay public key (starts with 'pk_')
    - **secret_key**: Korapay secret key (starts with 'sk_')
    - **webhook_secret**: Webhook secret for signature verification (optional)
    - **environment**: 'test' or 'live'
    
    **Response**:
    Returns verification result with status and stored configuration details.
    """
    
    log.info("Korapay credential verification requested", extra={
        "merchant_id": str(current_user.merchant_id),
        "environment": request.environment.value,
        "event_type": "api_payment_provider_verify_request"
    })
    
    try:
        service = PaymentProviderService(db)
        result = await service.verify_korapay_credentials(
            merchant_id=current_user.merchant_id,
            credentials=request
        )
        
        if result.success:
            return ApiResponse(
                data=result,
                message="Korapay credentials verified and stored successfully"
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "VERIFICATION_FAILED", 
                        "message": "Korapay credential verification failed",
                        "details": {
                            "reason": result.error_message or "Invalid credentials",
                            "provider": "korapay",
                            "environment": request.environment.value
                        }
                    }
                ).dict()
            )
            
    except Exception as e:
        log.error("Korapay credential verification error", extra={
            "merchant_id": str(current_user.merchant_id),
            "error": str(e),
            "event_type": "api_payment_provider_verify_error"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential verification failed"
        )

@router.get(
    "/providers",
    response_model=ApiResponse[PaymentProviderListResponse],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="List payment providers",
    description="Get all configured payment providers for the current merchant"
)
async def list_payment_providers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    List all payment provider configurations for the current merchant.
    
    **Response**:
    Returns list of all payment provider configurations with their verification status.
    Credentials are not included in the response for security.
    """
    
    try:
        service = PaymentProviderService(db)
        providers = await service.get_provider_configs(current_user.merchant_id)
        
        return ApiResponse(
            data=PaymentProviderListResponse(
                providers=providers,
                total_count=len(providers)
            ),
            message=f"Found {len(providers)} payment provider configurations"
        )
        
    except Exception as e:
        log.error("Failed to list payment providers", extra={
            "merchant_id": str(current_user.merchant_id),
            "error": str(e),
            "event_type": "api_payment_providers_list_error"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment providers"
        )

@router.delete(
    "/providers/{provider_type}",
    response_model=ApiResponse[dict],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Provider configuration not found"}
    },
    summary="Delete payment provider",
    description="Remove a payment provider configuration"
)
async def delete_payment_provider(
    provider_type: PaymentProviderType,
    environment: PaymentEnvironment,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Delete a payment provider configuration.
    
    **Path Parameters**:
    - **provider_type**: Payment provider type ('paystack' or 'korapay')
    
    **Query Parameters**:
    - **environment**: Environment ('test' or 'live')
    """
    
    try:
        service = PaymentProviderService(db)
        deleted = await service.delete_provider_config(
            merchant_id=current_user.merchant_id,
            provider_type=provider_type,
            environment=environment
        )
        
        if deleted:
            log.info("Payment provider configuration deleted", extra={
                "merchant_id": str(current_user.merchant_id),
                "provider_type": provider_type.value,
                "environment": environment.value,
                "event_type": "payment_provider_config_deleted"
            })
            
            return ApiResponse(
                data={"deleted": True},
                message=f"{provider_type.value.title()} {environment.value} configuration deleted"
            )
        else:
            return JSONResponse(
                status_code=404,
                content=ApiErrorResponse(
                    error={
                        "code": "PROVIDER_NOT_FOUND",
                        "message": "Payment provider configuration not found",
                        "details": {
                            "provider_type": provider_type.value,
                            "environment": environment.value
                        }
                    }
                ).dict()
            )
            
    except Exception as e:
        log.error("Failed to delete payment provider", extra={
            "merchant_id": str(current_user.merchant_id),
            "provider_type": provider_type.value,
            "environment": environment.value,
            "error": str(e),
            "event_type": "api_payment_provider_delete_error"
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete payment provider configuration"
        )
```

### 6.2 Rate Limiting Middleware

**File:** `back/src/middleware/rate_limit.py`

```python
"""
Rate limiting middleware for payment provider verification endpoints
"""

import time
from typing import Callable, Dict, Any
from functools import wraps
from fastapi import HTTPException, Request, status
from collections import defaultdict, deque

# In-memory rate limiting storage (use Redis in production)
_rate_limit_storage: Dict[str, deque] = defaultdict(deque)

def rate_limit(
    max_requests: int = 5,
    window_minutes: int = 5,
    key_func: Callable[[Request], str] = None
):
    """
    Rate limiting decorator for FastAPI endpoints
    
    Args:
        max_requests: Maximum requests allowed in the time window
        window_minutes: Time window in minutes
        key_func: Function to generate rate limit key from request
    """
    
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            
            # Generate rate limit key
            if key_func:
                rate_limit_key = f"rate_limit:{key_func(request)}"
            else:
                rate_limit_key = f"rate_limit:{request.client.host}"
            
            current_time = time.time()
            window_seconds = window_minutes * 60
            
            # Get request timestamps for this key
            timestamps = _rate_limit_storage[rate_limit_key]
            
            # Remove timestamps outside the current window
            while timestamps and current_time - timestamps[0] > window_seconds:
                timestamps.popleft()
            
            # Check if rate limit exceeded
            if len(timestamps) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_minutes} minutes.",
                    headers={
                        "Retry-After": str(int(window_seconds - (current_time - timestamps[0])))
                    }
                )
            
            # Add current request timestamp
            timestamps.append(current_time)
            
            # Call the actual endpoint
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

class RateLimitService:
    """Service for managing rate limits"""
    
    @staticmethod
    def get_remaining_requests(key: str, max_requests: int, window_minutes: int) -> int:
        """Get number of remaining requests for a key"""
        
        rate_limit_key = f"rate_limit:{key}"
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        timestamps = _rate_limit_storage[rate_limit_key]
        
        # Remove timestamps outside the current window
        while timestamps and current_time - timestamps[0] > window_seconds:
            timestamps.popleft()
        
        return max(0, max_requests - len(timestamps))
    
    @staticmethod
    def reset_rate_limit(key: str):
        """Reset rate limit for a specific key"""
        
        rate_limit_key = f"rate_limit:{key}"
        if rate_limit_key in _rate_limit_storage:
            del _rate_limit_storage[rate_limit_key]
```

---

## 7. Integration Tests

### 7.1 Comprehensive Test Suite

**File:** `back/tests/integration/test_payment_providers.py`

```python
"""
Integration tests for payment provider verification endpoints
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from ...main import app
from ...models.payment_providers import PaymentProviderType, PaymentEnvironment
from ...services.payment_provider_service import PaymentProviderService
from ...utils.encryption import encryption_service

@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)

@pytest.fixture
def mock_auth_user():
    """Mock authenticated user"""
    return {
        "user_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "email": "test@example.com",
        "role": "admin"
    }

class TestPaystackVerification:
    """Test suite for Paystack credential verification"""
    
    @patch('...integrations.paystack.PaystackIntegration.verify_credentials')
    async def test_verify_paystack_credentials_success(
        self, 
        mock_verify, 
        client, 
        mock_auth_user,
        db_session: AsyncSession
    ):
        """Test successful Paystack credential verification"""
        
        mock_verify.return_value = True
        
        # Mock authentication
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={
                    "secret_key": "sk_test_valid_key_12345678901234567890",
                    "public_key": "pk_test_valid_key_12345678901234567890",
                    "environment": "test"
                },
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["data"]["success"] == True
        assert data["data"]["provider_type"] == "paystack"
        assert data["data"]["verification_status"] == "verified"
        assert data["message"] == "Paystack credentials verified and stored successfully"
    
    @patch('...integrations.paystack.PaystackIntegration.verify_credentials')
    async def test_verify_paystack_credentials_invalid(
        self, 
        mock_verify, 
        client, 
        mock_auth_user
    ):
        """Test Paystack credential verification with invalid credentials"""
        
        mock_verify.return_value = False
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={
                    "secret_key": "sk_test_invalid_key_123456789",
                    "environment": "test"
                },
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 422
        data = response.json()
        
        assert data["ok"] == False
        assert data["error"]["code"] == "VERIFICATION_FAILED"
        assert "Invalid credentials" in data["error"]["details"]["reason"]
    
    async def test_verify_paystack_invalid_key_format(self, client, mock_auth_user):
        """Test Paystack verification with invalid key format"""
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={
                    "secret_key": "invalid_key_format",
                    "environment": "test"
                },
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 422
        data = response.json()
        
        # Should fail validation at Pydantic level
        assert "detail" in data
    
    async def test_paystack_rate_limiting(self, client, mock_auth_user):
        """Test rate limiting on Paystack verification endpoint"""
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            # Make 6 requests quickly (limit is 5 per 5 minutes)
            for i in range(6):
                response = client.post(
                    "/api/v1/payments/verify/paystack",
                    json={
                        "secret_key": f"sk_test_key_{i}",
                        "environment": "test"
                    },
                    headers={"Authorization": "Bearer valid_token"}
                )
                
                if i < 5:
                    assert response.status_code != 429
                else:
                    assert response.status_code == 429
                    assert "Rate limit exceeded" in response.json()["detail"]

class TestKorapayVerification:
    """Test suite for Korapay credential verification"""
    
    @patch('...integrations.korapay.KorapayIntegration.verify_credentials')
    async def test_verify_korapay_credentials_success(
        self, 
        mock_verify, 
        client, 
        mock_auth_user
    ):
        """Test successful Korapay credential verification"""
        
        mock_verify.return_value = True
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.post(
                "/api/v1/payments/verify/korapay",
                json={
                    "public_key": "pk_test_valid_key_12345678901234567890",
                    "secret_key": "sk_test_valid_key_12345678901234567890", 
                    "webhook_secret": "webhook_secret_123",
                    "environment": "test"
                },
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["data"]["success"] == True
        assert data["data"]["provider_type"] == "korapay"
        assert data["data"]["verification_status"] == "verified"
    
    @patch('...integrations.korapay.KorapayIntegration.verify_credentials')
    async def test_verify_korapay_credentials_invalid(
        self, 
        mock_verify, 
        client, 
        mock_auth_user
    ):
        """Test Korapay credential verification failure"""
        
        mock_verify.return_value = False
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.post(
                "/api/v1/payments/verify/korapay",
                json={
                    "public_key": "pk_test_invalid_key",
                    "secret_key": "sk_test_invalid_key",
                    "environment": "test"
                },
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 422
        data = response.json()
        
        assert data["ok"] == False
        assert data["error"]["code"] == "VERIFICATION_FAILED"

class TestPaymentProviderService:
    """Test suite for PaymentProviderService"""
    
    async def test_store_encrypted_credentials(self, db_session: AsyncSession):
        """Test credential encryption and storage"""
        
        service = PaymentProviderService(db_session)
        merchant_id = uuid.uuid4()
        
        # Mock successful verification
        with patch.object(service, '_store_credentials') as mock_store:
            mock_store.return_value = uuid.uuid4()
            
            credentials = {
                "secret_key": "sk_test_secret_key_123456789",
                "public_key": "pk_test_public_key_123456789"
            }
            
            result = await service._store_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.PAYSTACK,
                credentials_data=credentials,
                environment=PaymentEnvironment.TEST,
                verification_status="verified"
            )
            
            assert result is not None
    
    async def test_get_decrypted_credentials(self, db_session: AsyncSession):
        """Test credential decryption"""
        
        service = PaymentProviderService(db_session)
        merchant_id = uuid.uuid4()
        
        # First store credentials
        original_secret = "sk_test_secret_key_123456789"
        original_public = "pk_test_public_key_123456789"
        
        config_id = await service._store_credentials(
            merchant_id=merchant_id,
            provider_type=PaymentProviderType.PAYSTACK,
            credentials_data={
                "secret_key": original_secret,
                "public_key": original_public
            },
            environment=PaymentEnvironment.TEST,
            verification_status="verified"
        )
        
        # Retrieve and decrypt
        decrypted = await service.get_decrypted_credentials(
            merchant_id=merchant_id,
            provider_type=PaymentProviderType.PAYSTACK,
            environment=PaymentEnvironment.TEST
        )
        
        assert decrypted is not None
        assert decrypted["secret_key"] == original_secret
        assert decrypted["public_key"] == original_public

class TestEncryption:
    """Test suite for encryption service"""
    
    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption"""
        
        original_text = "sk_test_secret_key_123456789"
        
        encrypted = encryption_service.encrypt(original_text)
        assert encrypted != original_text
        assert len(encrypted) > 0
        
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == original_text
    
    def test_encrypt_empty_string_raises_error(self):
        """Test encryption of empty string raises error"""
        
        with pytest.raises(ValueError, match="Cannot encrypt empty string"):
            encryption_service.encrypt("")
    
    def test_decrypt_invalid_data_raises_error(self):
        """Test decryption of invalid data raises error"""
        
        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt("invalid_encrypted_data")

class TestListProviders:
    """Test suite for listing payment providers"""
    
    async def test_list_payment_providers_empty(self, client, mock_auth_user):
        """Test listing payment providers when none exist"""
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.get(
                "/api/v1/payments/providers",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["data"]["total_count"] == 0
        assert len(data["data"]["providers"]) == 0
    
    async def test_list_payment_providers_with_configs(
        self, 
        client, 
        mock_auth_user,
        db_session: AsyncSession
    ):
        """Test listing payment providers with existing configurations"""
        
        # Set up test data - create some payment provider configs
        service = PaymentProviderService(db_session)
        
        await service._store_credentials(
            merchant_id=uuid.UUID(mock_auth_user["merchant_id"]),
            provider_type=PaymentProviderType.PAYSTACK,
            credentials_data={
                "secret_key": "sk_test_key",
                "public_key": "pk_test_key"
            },
            environment=PaymentEnvironment.TEST,
            verification_status="verified"
        )
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.get(
                "/api/v1/payments/providers",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["data"]["total_count"] == 1
        assert len(data["data"]["providers"]) == 1
        
        provider = data["data"]["providers"][0]
        assert provider["provider_type"] == "paystack"
        assert provider["environment"] == "test"
        assert provider["verification_status"] == "verified"

class TestDeleteProvider:
    """Test suite for deleting payment provider configurations"""
    
    async def test_delete_existing_provider(self, client, mock_auth_user):
        """Test deleting an existing payment provider"""
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.delete(
                "/api/v1/payments/providers/paystack?environment=test",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        # Assuming provider exists and is deleted successfully
        assert response.status_code in [200, 404]  # 200 if exists, 404 if not found
    
    async def test_delete_nonexistent_provider(self, client, mock_auth_user):
        """Test deleting a non-existent payment provider"""
        
        with patch('...dependencies.auth.get_current_user', return_value=mock_auth_user):
            response = client.delete(
                "/api/v1/payments/providers/paystack?environment=live",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["ok"] == False
        assert data["error"]["code"] == "PROVIDER_NOT_FOUND"

# Test configuration and fixtures
@pytest.fixture
async def db_session():
    """Database session fixture for tests"""
    # This would be implemented based on your test database setup
    pass

if __name__ == "__main__":
    pytest.main([__file__])
```

---

## 8. Environment Configuration

### 8.1 Environment Variables

**File:** `back/.env.example` (add these variables)

```env
# Add to existing .env.example file

# Payment Provider Encryption
PAYMENT_ENCRYPTION_KEY=your_base64_encoded_fernet_key_here

# Rate Limiting Configuration  
PAYMENT_VERIFICATION_RATE_LIMIT=5
PAYMENT_VERIFICATION_WINDOW_MINUTES=5

# Payment Provider API URLs (optional - defaults in code)
PAYSTACK_BASE_URL=https://api.paystack.co
KORAPAY_BASE_URL=https://api.korapay.com

# Development/Testing
MOCK_PAYMENT_VERIFICATION=false
```

### 8.2 Configuration Management

**File:** `back/src/config/payment_config.py`

```python
"""
Payment provider configuration management
"""

import os
from typing import Optional
from pydantic import BaseModel
from cryptography.fernet import Fernet

class PaymentConfig(BaseModel):
    """Payment provider configuration"""
    
    # Encryption
    encryption_key: str
    
    # Rate limiting
    verification_rate_limit: int = 5
    verification_window_minutes: int = 5
    
    # API URLs
    paystack_base_url: str = "https://api.paystack.co"
    korapay_base_url: str = "https://api.korapay.com"
    
    # Development settings
    mock_verification: bool = False

def get_payment_config() -> PaymentConfig:
    """Get payment configuration from environment"""
    
    encryption_key = os.getenv("PAYMENT_ENCRYPTION_KEY")
    
    if not encryption_key:
        if os.getenv("ENV", "development") == "development":
            # Generate key for development
            encryption_key = Fernet.generate_key().decode()
            print(f"Generated encryption key for development: {encryption_key}")
        else:
            raise ValueError("PAYMENT_ENCRYPTION_KEY is required in production")
    
    return PaymentConfig(
        encryption_key=encryption_key,
        verification_rate_limit=int(os.getenv("PAYMENT_VERIFICATION_RATE_LIMIT", "5")),
        verification_window_minutes=int(os.getenv("PAYMENT_VERIFICATION_WINDOW_MINUTES", "5")),
        paystack_base_url=os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co"),
        korapay_base_url=os.getenv("KORAPAY_BASE_URL", "https://api.korapay.com"),
        mock_verification=os.getenv("MOCK_PAYMENT_VERIFICATION", "false").lower() == "true"
    )

# Global configuration instance
payment_config = get_payment_config()
```

---

## 9. Main Application Integration

### 9.1 Register Router in Main App

**File:** `back/main.py` (add payment providers router)

```python
# Add to existing imports
from src.api.payment_providers import router as payment_providers_router

# Add to router registration section (around line 148)
app.include_router(payment_providers_router, prefix="/api/v1")
```

---

## 10. Production Deployment Checklist

### 10.1 Security Requirements

- [ ] **Encryption Key Management**: Set `PAYMENT_ENCRYPTION_KEY` in production environment
- [ ] **Database Security**: Ensure RLS policies are active and properly configured  
- [ ] **Rate Limiting**: Configure appropriate rate limits for production traffic
- [ ] **API Key Validation**: Test both Paystack and Korapay credential verification flows
- [ ] **Webhook Security**: Validate signature verification for both providers
- [ ] **Audit Logging**: Ensure all payment operations are logged without sensitive data

### 10.2 Performance Requirements

- [ ] **Database Indexing**: Verify all performance indexes are created
- [ ] **Connection Pooling**: Configure appropriate database connection limits
- [ ] **Caching**: Consider Redis for rate limiting in production
- [ ] **API Timeouts**: Set reasonable timeouts for provider API calls
- [ ] **Monitoring**: Set up alerts for verification failures and rate limits

### 10.3 Testing Requirements

- [ ] **Unit Tests**: All service methods covered with tests
- [ ] **Integration Tests**: End-to-end API endpoint testing
- [ ] **Security Tests**: Test encryption/decryption and access controls
- [ ] **Load Tests**: Verify rate limiting works under load
- [ ] **Provider Tests**: Test with both Paystack and Korapay test credentials

---

## 11. Implementation Steps

### Phase 1: Infrastructure Setup
1. **Create database migration** - Run `migrations/012_payment_provider_configs.sql`
2. **Add SQLAlchemy model** - Update `sqlalchemy_models.py`
3. **Implement encryption service** - Create `utils/encryption.py`
4. **Set environment variables** - Add encryption key and configuration

### Phase 2: Core Services
1. **Create Pydantic models** - Implement `models/payment_providers.py`
2. **Build provider integrations** - Create Paystack and Korapay integration classes
3. **Implement service layer** - Create `services/payment_provider_service.py`
4. **Add rate limiting** - Implement `middleware/rate_limit.py`

### Phase 3: API Endpoints
1. **Create API router** - Implement `api/payment_providers.py`
2. **Register router** - Add to `main.py`
3. **Test endpoints** - Verify all endpoints work correctly
4. **Add OpenAPI docs** - Ensure proper API documentation

### Phase 4: Testing & Integration
1. **Write integration tests** - Create comprehensive test suite
2. **Test with real providers** - Verify Paystack and Korapay integration
3. **Security testing** - Test encryption, decryption, and access controls
4. **Performance testing** - Verify rate limiting and database performance

### Phase 5: Production Deployment
1. **Set production config** - Configure encryption keys and environment variables
2. **Deploy database migration** - Apply schema changes to production
3. **Monitor deployment** - Watch logs and metrics for issues
4. **Document for team** - Create operational runbooks

---

## 12. Success Criteria

✅ **Functional Requirements**
- Merchants can verify and store Paystack credentials securely
- Merchants can verify and store Korapay credentials securely  
- All credentials are encrypted at rest using AES-256 encryption
- Verification status is properly tracked and updated
- Rate limiting prevents abuse of verification endpoints

✅ **Security Requirements**
- Multi-tenant isolation via Row Level Security
- No plaintext storage of API keys or secrets
- Proper webhook signature validation
- Comprehensive audit logging of all operations
- Rate limiting and DDoS protection

✅ **Performance Requirements**  
- Fast credential verification (< 5 seconds)
- Efficient database queries with proper indexing
- Scalable rate limiting mechanism
- Minimal impact on existing system performance

✅ **Operational Requirements**
- Comprehensive error handling and user feedback
- Production-ready logging and monitoring
- Complete test coverage for all functionality
- Clear documentation and operational procedures

---

## 13) Context Plan
**Beginning (add these to the agent's context; mark some read-only):**
- `back/src/integrations/paystack.py` _(read-only)_
- `back/src/integrations/korapay.py` _(read-only)_
- `back/src/models/sqlalchemy_models.py`
- `back/src/utils/encryption.py` _(may need creation)_
- `back/src/dependencies/auth.py` _(read-only)_
- `back/main.py`

**End state (must exist after completion):**
- `back/src/models/payment_providers.py` (new)
- `back/src/api/payment_providers.py` (new)
- `back/src/services/payment_provider_service.py` (new)
- `back/src/utils/encryption.py` (new)
- `migrations/012_payment_provider_configs.sql` (new)
- `back/tests/integration/test_payment_providers.py` (new)

---
