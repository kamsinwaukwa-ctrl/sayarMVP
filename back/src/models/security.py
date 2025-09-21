"""
Security models for encryption, webhook verification, and retry configuration
"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class WebhookProvider(str, Enum):
    """Webhook provider enumeration"""

    PAYSTACK = "paystack"
    KORAPAY = "korapay"
    WHATSAPP = "whatsapp"


class EncryptionResult(BaseModel):
    """Result of encryption operation"""

    encrypted_data: str
    key_id: str


class WebhookVerificationResult(BaseModel):
    """Result of webhook signature verification"""

    is_valid: bool
    provider: WebhookProvider
    payload: dict
    error: Optional[str] = None


class RetryConfig(BaseModel):
    """Configuration for retry logic with exponential backoff"""

    max_attempts: int = 8
    base_delay: float = 1.0
    max_delay: float = 300.0
    exponential_base: float = 2.0
    jitter: bool = True
