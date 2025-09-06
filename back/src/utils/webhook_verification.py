"""
Webhook signature verification utilities for Paystack, Korapay, and WhatsApp
"""

import hashlib
import hmac
import json
from typing import Optional
import os

from ..models.security import WebhookVerificationResult, WebhookProvider


class WebhookVerificationService:
    """Service for verifying webhook signatures from various providers"""
    
    def __init__(self):
        """Initialize with provider-specific secret keys from environment"""
        self.secrets = {
            WebhookProvider.PAYSTACK: os.getenv("PAYSTACK_SECRET_KEY"),
            WebhookProvider.KORAPAY: os.getenv("KORAPAY_SECRET_KEY"),
            WebhookProvider.WHATSAPP: os.getenv("WHATSAPP_APP_SECRET")
        }
    
    def verify_paystack_webhook(
        self, 
        payload: bytes, 
        signature: str, 
        secret_key: Optional[str] = None
    ) -> WebhookVerificationResult:
        """
        Verify Paystack webhook signature using HMAC-SHA512
        
        Args:
            payload: Raw request body bytes
            signature: X-Paystack-Signature header value
            secret_key: Paystack secret key (optional, uses env if not provided)
            
        Returns:
            WebhookVerificationResult with verification status
        """
        secret = secret_key or self.secrets[WebhookProvider.PAYSTACK]
        if not secret:
            return WebhookVerificationResult(
                is_valid=False,
                provider=WebhookProvider.PAYSTACK,
                payload={},
                error="PAYSTACK_SECRET_KEY not configured"
            )
        
        try:
            # Paystack uses HMAC-SHA512 with the raw payload
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha512
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            return WebhookVerificationResult(
                is_valid=is_valid,
                provider=WebhookProvider.PAYSTACK,
                payload=json.loads(payload.decode()) if is_valid else {},
                error=None if is_valid else "Invalid signature"
            )
            
        except Exception as e:
            return WebhookVerificationResult(
                is_valid=False,
                provider=WebhookProvider.PAYSTACK,
                payload={},
                error=f"Verification failed: {e}"
            )
    
    def verify_korapay_webhook(
        self, 
        payload: bytes, 
        signature: str, 
        secret_key: Optional[str] = None
    ) -> WebhookVerificationResult:
        """
        Verify Korapay webhook signature using HMAC-SHA256
        
        Args:
            payload: Raw request body bytes
            signature: X-Korapay-Signature header value
            secret_key: Korapay secret key (optional, uses env if not provided)
            
        Returns:
            WebhookVerificationResult with verification status
        """
        secret = secret_key or self.secrets[WebhookProvider.KORAPAY]
        if not secret:
            return WebhookVerificationResult(
                is_valid=False,
                provider=WebhookProvider.KORAPAY,
                payload={},
                error="KORAPAY_SECRET_KEY not configured"
            )
        
        try:
            # Korapay uses HMAC-SHA256 with the raw payload
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            return WebhookVerificationResult(
                is_valid=is_valid,
                provider=WebhookProvider.KORAPAY,
                payload=json.loads(payload.decode()) if is_valid else {},
                error=None if is_valid else "Invalid signature"
            )
            
        except Exception as e:
            return WebhookVerificationResult(
                is_valid=False,
                provider=WebhookProvider.KORAPAY,
                payload={},
                error=f"Verification failed: {e}"
            )
    
    def verify_whatsapp_webhook(
        self, 
        payload: bytes, 
        signature: str, 
        app_secret: Optional[str] = None
    ) -> WebhookVerificationResult:
        """
        Verify WhatsApp webhook signature using HMAC-SHA256
        
        Args:
            payload: Raw request body bytes
            signature: X-Hub-Signature-256 header value (format: sha256=...)
            app_secret: WhatsApp app secret (optional, uses env if not provided)
            
        Returns:
            WebhookVerificationResult with verification status
        """
        secret = app_secret or self.secrets[WebhookProvider.WHATSAPP]
        if not secret:
            return WebhookVerificationResult(
                is_valid=False,
                provider=WebhookProvider.WHATSAPP,
                payload={},
                error="WHATSAPP_APP_SECRET not configured"
            )
        
        try:
            # WhatsApp uses HMAC-SHA256 and includes 'sha256=' prefix
            if signature.startswith('sha256='):
                signature = signature[7:]  # Remove 'sha256=' prefix
            
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            return WebhookVerificationResult(
                is_valid=is_valid,
                provider=WebhookProvider.WHATSAPP,
                payload=json.loads(payload.decode()) if is_valid else {},
                error=None if is_valid else "Invalid signature"
            )
            
        except Exception as e:
            return WebhookVerificationResult(
                is_valid=False,
                provider=WebhookProvider.WHATSAPP,
                payload={},
                error=f"Verification failed: {e}"
            )
    
    def verify_webhook(
        self, 
        provider: WebhookProvider, 
        payload: bytes, 
        signature: str
    ) -> WebhookVerificationResult:
        """
        Generic webhook verification method that routes to provider-specific verification
        
        Args:
            provider: Webhook provider type
            payload: Raw request body bytes
            signature: Signature header value
            
        Returns:
            WebhookVerificationResult with verification status
        """
        if provider == WebhookProvider.PAYSTACK:
            return self.verify_paystack_webhook(payload, signature)
        elif provider == WebhookProvider.KORAPAY:
            return self.verify_korapay_webhook(payload, signature)
        elif provider == WebhookProvider.WHATSAPP:
            return self.verify_whatsapp_webhook(payload, signature)
        else:
            return WebhookVerificationResult(
                is_valid=False,
                provider=provider,
                payload={},
                error=f"Unsupported provider: {provider}"
            )


# Global webhook verification service instance
_webhook_service: Optional[WebhookVerificationService] = None


def get_webhook_service() -> WebhookVerificationService:
    """
    Get or create global webhook verification service instance
    
    Returns:
        WebhookVerificationService instance
    """
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookVerificationService()
    return _webhook_service


def verify_webhook_signature(
    provider: WebhookProvider, 
    payload: bytes, 
    signature: str
) -> WebhookVerificationResult:
    """
    Verify webhook signature for a specific provider
    
    Args:
        provider: Webhook provider type
        payload: Raw request body bytes
        signature: Signature header value
        
    Returns:
        WebhookVerificationResult with verification status
    """
    service = get_webhook_service()
    return service.verify_webhook(provider, payload, signature)