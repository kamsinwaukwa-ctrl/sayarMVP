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
from ..utils.encryption import get_encryption_service
from ..utils.logger import log
from ..integrations.paystack import PaystackIntegration
from ..integrations.korapay import KorapayIntegration

class PaymentProviderService:
    """Service for managing payment provider credentials"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption_service = get_encryption_service()

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
            paystack = PaystackIntegration(api_key=credentials.secret_key)
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
            korapay = KorapayIntegration()
            verification_success = korapay.verify_credentials(
                public_key=credentials.public_key,
                secret_key=credentials.secret_key,
                environment=credentials.environment.value
            )

            if credentials.webhook_secret:
                # Test webhook signature validation if secret provided
                webhook_valid = korapay.validate_webhook_signature(
                    payload={"test": "data"},
                    webhook_secret=credentials.webhook_secret
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
        encrypted_data = {}
        if credentials_data["public_key"]:
            public_key_result = self.encryption_service.encrypt_data(credentials_data["public_key"])
            encrypted_data["public_key_encrypted"] = public_key_result.encrypted_data

        secret_key_result = self.encryption_service.encrypt_data(credentials_data["secret_key"])
        encrypted_data["secret_key_encrypted"] = secret_key_result.encrypted_data

        if credentials_data.get("webhook_secret"):
            webhook_result = self.encryption_service.encrypt_data(credentials_data["webhook_secret"])
            encrypted_data["webhook_secret_encrypted"] = webhook_result.encrypted_data

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
                public_key_encrypted=encrypted_data.get("public_key_encrypted", ""),
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
                public_key_encrypted=encrypted_data.get("public_key_encrypted", ""),
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
            PaymentProviderConfigResponse.from_attributes(config)
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
        decrypted_data = {}

        if config.public_key_encrypted:
            decrypted_data["public_key"] = self.encryption_service.decrypt_data(config.public_key_encrypted)

        decrypted_data["secret_key"] = self.encryption_service.decrypt_data(config.secret_key_encrypted)

        if config.webhook_secret_encrypted:
            decrypted_data["webhook_secret"] = self.encryption_service.decrypt_data(
                config.webhook_secret_encrypted
            )

        return decrypted_data