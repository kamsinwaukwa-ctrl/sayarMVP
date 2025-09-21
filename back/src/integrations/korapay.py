"""
Korapay integration helpers with secure API key handling and webhook verification
"""

import os
from typing import Optional, Dict, Any
import httpx
from ..utils.encryption import encrypt_key, decrypt_key
from ..utils.webhook_verification import verify_webhook_signature, WebhookProvider
from ..utils.retry import retry_with_backoff, RetryConfig


class KorapayIntegration:
    """Korapay integration service with secure API key management"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Korapay integration

        Args:
            api_key: Korapay secret key (optional, uses env if not provided)
        """
        self.api_key = api_key or os.getenv("KORAPAY_SECRET_KEY")
        self.base_url = "https://api.korapay.com/merchant/api/v1"

        # Default retry configuration for Korapay API calls
        self.retry_config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
        )

    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt Korapay API key for secure storage

        Args:
            api_key: Plaintext Korapay secret key

        Returns:
            Encrypted API key
        """
        result = encrypt_key(api_key)
        return result.encrypted_data

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt Korapay API key for API calls

        Args:
            encrypted_key: Encrypted Korapay secret key

        Returns:
            Decrypted plaintext API key
        """
        return decrypt_key(encrypted_key)

    @retry_with_backoff()
    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Korapay API with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters

        Returns:
            API response data
        """
        if not self.api_key:
            raise ValueError("Korapay API key not configured")

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=30.0,
            )

            response.raise_for_status()
            return response.json()

    async def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify transaction status

        Args:
            reference: Transaction reference

        Returns:
            Transaction verification response
        """
        return await self.make_request("GET", f"/transactions/{reference}")

    async def initialize_transaction(
        self,
        email: str,
        amount: int,
        reference: str,
        currency: str = "NGN",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initialize a new transaction

        Args:
            email: Customer email
            amount: Amount in kobo
            reference: Transaction reference
            currency: Currency code (default: NGN)
            metadata: Additional metadata

        Returns:
            Transaction initialization response
        """
        data = {
            "email": email,
            "amount": amount,
            "reference": reference,
            "currency": currency,
            "metadata": metadata or {},
        }
        return await self.make_request("POST", "/charges", data=data)

    async def create_virtual_account(
        self,
        customer_name: str,
        customer_email: str,
        bvn: Optional[str] = None,
        permanent: bool = True,
    ) -> Dict[str, Any]:
        """
        Create virtual account for customer

        Args:
            customer_name: Customer full name
            customer_email: Customer email
            bvn: Bank Verification Number (optional)
            permanent: Whether account is permanent

        Returns:
            Virtual account creation response
        """
        data = {
            "customer": {"name": customer_name, "email": customer_email},
            "permanent": permanent,
        }

        if bvn:
            data["customer"]["bvn"] = bvn

        return await self.make_request("POST", "/virtual-accounts", data=data)

    def verify_credentials(
        self, public_key: str, secret_key: str, environment: str = "test"
    ) -> bool:
        """
        Verify Korapay credentials by validating key formats and environment consistency

        Args:
            public_key: Korapay public key
            secret_key: Korapay secret key
            environment: Environment (test/live)

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            # Validate key formats
            if not self._validate_key_format(public_key, "pk_"):
                return False

            if not self._validate_key_format(secret_key, "sk_"):
                return False

            # Validate environment consistency
            env_from_public = self._extract_environment_from_key(public_key)
            env_from_secret = self._extract_environment_from_key(secret_key)

            if env_from_public != env_from_secret:
                return False

            if environment != env_from_public:
                return False

            # Additional validation: check key length
            if len(secret_key) < 20 or len(public_key) < 20:
                return False

            return True

        except Exception:
            return False

    def _validate_key_format(self, key: str, expected_prefix: str) -> bool:
        """Validate Korapay key format"""
        import re

        if not key.startswith(expected_prefix):
            return False

        # Check if key contains environment indicator
        env_pattern = r"_(test|live)_"
        if not re.search(env_pattern, key):
            return False

        return True

    def _extract_environment_from_key(self, key: str) -> Optional[str]:
        """Extract environment from Korapay key"""
        import re

        env_match = re.search(r"_(test|live)_", key)
        if env_match:
            return env_match.group(1)
        return None

    def validate_webhook_signature(
        self, payload: Dict[str, Any], webhook_secret: str
    ) -> bool:
        """
        Validate webhook signature using secret key

        Args:
            payload: Webhook payload
            webhook_secret: Webhook secret for validation

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            import hmac
            import hashlib
            import json

            # Create test signature
            data_string = json.dumps(payload.get("data", {}), separators=(",", ":"))
            expected_signature = hmac.new(
                webhook_secret.encode(), data_string.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, webhook_secret)

        except Exception:
            return False

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify Korapay webhook signature

        Args:
            payload: Raw request body
            signature: X-Korapay-Signature header value

        Returns:
            Webhook verification result
        """
        result = verify_webhook_signature(WebhookProvider.KORAPAY, payload, signature)
        return {
            "is_valid": result.is_valid,
            "payload": result.payload if result.is_valid else {},
            "error": result.error,
        }


def get_korapay_integration() -> KorapayIntegration:
    """
    Get or create global Korapay integration instance

    Returns:
        KorapayIntegration instance
    """
    return KorapayIntegration()
