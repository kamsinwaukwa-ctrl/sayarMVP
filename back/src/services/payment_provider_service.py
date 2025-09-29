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
import os
import asyncio
import aiohttp
from decimal import Decimal

from ..models.sqlalchemy_models import PaymentProviderConfig
from ..models.payment_providers import (
    PaystackCredentialsRequest,
    KorapayCredentialsRequest,
    PaymentProviderType,
    PaymentEnvironment,
    VerificationStatus,
    VerificationResult,
    PaymentProviderConfigResponse,
    SubaccountUpdateRequest,
    SubaccountUpdateResponse,
    SyncStatus,
    Bank,
    BankListResponse,
    AccountResolutionResponse,
    SubaccountRequest,
    SubaccountResponse,
    SettlementSchedule,
)
from ..utils.encryption import get_encryption_service
from ..utils.logger import log
from ..integrations.paystack import PaystackIntegration
from ..integrations.korapay import KorapayIntegration


class PaymentProviderService:
    """Service for managing payment provider credentials"""

    # Class-level cache for banks
    _banks_cache: Optional[List[Bank]] = None
    _banks_cache_timestamp: Optional[datetime] = None
    _banks_cache_ttl = 6 * 60 * 60  # 6 hours in seconds

    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption_service = get_encryption_service()

    async def verify_paystack_credentials(
        self, merchant_id: UUID, credentials: PaystackCredentialsRequest
    ) -> VerificationResult:
        """Verify Paystack credentials and store if valid"""

        log.info(
            "Starting Paystack credential verification",
            extra={
                "merchant_id": str(merchant_id),
                "environment": credentials.environment.value,
                "event_type": "payment_provider_verification_start",
            },
        )

        try:
            # Test credentials with Paystack API
            paystack = PaystackIntegration(api_key=credentials.secret_key)
            verification_success = await paystack.verify_credentials()

            if not verification_success:
                log.warning(
                    "Paystack credential verification failed",
                    extra={
                        "merchant_id": str(merchant_id),
                        "environment": credentials.environment.value,
                        "event_type": "payment_provider_verification_failed",
                    },
                )

                return VerificationResult(
                    success=False,
                    provider_type=PaymentProviderType.PAYSTACK,
                    environment=credentials.environment,
                    verification_status=VerificationStatus.FAILED,
                    error_message="Invalid Paystack credentials",
                )

            # Store encrypted credentials
            config_id = await self._store_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.PAYSTACK,
                credentials_data={
                    "public_key": credentials.public_key or "",
                    "secret_key": credentials.secret_key,
                    "webhook_secret": "",
                },
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED,
            )

            log.info(
                "Paystack credentials verified and stored",
                extra={
                    "merchant_id": str(merchant_id),
                    "config_id": str(config_id),
                    "environment": credentials.environment.value,
                    "event_type": "payment_provider_verification_success",
                },
            )

            return VerificationResult(
                success=True,
                provider_type=PaymentProviderType.PAYSTACK,
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED,
                verified_at=datetime.utcnow(),
                config_id=config_id,
            )

        except Exception as e:
            log.error(
                "Paystack credential verification error",
                extra={
                    "merchant_id": str(merchant_id),
                    "error": str(e),
                    "event_type": "payment_provider_verification_error",
                },
            )

            return VerificationResult(
                success=False,
                provider_type=PaymentProviderType.PAYSTACK,
                environment=credentials.environment,
                verification_status=VerificationStatus.FAILED,
                error_message=f"Verification failed: {str(e)}",
            )

    async def verify_korapay_credentials(
        self, merchant_id: UUID, credentials: KorapayCredentialsRequest
    ) -> VerificationResult:
        """Verify Korapay credentials and store if valid"""

        log.info(
            "Starting Korapay credential verification",
            extra={
                "merchant_id": str(merchant_id),
                "environment": credentials.environment.value,
                "event_type": "payment_provider_verification_start",
            },
        )

        try:
            # Test credentials with Korapay validation
            korapay = KorapayIntegration()
            verification_success = korapay.verify_credentials(
                public_key=credentials.public_key,
                secret_key=credentials.secret_key,
                environment=credentials.environment.value,
            )

            if credentials.webhook_secret:
                # Test webhook signature validation if secret provided
                webhook_valid = korapay.validate_webhook_signature(
                    payload={"test": "data"}, webhook_secret=credentials.webhook_secret
                )
                if not webhook_valid:
                    log.warning("Korapay webhook secret validation failed")

            if not verification_success:
                log.warning(
                    "Korapay credential verification failed",
                    extra={
                        "merchant_id": str(merchant_id),
                        "environment": credentials.environment.value,
                        "event_type": "payment_provider_verification_failed",
                    },
                )

                return VerificationResult(
                    success=False,
                    provider_type=PaymentProviderType.KORAPAY,
                    environment=credentials.environment,
                    verification_status=VerificationStatus.FAILED,
                    error_message="Invalid Korapay credentials",
                )

            # Store encrypted credentials
            config_id = await self._store_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.KORAPAY,
                credentials_data={
                    "public_key": credentials.public_key,
                    "secret_key": credentials.secret_key,
                    "webhook_secret": credentials.webhook_secret or "",
                },
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED,
            )

            log.info(
                "Korapay credentials verified and stored",
                extra={
                    "merchant_id": str(merchant_id),
                    "config_id": str(config_id),
                    "environment": credentials.environment.value,
                    "event_type": "payment_provider_verification_success",
                },
            )

            return VerificationResult(
                success=True,
                provider_type=PaymentProviderType.KORAPAY,
                environment=credentials.environment,
                verification_status=VerificationStatus.VERIFIED,
                verified_at=datetime.utcnow(),
                config_id=config_id,
            )

        except Exception as e:
            log.error(
                "Korapay credential verification error",
                extra={
                    "merchant_id": str(merchant_id),
                    "error": str(e),
                    "event_type": "payment_provider_verification_error",
                },
            )

            return VerificationResult(
                success=False,
                provider_type=PaymentProviderType.KORAPAY,
                environment=credentials.environment,
                verification_status=VerificationStatus.FAILED,
                error_message=f"Verification failed: {str(e)}",
            )

    async def _store_credentials(
        self,
        merchant_id: UUID,
        provider_type: PaymentProviderType,
        credentials_data: Dict[str, str],
        environment: PaymentEnvironment,
        verification_status: VerificationStatus,
    ) -> UUID:
        """Store encrypted credentials in database"""

        # Encrypt credentials
        encrypted_data = {}
        if credentials_data["public_key"]:
            public_key_result = self.encryption_service.encrypt_data(
                credentials_data["public_key"]
            )
            encrypted_data["public_key_encrypted"] = public_key_result.encrypted_data

        secret_key_result = self.encryption_service.encrypt_data(
            credentials_data["secret_key"]
        )
        encrypted_data["secret_key_encrypted"] = secret_key_result.encrypted_data

        if credentials_data.get("webhook_secret"):
            webhook_result = self.encryption_service.encrypt_data(
                credentials_data["webhook_secret"]
            )
            encrypted_data["webhook_secret_encrypted"] = webhook_result.encrypted_data

        # Create or update configuration
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.environment == environment.value,
        )

        existing_config = await self.db.execute(stmt)
        config_row = existing_config.scalar_one_or_none()

        if config_row:
            # Update existing configuration
            update_stmt = (
                update(PaymentProviderConfig)
                .where(PaymentProviderConfig.id == config_row.id)
                .values(
                    public_key_encrypted=encrypted_data.get("public_key_encrypted", ""),
                    secret_key_encrypted=encrypted_data["secret_key_encrypted"],
                    webhook_secret_encrypted=encrypted_data.get(
                        "webhook_secret_encrypted"
                    ),
                    verification_status=verification_status.value,
                    last_verified_at=datetime.utcnow(),
                    verification_error=None,
                    active=True,
                    updated_at=datetime.utcnow(),
                )
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
                last_verified_at=datetime.utcnow(),
                active=True,
            )

            self.db.add(new_config)
            await self.db.commit()
            return new_config.id

    async def get_provider_configs(
        self, merchant_id: UUID
    ) -> List[PaymentProviderConfigResponse]:
        """Get all payment provider configurations for a merchant"""

        stmt = (
            select(PaymentProviderConfig)
            .where(
                PaymentProviderConfig.merchant_id == merchant_id,
                PaymentProviderConfig.active == True,
            )
            .order_by(PaymentProviderConfig.created_at.desc())
        )

        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        return [
            PaymentProviderConfigResponse.from_attributes(config) for config in configs
        ]

    async def delete_provider_config(
        self,
        merchant_id: UUID,
        provider_type: PaymentProviderType,
        environment: PaymentEnvironment,
    ) -> bool:
        """Delete payment provider configuration"""

        stmt = delete(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.environment == environment.value,
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount > 0

    async def get_decrypted_credentials(
        self,
        merchant_id: UUID,
        provider_type: PaymentProviderType,
        environment: PaymentEnvironment,
    ) -> Optional[Dict[str, str]]:
        """Get decrypted credentials for a merchant and provider"""

        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.environment == environment.value,
            PaymentProviderConfig.active == True,
            PaymentProviderConfig.verification_status
            == VerificationStatus.VERIFIED.value,
        )

        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            return None

        # Decrypt credentials
        decrypted_data = {}

        if config.public_key_encrypted:
            decrypted_data["public_key"] = self.encryption_service.decrypt_data(
                config.public_key_encrypted
            )

        decrypted_data["secret_key"] = self.encryption_service.decrypt_data(
            config.secret_key_encrypted
        )

        if config.webhook_secret_encrypted:
            decrypted_data["webhook_secret"] = self.encryption_service.decrypt_data(
                config.webhook_secret_encrypted
            )

        return decrypted_data

    async def get_nigerian_banks(self) -> BankListResponse:
        """Get list of Nigerian banks from Paystack with caching"""

        # Check cache validity
        now = datetime.utcnow()
        if (
            self._banks_cache
            and self._banks_cache_timestamp
            and (now - self._banks_cache_timestamp).total_seconds() < self._banks_cache_ttl
        ):
            log.info("Returning cached banks list")
            return BankListResponse(
                banks=self._banks_cache,
                total_count=len(self._banks_cache),
                cached=True,
            )

        # Fetch from Paystack
        paystack_secret = os.getenv("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            raise ValueError("PAYSTACK_SECRET_KEY environment variable not set")

        url = "https://api.paystack.co/bank"
        headers = {
            "Authorization": f"Bearer {paystack_secret}",
            "Content-Type": "application/json",
        }
        params = {
            "country": "nigeria",
            "perPage": 100,  # Get all Nigerian banks
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"Paystack API error: {response.status}")

                    data = await response.json()

                    if not data.get("status"):
                        raise Exception(f"Paystack API error: {data.get('message')}")

                    # Transform to our Bank model
                    banks = [
                        Bank(
                            name=bank["name"],
                            code=bank["code"],
                            slug=bank.get("slug"),
                            country=bank.get("country"),
                            currency=bank.get("currency"),
                            type=bank.get("type"),
                            active=bank.get("active", True),
                        )
                        for bank in data["data"]
                        if bank.get("active", True)  # Only active banks
                    ]

                    # Cache results
                    self._banks_cache = banks
                    self._banks_cache_timestamp = now

                    log.info(
                        f"Fetched {len(banks)} Nigerian banks from Paystack",
                        extra={"event_type": "banks_list_fetched", "count": len(banks)},
                    )

                    return BankListResponse(
                        banks=banks,
                        total_count=len(banks),
                        cached=False,
                    )

        except Exception as e:
            log.error(
                "Failed to fetch banks from Paystack",
                extra={"error": str(e), "event_type": "banks_list_error"},
            )
            raise

    async def resolve_account(
        self, account_number: str, bank_code: str
    ) -> AccountResolutionResponse:
        """Resolve bank account number using Paystack"""

        paystack_secret = os.getenv("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            raise ValueError("PAYSTACK_SECRET_KEY environment variable not set")

        url = "https://api.paystack.co/bank/resolve"
        headers = {
            "Authorization": f"Bearer {paystack_secret}",
            "Content-Type": "application/json",
        }
        params = {
            "account_number": account_number,
            "bank_code": bank_code,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("status"):
                        return AccountResolutionResponse(
                            success=True,
                            data={
                                "account_number": data["data"]["account_number"],
                                "account_name": data["data"]["account_name"],
                            },
                        )
                    else:
                        error_msg = data.get("message", "Account resolution failed")
                        log.warning(
                            "Account resolution failed",
                            extra={
                                "account_last4": account_number[-4:],
                                "bank_code": bank_code,
                                "error": error_msg,
                                "event_type": "account_resolution_failed",
                            },
                        )
                        return AccountResolutionResponse(
                            success=False,
                            error_message=error_msg,
                        )

        except Exception as e:
            log.error(
                "Account resolution error",
                extra={
                    "account_last4": account_number[-4:],
                    "bank_code": bank_code,
                    "error": str(e),
                    "event_type": "account_resolution_error",
                },
            )
            return AccountResolutionResponse(
                success=False,
                error_message=f"Account resolution failed: {str(e)}",
            )

    async def create_paystack_subaccount(
        self, merchant_id: UUID, subaccount_data: SubaccountRequest
    ) -> SubaccountResponse:
        """Create Paystack subaccount and save configuration with proper error handling"""

        # Check if configuration already exists (idempotency)
        existing_config = await self._get_existing_config_by_merchant_provider(
            merchant_id, PaymentProviderType.PAYSTACK
        )
        if existing_config and existing_config.subaccount_code:
            # Return existing configuration (idempotent behavior)
            log.info(
                "Subaccount already exists, returning existing configuration",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": existing_config.subaccount_code,
                    "event_type": "subaccount_exists",
                },
            )
            return SubaccountResponse(
                success=True,
                subaccount_code=existing_config.subaccount_code,
                account_name=existing_config.account_name,
                account_last4=existing_config.account_last4,
                business_name=subaccount_data.business_name,
                bank_name=existing_config.bank_name,
                percentage_charge=existing_config.percentage_charge,
                settlement_schedule=existing_config.settlement_schedule or "AUTO",
            )

        # Validate required environment variables
        paystack_secret = os.getenv("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            raise ValueError("PAYSTACK_SECRET_KEY environment variable not set")

        # Explicitly set settlement_schedule to 'AUTO' (guardrail)
        settlement_schedule = subaccount_data.settlement_schedule or "AUTO"

        # Security: Extract only last 4 digits of account number (never store full number)
        account_last4 = subaccount_data.account_number[-4:]

        # Resolve account name from Paystack before creating subaccount
        account_resolution = await self.resolve_account(
            account_number=subaccount_data.account_number,
            bank_code=subaccount_data.bank_code,
        )

        if not account_resolution.success:
            return SubaccountResponse(
                success=False,
                error_message=f"Account verification failed: {account_resolution.error_message}",
            )

        account_name = account_resolution.data["account_name"]

        url = "https://api.paystack.co/subaccount"
        headers = {
            "Authorization": f"Bearer {paystack_secret}",
            "Content-Type": "application/json",
        }
        payload = {
            "business_name": subaccount_data.business_name,
            "settlement_bank": subaccount_data.bank_code,
            "account_number": subaccount_data.account_number,  # Sent to Paystack but not stored
            "percentage_charge": float(subaccount_data.percentage_charge),
        }

        try:
            # Create Paystack subaccount
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()

                    if response.status == 201 and data.get("status"):
                        # Extract subaccount details (do not store any PII from Paystack response)
                        subaccount_info = data["data"]
                        subaccount_code = subaccount_info["subaccount_code"]
                        bank_name = subaccount_info.get("settlement_bank", "Unknown Bank")

                        try:
                            # Save to database (atomic transaction)
                            config_id = await self._save_subaccount_config(
                                merchant_id=merchant_id,
                                subaccount_code=subaccount_code,
                                bank_code=subaccount_data.bank_code,
                                bank_name=bank_name,
                                account_name=account_name,
                                account_last4=account_last4,
                                percentage_charge=subaccount_data.percentage_charge,
                                settlement_schedule=settlement_schedule,
                            )

                            log.info(
                                "Subaccount created and configured successfully",
                                extra={
                                    "merchant_id": str(merchant_id),
                                    "config_id": str(config_id),
                                    "subaccount_code": subaccount_code,
                                    "business_name": subaccount_data.business_name,
                                    "event_type": "subaccount_created",
                                },
                            )

                            return SubaccountResponse(
                                success=True,
                                subaccount_code=subaccount_code,
                                account_name=account_name,
                                account_last4=account_last4,
                                business_name=subaccount_data.business_name,
                                bank_name=bank_name,
                                percentage_charge=subaccount_data.percentage_charge,
                                settlement_schedule=settlement_schedule,
                            )

                        except Exception as db_error:
                            # Database save failed after Paystack creation succeeded
                            # Log the issue but don't attempt cleanup (merchant can retry)
                            log.error(
                                "Database save failed after Paystack subaccount creation",
                                extra={
                                    "merchant_id": str(merchant_id),
                                    "subaccount_code": subaccount_code,
                                    "db_error": str(db_error),
                                    "event_type": "subaccount_db_save_failed",
                                },
                            )
                            return SubaccountResponse(
                                success=False,
                                error_message="Subaccount created but configuration save failed. Please contact support.",
                            )

                    else:
                        # Paystack API returned error
                        error_msg = data.get("message", "Subaccount creation failed")
                        log.error(
                            "Paystack subaccount creation failed",
                            extra={
                                "merchant_id": str(merchant_id),
                                "business_name": subaccount_data.business_name,
                                "paystack_error": error_msg,
                                "event_type": "paystack_subaccount_creation_failed",
                            },
                        )
                        return SubaccountResponse(
                            success=False,
                            error_message=f"Payment provider error: {error_msg}",
                        )

        except aiohttp.ClientError as network_error:
            # Network or HTTP-level error
            log.error(
                "Network error during subaccount creation",
                extra={
                    "merchant_id": str(merchant_id),
                    "business_name": subaccount_data.business_name,
                    "network_error": str(network_error),
                    "event_type": "subaccount_network_error",
                },
            )
            return SubaccountResponse(
                success=False,
                error_message="Network error. Please check your connection and try again.",
            )

        except Exception as e:
            # Unexpected error
            log.error(
                "Unexpected error during subaccount creation",
                extra={
                    "merchant_id": str(merchant_id),
                    "business_name": subaccount_data.business_name,
                    "error": str(e),
                    "event_type": "subaccount_creation_unexpected_error",
                },
            )
            return SubaccountResponse(
                success=False,
                error_message="An unexpected error occurred. Please try again.",
            )

    async def _get_existing_subaccount(self, merchant_id: UUID) -> Optional[PaymentProviderConfig]:
        """Check if merchant already has a Paystack subaccount (legacy method)"""

        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == PaymentProviderType.PAYSTACK.value,
            PaymentProviderConfig.subaccount_code.isnot(None),
            PaymentProviderConfig.active == True,
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_existing_config_by_merchant_provider(
        self, merchant_id: UUID, provider_type: PaymentProviderType
    ) -> Optional[PaymentProviderConfig]:
        """Get existing payment provider configuration by merchant and provider (for idempotency)"""

        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == provider_type.value,
            PaymentProviderConfig.active == True,
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _save_subaccount_config(
        self,
        merchant_id: UUID,
        subaccount_code: str,
        bank_code: str,
        bank_name: str,
        account_name: str,
        account_last4: str,
        percentage_charge: Decimal,
        settlement_schedule: str,
    ) -> UUID:
        """Save subaccount configuration to database with idempotent upsert"""

        # Explicitly set settlement_schedule to 'AUTO' if not provided (guardrail)
        if not settlement_schedule:
            settlement_schedule = "AUTO"

        # Check for existing configuration (idempotency by merchant_id + provider_type)
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == PaymentProviderType.PAYSTACK.value,
            PaymentProviderConfig.active == True,
        )

        result = await self.db.execute(stmt)
        existing_config = result.scalar_one_or_none()

        if existing_config:
            # Update existing configuration (idempotent upsert)
            update_stmt = (
                update(PaymentProviderConfig)
                .where(PaymentProviderConfig.id == existing_config.id)
                .values(
                    subaccount_code=subaccount_code,
                    bank_code=bank_code,
                    bank_name=bank_name,
                    account_name=account_name,
                    account_last4=account_last4,
                    percentage_charge=percentage_charge,
                    settlement_schedule=settlement_schedule,
                    verification_status=VerificationStatus.VERIFIED.value,
                    last_verified_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )

            await self.db.execute(update_stmt)
            await self.db.commit()

            log.info(
                "Updated existing subaccount configuration",
                extra={
                    "merchant_id": str(merchant_id),
                    "config_id": str(existing_config.id),
                    "event_type": "subaccount_config_updated",
                },
            )

            return existing_config.id
        else:
            # Create new configuration
            new_config = PaymentProviderConfig(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.PAYSTACK.value,
                bank_code=bank_code,
                bank_name=bank_name,
                environment="test",  # Start with test environment
                verification_status=VerificationStatus.VERIFIED.value,
                last_verified_at=datetime.utcnow(),
                active=True,
                subaccount_code=subaccount_code,
                account_name=account_name,
                account_last4=account_last4,
                percentage_charge=percentage_charge,
                settlement_schedule=settlement_schedule,
            )

            self.db.add(new_config)
            await self.db.commit()

            log.info(
                "Created new subaccount configuration",
                extra={
                    "merchant_id": str(merchant_id),
                    "config_id": str(new_config.id),
                    "event_type": "subaccount_config_created",
                },
            )

            return new_config.id

    # New methods for Paystack-first pattern (no API keys stored)

    async def get_provider_configs_simple(self, merchant_id: UUID) -> List[PaymentProviderConfigResponse]:
        """
        Get payment provider configurations (cached metadata only).
        Fast DB-only query for Settings tab display.
        """
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.active == True
        )

        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        return [
            PaymentProviderConfigResponse.from_orm(config)
            for config in configs
        ]

    async def update_paystack_subaccount(
        self,
        merchant_id: UUID,
        update_data: SubaccountUpdateRequest
    ) -> SubaccountUpdateResponse:
        """
        Update Paystack subaccount: Paystack API first, then sync our DB.
        Implements the planned error handling strategy.
        """

        # 1. Get current config to find subaccount_code
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == PaymentProviderType.PAYSTACK.value,
            PaymentProviderConfig.active == True
        )
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config or not config.subaccount_code:
            return SubaccountUpdateResponse(
                success=False,
                message="No Paystack subaccount found for this merchant",
            )

        try:
            # 2. Call Paystack Update Subaccount API first
            paystack_updated_data = await self._call_paystack_update_subaccount(
                config.subaccount_code,
                update_data
            )

            log.info(
                "Paystack subaccount update succeeded",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": config.subaccount_code,
                    "updated_fields": list(update_data.dict(exclude_unset=True).keys()),
                    "event_type": "paystack_subaccount_update_success",
                },
            )

        except Exception as paystack_error:
            # Paystack failed → return error immediately, no DB changes
            log.error(
                "Paystack subaccount update failed",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": config.subaccount_code,
                    "error": str(paystack_error),
                    "event_type": "paystack_subaccount_update_failed",
                },
            )

            return SubaccountUpdateResponse(
                success=False,
                message=f"Paystack update failed: {str(paystack_error)}",
                subaccount_code=config.subaccount_code,
                sync_status=config.sync_status
            )

        # 3. Paystack succeeded → update our DB
        try:
            updated_fields = []
            update_values = {
                "sync_status": SyncStatus.SYNCED.value,
                "last_synced_with_provider": datetime.now(timezone.utc),
                "sync_error": None,
                "updated_at": datetime.now(timezone.utc),
            }

            # Update only the fields that were provided and successfully updated by Paystack
            if paystack_updated_data.get("bank_code"):
                update_values["bank_code"] = paystack_updated_data["bank_code"]
                update_values["bank_name"] = paystack_updated_data.get("settlement_bank", "")
                updated_fields.append("bank")

            if paystack_updated_data.get("account_number"):
                update_values["account_last4"] = paystack_updated_data["account_number"][-4:]
                update_values["account_name"] = paystack_updated_data.get("account_name", "")
                updated_fields.append("account")

            if paystack_updated_data.get("percentage_charge") is not None:
                update_values["percentage_charge"] = Decimal(str(paystack_updated_data["percentage_charge"]))
                updated_fields.append("percentage_charge")

            if paystack_updated_data.get("settlement_schedule"):
                update_values["settlement_schedule"] = paystack_updated_data["settlement_schedule"]
                updated_fields.append("settlement_schedule")

            update_stmt = (
                update(PaymentProviderConfig)
                .where(PaymentProviderConfig.id == config.id)
                .values(**update_values)
            )

            await self.db.execute(update_stmt)
            await self.db.commit()

            log.info(
                "Database sync completed after Paystack update",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": config.subaccount_code,
                    "updated_fields": updated_fields,
                    "event_type": "paystack_subaccount_db_sync_success",
                },
            )

            return SubaccountUpdateResponse(
                success=True,
                message="Subaccount updated successfully",
                subaccount_code=config.subaccount_code,
                sync_status=SyncStatus.SYNCED,
                updated_fields=updated_fields
            )

        except Exception as db_error:
            # Paystack succeeded but DB failed → partial success with outbox retry
            log.error(
                "Database sync failed after Paystack update",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": config.subaccount_code,
                    "db_error": str(db_error),
                    "event_type": "paystack_subaccount_db_sync_failed",
                },
            )

            # Enqueue ReconcileSubaccount outbox job for background healing
            await self._enqueue_reconcile_subaccount_job(merchant_id, config.subaccount_code)

            return SubaccountUpdateResponse(
                success=True,
                partial_success=True,
                message="Updated on Paystack. Syncing your dashboard…",
                subaccount_code=config.subaccount_code,
                sync_status=SyncStatus.PENDING,
                updated_fields=list(update_data.dict(exclude_unset=True).keys())
            )

    async def sync_paystack_subaccount(self, merchant_id: UUID) -> PaymentProviderConfigResponse:
        """
        Manual sync: fetch fresh data from Paystack and update our DB.
        Used for the "Sync with Paystack" button.
        """

        # Get current config
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == merchant_id,
            PaymentProviderConfig.provider_type == PaymentProviderType.PAYSTACK.value,
            PaymentProviderConfig.active == True
        )
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config or not config.subaccount_code:
            raise ValueError("No Paystack subaccount found for this merchant")

        try:
            # Fetch latest data from Paystack
            paystack_data = await self._call_paystack_get_subaccount(config.subaccount_code)

            # Update our DB with fresh data
            update_values = {
                "bank_code": paystack_data.get("bank_code", config.bank_code),
                "bank_name": paystack_data.get("settlement_bank", config.bank_name),
                "account_name": paystack_data.get("account_name", config.account_name),
                "account_last4": paystack_data.get("account_number", "")[-4:] if paystack_data.get("account_number") else config.account_last4,
                "percentage_charge": Decimal(str(paystack_data.get("percentage_charge", config.percentage_charge or 0))),
                "settlement_schedule": paystack_data.get("settlement_schedule", config.settlement_schedule),
                "sync_status": SyncStatus.SYNCED.value,
                "last_synced_with_provider": datetime.now(timezone.utc),
                "sync_error": None,
                "updated_at": datetime.now(timezone.utc),
            }

            update_stmt = (
                update(PaymentProviderConfig)
                .where(PaymentProviderConfig.id == config.id)
                .values(**update_values)
            )

            await self.db.execute(update_stmt)
            await self.db.commit()

            log.info(
                "Manual Paystack sync completed",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": config.subaccount_code,
                    "event_type": "paystack_manual_sync_success",
                },
            )

            # Return fresh config
            result = await self.db.execute(stmt)
            updated_config = result.scalar_one()
            return PaymentProviderConfigResponse.from_orm(updated_config)

        except Exception as sync_error:
            # Mark sync as failed
            update_stmt = (
                update(PaymentProviderConfig)
                .where(PaymentProviderConfig.id == config.id)
                .values(
                    sync_status=SyncStatus.FAILED.value,
                    sync_error=str(sync_error),
                    updated_at=datetime.now(timezone.utc),
                )
            )

            await self.db.execute(update_stmt)
            await self.db.commit()

            log.error(
                "Manual Paystack sync failed",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": config.subaccount_code,
                    "error": str(sync_error),
                    "event_type": "paystack_manual_sync_failed",
                },
            )

            raise Exception(f"Sync failed: {str(sync_error)}")

    async def _call_paystack_update_subaccount(self, subaccount_code: str, update_data: SubaccountUpdateRequest) -> Dict[str, Any]:
        """
        Call Paystack PUT /subaccount/:subaccount_code API.
        Uses platform-level API keys (not stored per merchant).
        """

        # Build update payload (only include non-None fields)
        payload = {}
        update_dict = update_data.dict(exclude_unset=True)

        if "business_name" in update_dict:
            payload["business_name"] = update_dict["business_name"]
        if "bank_code" in update_dict:
            payload["bank_code"] = update_dict["bank_code"]
        if "account_number" in update_dict:
            payload["account_number"] = update_dict["account_number"]
        if "percentage_charge" in update_dict:
            payload["percentage_charge"] = float(update_dict["percentage_charge"])
        if "settlement_schedule" in update_dict:
            payload["settlement_schedule"] = update_dict["settlement_schedule"]

        # Get platform Paystack secret key from environment
        paystack_secret = os.getenv("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            raise Exception("PAYSTACK_SECRET_KEY not configured")

        # Call Paystack API
        url = f"https://api.paystack.co/subaccount/{subaccount_code}"
        headers = {
            "Authorization": f"Bearer {paystack_secret}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    error_text = await response.text()
                    raise Exception(f"Paystack API error {response.status}: {error_text}")

    async def _call_paystack_get_subaccount(self, subaccount_code: str) -> Dict[str, Any]:
        """
        Call Paystack GET /subaccount/:subaccount_code API.
        Used for manual sync operations.
        """

        # Get platform Paystack secret key from environment
        paystack_secret = os.getenv("PAYSTACK_SECRET_KEY")
        if not paystack_secret:
            raise Exception("PAYSTACK_SECRET_KEY not configured")

        # Call Paystack API
        url = f"https://api.paystack.co/subaccount/{subaccount_code}"
        headers = {
            "Authorization": f"Bearer {paystack_secret}",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    error_text = await response.text()
                    raise Exception(f"Paystack API error {response.status}: {error_text}")


    async def _enqueue_reconcile_subaccount_job(self, merchant_id: UUID, subaccount_code: str) -> None:
        """
        Enqueue a ReconcileSubaccount outbox job for background healing.
        Called when Paystack update succeeds but DB sync fails.
        """
        from ..utils.outbox import create_outbox_event
        from ..models.outbox import JobType
        from datetime import timedelta

        # Schedule job to run in 30 seconds (allow for transient DB issues to resolve)
        next_run_at = datetime.now(timezone.utc) + timedelta(seconds=30)

        payload = {
            "subaccount_code": subaccount_code,
            "reason": "db_sync_failed_after_paystack_update",
        }

        try:
            await create_outbox_event(
                db=self.db,
                merchant_id=merchant_id,
                job_type=JobType.RECONCILE_SUBACCOUNT,
                payload=payload,
                next_run_at=next_run_at,
                max_attempts=5  # Allow up to 5 retry attempts with exponential backoff
            )

            log.info(
                "Reconcile subaccount job enqueued",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": subaccount_code,
                    "next_run_at": next_run_at.isoformat(),
                    "event_type": "reconcile_subaccount_job_enqueued",
                },
            )

        except Exception as enqueue_error:
            log.error(
                "Failed to enqueue reconcile subaccount job",
                extra={
                    "merchant_id": str(merchant_id),
                    "subaccount_code": subaccount_code,
                    "error": str(enqueue_error),
                    "event_type": "reconcile_subaccount_job_enqueue_failed",
                },
            )
            # Don't re-raise - this is a best-effort background job
