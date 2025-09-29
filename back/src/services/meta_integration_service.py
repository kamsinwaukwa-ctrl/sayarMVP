"""
Meta Integration service for credential management and verification
Handles encrypted storage and Meta Graph API verification of credentials
"""

import httpx
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from sqlalchemy.dialects.postgresql import insert

from ..models.meta_integrations import (
    MetaIntegration,
    MetaIntegrationDB,
    MetaCredentialsRequest,
    MetaWhatsAppCredentialsRequest,
    MetaCredentialsResponse,
    MetaIntegrationStatusResponse,
    MetaTokenRotateRequest,
    MetaCredentialsForWorker,
    MetaIntegrationStatus,
    MetaVerificationDetails,
)
from ..utils.encryption import get_encryption_service, encrypt_key, decrypt_key
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer
from ..utils.error_handling import map_exception_to_response, create_error_response
from ..utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..utils.retry import retryable, RetryConfig

logger = get_logger(__name__)


class MetaIntegrationError(Exception):
    """Meta integration specific error"""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class MetaIntegrationService:
    """Service class for Meta integration credential management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption_service = get_encryption_service()
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0
        )
        self.circuit_breaker = CircuitBreaker("meta_integration", config)

        # Meta API configuration
        self.meta_api_version = os.getenv("META_GRAPH_API_VERSION", "v18.0")
        self.meta_base_url = os.getenv(
            "META_GRAPH_BASE_URL", "https://graph.facebook.com"
        )
        self.meta_timeout = int(os.getenv("META_API_TIMEOUT_SECONDS", "30"))
        self.meta_app_secret = os.getenv("META_APP_SECRET")

        # Cache configuration
        self.cache_ttl = int(os.getenv("META_CREDS_CACHE_TTL_SECONDS", "300"))
        self._status_cache: Dict[str, tuple] = (
            {}
        )  # {merchant_id: (response, timestamp)}

    async def store_credentials(
        self, merchant_id: UUID, request: MetaCredentialsRequest
    ) -> MetaCredentialsResponse:
        """Store and verify Meta credentials for a merchant"""
        start_time = datetime.now()

        try:
            logger.info(f"Storing Meta credentials for merchant: {merchant_id}")

            # Check if credentials are unchanged (idempotency)
            existing = await self._get_integration_by_merchant(merchant_id)
            if existing and await self._credentials_unchanged(existing, request):
                logger.info(
                    f"Credentials unchanged for merchant {merchant_id}, returning cached status"
                )
                return self._build_response_from_db(existing)

            # Encrypt the system user token
            encrypted_token = encrypt_key(request.system_user_token)

            # Verify credentials with Meta API
            verification_result = await self._verify_credentials(request)

            # Prepare data for database
            integration_data = {
                "merchant_id": merchant_id,
                "catalog_id": request.catalog_id,
                "system_user_token_encrypted": encrypted_token.encrypted_data,
                "app_id": request.app_id,
                "waba_id": request.waba_id,
                "status": verification_result["status"],
                "catalog_name": verification_result.get("catalog_name"),
                "last_verified_at": verification_result.get("verified_at"),
                "last_error": verification_result.get("error"),
                "error_code": verification_result.get("error_code"),
                "updated_at": datetime.utcnow(),
            }

            # Upsert integration record
            stmt = insert(MetaIntegration).values(**integration_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["merchant_id"], set_=integration_data
            )

            result = await self.db.execute(stmt)
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            # Log metrics
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "store", "status": "success"},
            )
            record_timer("meta_verification_duration_seconds", duration_ms / 1000.0)

            # Log structured event
            logger.info(
                "Meta credentials stored",
                extra={
                    "event": "meta_credentials_stored",
                    "merchant_id": str(merchant_id),
                    "catalog_id": f"***{request.catalog_id[-4:]}",
                    "app_id": f"***{request.app_id[-4:]}",
                    "verification_status": verification_result["status"],
                    "duration_ms": duration_ms,
                },
            )

            return MetaCredentialsResponse(
                success=True,
                message="Meta credentials saved successfully",
                status=verification_result["status"],
                catalog_name=verification_result.get("catalog_name"),
                verification_timestamp=verification_result.get("verified_at"),
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to store Meta credentials for merchant {merchant_id}: {str(e)}"
            )
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "store", "status": "error"},
            )
            raise MetaIntegrationError(f"Failed to store credentials: {str(e)}")

    async def get_integration_status(
        self, merchant_id: UUID
    ) -> MetaIntegrationStatusResponse:
        """Get Meta integration status for a merchant"""
        try:
            # Check cache first
            cached_response = self._get_cached_status(str(merchant_id))
            if cached_response:
                return cached_response

            integration = await self._get_integration_by_merchant(merchant_id)
            if not integration:
                response = MetaIntegrationStatusResponse.not_configured()
            elif integration.status == MetaIntegrationStatus.INVALID:
                user_friendly_error = self._get_user_friendly_error(
                    integration.last_error or "Invalid credentials",
                    integration.error_code or "META_AUTH_FAILED"
                )
                response = MetaIntegrationStatusResponse(
                    status=MetaIntegrationStatus.INVALID,
                    catalog_id=integration.catalog_id,
                    catalog_name=integration.catalog_name,
                    app_id=integration.app_id,
                    waba_id=integration.waba_id,
                    last_verified_at=integration.last_verified_at,
                    error=integration.last_error or "Invalid credentials",
                    error_code=integration.error_code or "META_AUTH_FAILED",
                    last_error_at=integration.updated_at,
                    message=user_friendly_error,
                )
            else:
                # Build successful response
                verification_details = None
                if integration.status == MetaIntegrationStatus.VERIFIED:
                    verification_details = MetaVerificationDetails(
                        token_valid=True,
                        catalog_accessible=True,
                        permissions_valid=True,
                    )

                response = MetaIntegrationStatusResponse(
                    status=integration.status,
                    catalog_id=integration.catalog_id,
                    catalog_name=integration.catalog_name,
                    app_id=integration.app_id,
                    waba_id=integration.waba_id,
                    last_verified_at=integration.last_verified_at,
                    verification_details=verification_details,
                )

            # Cache response
            self._cache_status(str(merchant_id), response)

            return response

        except Exception as e:
            logger.error(
                f"Failed to get integration status for merchant {merchant_id}: {str(e)}"
            )
            raise MetaIntegrationError(f"Failed to get status: {str(e)}")

    async def verify_existing_integration(
        self, merchant_id: UUID
    ) -> MetaIntegrationStatusResponse:
        """Verify existing Meta integration credentials without making changes to stored config"""
        try:
            logger.info(f"Verifying existing Meta integration for merchant: {merchant_id}")

            # Get existing integration
            integration = await self._get_integration_by_merchant(merchant_id)
            if not integration:
                raise MetaIntegrationError("No integration found to verify")

            # Check if we have the minimum required data to verify
            if not integration.catalog_id or not integration.system_user_token_encrypted:
                raise MetaIntegrationError("Missing required credentials for verification")

            # Decrypt token for verification
            from ..utils.encryption import decrypt_key
            decrypted_token = decrypt_key(integration.system_user_token_encrypted)

            # Create temporary credentials request for verification
            temp_request = MetaCredentialsRequest(
                catalog_id=integration.catalog_id,
                system_user_token=decrypted_token,
                app_id=integration.app_id or "placeholder",
                waba_id=integration.waba_id,
            )

            # Verify credentials with Meta API
            verification_result = await self._verify_credentials(temp_request)

            # Update only verification-related fields in the database
            from ..models.meta_integrations import MetaIntegration
            from sqlalchemy import update
            from datetime import datetime

            stmt = (
                update(MetaIntegration)
                .where(MetaIntegration.merchant_id == merchant_id)
                .values(
                    status=verification_result["status"],
                    catalog_name=verification_result.get("catalog_name"),
                    last_verified_at=verification_result.get("verified_at"),
                    last_error=verification_result.get("error"),
                    error_code=verification_result.get("error_code"),
                    updated_at=datetime.utcnow(),
                )
                .returning(MetaIntegration)
            )

            result = await self.db.execute(stmt)
            updated_integration = result.scalar_one()
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            # Build response with all stored data
            verification_details = None
            if updated_integration.status == MetaIntegrationStatus.VERIFIED:
                verification_details = MetaVerificationDetails(
                    token_valid=True,
                    catalog_accessible=True,
                    permissions_valid=True,
                )

            # Add user-friendly message for invalid status
            user_friendly_message = None
            if updated_integration.status == MetaIntegrationStatus.INVALID:
                user_friendly_message = self._get_user_friendly_error(
                    updated_integration.last_error,
                    updated_integration.error_code
                )

            response = MetaIntegrationStatusResponse(
                status=updated_integration.status,
                catalog_id=updated_integration.catalog_id,
                catalog_name=updated_integration.catalog_name,
                app_id=updated_integration.app_id,
                waba_id=updated_integration.waba_id,
                last_verified_at=updated_integration.last_verified_at,
                verification_details=verification_details,
                error=updated_integration.last_error,
                error_code=updated_integration.error_code,
                last_error_at=updated_integration.updated_at if updated_integration.last_error else None,
                message=user_friendly_message,
            )

            logger.info(f"Verification completed for merchant {merchant_id}, status: {updated_integration.status}")
            return response

        except MetaIntegrationError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to verify integration for merchant {merchant_id}: {str(e)}")
            raise MetaIntegrationError(f"Failed to verify integration: {str(e)}")

    async def delete_integration(self, merchant_id: UUID) -> bool:
        """Delete Meta integration for a merchant"""
        try:
            logger.info(f"Deleting Meta integration for merchant: {merchant_id}")

            stmt = delete(MetaIntegration).where(
                MetaIntegration.merchant_id == merchant_id
            )
            result = await self.db.execute(stmt)
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            # Log metrics
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "delete", "status": "success"},
            )

            logger.info(f"Meta integration deleted for merchant: {merchant_id}")
            return result.rowcount > 0

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to delete Meta integration for merchant {merchant_id}: {str(e)}"
            )
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "delete", "status": "error"},
            )
            raise MetaIntegrationError(f"Failed to delete integration: {str(e)}")

    async def rotate_token(
        self, merchant_id: UUID, request: MetaTokenRotateRequest
    ) -> MetaCredentialsResponse:
        """Rotate system user token for existing integration"""
        try:
            logger.info(f"Rotating Meta token for merchant: {merchant_id}")

            # Get existing integration
            integration = await self._get_integration_by_merchant(merchant_id)
            if not integration:
                raise MetaIntegrationError("No existing Meta integration found")

            # Create updated credentials request
            updated_request = MetaCredentialsRequest(
                catalog_id=integration.catalog_id,
                system_user_token=request.system_user_token,
                app_id=integration.app_id,
                waba_id=integration.waba_id,
            )

            # Use store_credentials which will update existing record
            response = await self.store_credentials(merchant_id, updated_request)

            logger.info(f"Meta token rotated for merchant: {merchant_id}")
            return response

        except Exception as e:
            logger.error(
                f"Failed to rotate Meta token for merchant {merchant_id}: {str(e)}"
            )
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "rotate", "status": "error"},
            )
            raise MetaIntegrationError(f"Failed to rotate token: {str(e)}")

    async def load_credentials_for_worker(
        self, merchant_id: UUID
    ) -> Optional[MetaCredentialsForWorker]:
        """Load decrypted credentials for sync worker"""
        try:
            integration = await self._get_integration_by_merchant(merchant_id)
            if not integration:
                logger.debug(f"No Meta integration found for merchant: {merchant_id}")
                return None

            if integration.status != MetaIntegrationStatus.VERIFIED:
                logger.warning(
                    f"Meta integration not verified for merchant: {merchant_id}"
                )
                return None

            # Decrypt token
            decrypted_token = decrypt_key(integration.system_user_token_encrypted)

            return MetaCredentialsForWorker(
                catalog_id=integration.catalog_id,
                system_user_token=decrypted_token,
                app_id=integration.app_id,
                waba_id=integration.waba_id,
                status=integration.status,
                last_verified_at=integration.last_verified_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to load credentials for worker, merchant {merchant_id}: {str(e)}"
            )
            return None

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def update_catalog_only(
        self, merchant_id: UUID, catalog_id: str
    ) -> MetaCredentialsResponse:
        """
        Update only catalog_id without requiring WhatsApp credentials

        This method:
        1. Validates catalog_id format
        2. Updates or creates Meta integration record with catalog_id only
        3. Does NOT verify credentials (can be done later via separate endpoint)
        """
        logger.info(f"Starting catalog-only update for merchant {merchant_id} with catalog_id: {catalog_id}")

        try:
            # Step 1: Validate catalog_id format
            if not catalog_id or not catalog_id.strip():
                raise MetaIntegrationError(
                    "Catalog ID cannot be empty",
                    "INVALID_CATALOG_ID"
                )

            catalog_id = catalog_id.strip()
            if not catalog_id.isdigit():
                raise MetaIntegrationError(
                    "Catalog ID must be numeric",
                    "INVALID_CATALOG_ID"
                )

            logger.info(f"Catalog ID validation passed for merchant {merchant_id}")

            # Step 2: Upsert Meta integration with catalog_id only
            logger.info(f"Upserting Meta integration for merchant {merchant_id}")
            integration = await self._upsert_meta_integration_minimal(merchant_id, catalog_id)

            logger.info(f"Catalog-only update completed successfully for merchant {merchant_id}")

            # Step 3: Return response
            return MetaCredentialsResponse(
                catalog_id=catalog_id,
                status=MetaIntegrationStatus.CATALOG_SAVED,
                message="Catalog ID saved successfully. Credentials verification can be done separately.",
                verification_date=None,
                merchant_id=str(merchant_id)
            )

        except MetaIntegrationError:
            # Re-raise MetaIntegrationError as-is (these have specific error codes and messages)
            raise
        except Exception as e:
            # Catch any unexpected errors and wrap them
            logger.error(f"Unexpected error updating catalog for merchant {merchant_id}: {str(e)}", exc_info=True)
            await self.db.rollback()  # Ensure rollback on unexpected errors
            raise MetaIntegrationError(
                f"An unexpected error occurred while updating the catalog. Please try again.",
                "UNEXPECTED_ERROR"
            )

    async def _upsert_meta_integration_minimal(
        self, merchant_id: UUID, catalog_id: str
    ):
        """
        Upsert Meta integration with catalog_id only (no credentials)
        Uses COALESCE pattern to avoid overwriting existing data with NULL
        """
        from ..models.meta_integrations import MetaIntegration
        from sqlalchemy import insert, update, select
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from datetime import datetime

        try:
            logger.info(f"Upserting catalog_id for merchant {merchant_id}")

            integration_data = {
                "merchant_id": merchant_id,
                "catalog_id": catalog_id,
                "status": MetaIntegrationStatus.CATALOG_SAVED,  # Custom status for catalog-only
                "updated_at": datetime.utcnow(),
                "last_error": None,
                "error_code": None,
                "created_at": datetime.utcnow(),  # Will be ignored on conflict
            }

            # Use PostgreSQL UPSERT with COALESCE to preserve existing values
            stmt = pg_insert(MetaIntegration).values(**integration_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["merchant_id"],
                set_={
                    # Only update catalog_id, status, timestamps, and error fields
                    # Preserve existing system_user_token_encrypted, app_id, waba_id
                    "catalog_id": stmt.excluded.catalog_id,
                    "status": stmt.excluded.status,
                    "updated_at": stmt.excluded.updated_at,
                    "last_error": stmt.excluded.last_error,
                    "error_code": stmt.excluded.error_code,
                    # Do NOT update: system_user_token_encrypted, app_id, waba_id
                    # These are preserved from existing record
                }
            ).returning(MetaIntegration)

            result = await self.db.execute(stmt)
            integration = result.scalar_one()
            await self.db.commit()

            logger.info(f"Successfully upserted catalog_id for merchant {merchant_id}")
            return integration

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to upsert minimal Meta integration for merchant {merchant_id}: {str(e)}")
            raise

    async def update_whatsapp_credentials(
        self, merchant_id: UUID, request: "MetaWhatsAppCredentialsRequest"
    ) -> "MetaCredentialsResponse":
        """
        Update only WhatsApp credentials, preserving existing catalog_id.

        This method:
        1. Gets the existing integration to preserve catalog_id
        2. Updates only WhatsApp-related fields
        3. Re-verifies credentials with Meta API
        """
        try:
            # Import here to avoid circular imports
            from ..utils.encryption import encrypt_key
            from datetime import datetime

            logger.info(f"Updating WhatsApp credentials for merchant {merchant_id}")

            # Get existing integration to preserve catalog_id
            existing = await self._get_integration_by_merchant(merchant_id)
            if not existing:
                raise MetaIntegrationError(
                    "Meta integration not found. Please set up Meta Catalog first.",
                    "INTEGRATION_NOT_FOUND"
                )

            if not existing.catalog_id:
                raise MetaIntegrationError(
                    "No catalog_id found. Please set up Meta Catalog first.",
                    "CATALOG_NOT_CONFIGURED"
                )

            # Check if credentials are unchanged (idempotency)
            if await self._whatsapp_credentials_unchanged(existing, request):
                logger.info(
                    f"WhatsApp credentials unchanged for merchant {merchant_id}, returning cached status"
                )
                return self._build_response_from_db(existing)

            # Encrypt the system user token
            encrypted_token = encrypt_key(request.system_user_token)

            # Create a temporary full credentials object for verification
            from ..models.meta_integrations import MetaCredentialsRequest
            full_request = MetaCredentialsRequest(
                catalog_id=existing.catalog_id,  # Preserve existing catalog_id
                system_user_token=request.system_user_token,
                app_id=request.app_id,
                waba_id=request.waba_id,
            )

            # Verify credentials with Meta API
            verification_result = await self._verify_credentials(full_request)

            # Update only WhatsApp-related fields in the database
            from ..models.meta_integrations import MetaIntegration

            stmt = (
                update(MetaIntegration)
                .where(MetaIntegration.merchant_id == merchant_id)
                .values(
                    # Update WhatsApp fields only
                    system_user_token_encrypted=encrypted_token.encrypted_data,
                    app_id=request.app_id,
                    waba_id=request.waba_id,
                    phone_number_id=request.phone_number_id,
                    whatsapp_phone_e164=request.whatsapp_phone_e164,
                    # Update verification status
                    status=verification_result["status"],
                    last_verified_at=verification_result.get("verified_at"),
                    last_error=verification_result.get("error"),
                    error_code=verification_result.get("error_code"),
                    updated_at=datetime.utcnow(),
                    # Preserve catalog_id and catalog_name - don't touch them
                )
                .returning(MetaIntegration)
            )

            result = await self.db.execute(stmt)
            integration = result.scalar_one()
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            logger.info(f"Successfully updated WhatsApp credentials for merchant {merchant_id}")

            return MetaCredentialsResponse(
                success=True,
                message="WhatsApp credentials updated successfully",
                status=integration.status,
                catalog_name=integration.catalog_name,
                verification_timestamp=integration.last_verified_at,
                merchant_id=str(merchant_id),
            )

        except MetaIntegrationError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update WhatsApp credentials for merchant {merchant_id}: {str(e)}")
            raise MetaIntegrationError(
                f"Failed to update WhatsApp credentials: {str(e)}",
                "WHATSAPP_UPDATE_FAILED"
            )

    async def _whatsapp_credentials_unchanged(
        self, existing: "MetaIntegrationDB", request: "MetaWhatsAppCredentialsRequest"
    ) -> bool:
        """Check if WhatsApp credentials are unchanged for idempotency"""
        try:
            from ..utils.encryption import decrypt_key

            # Check if token is the same
            if existing.system_user_token_encrypted:
                existing_token = decrypt_key(existing.system_user_token_encrypted)
                if existing_token != request.system_user_token:
                    return False

            # Check other fields
            return (
                existing.app_id == request.app_id
                and existing.waba_id == request.waba_id
                and existing.phone_number_id == request.phone_number_id
                and existing.whatsapp_phone_e164 == request.whatsapp_phone_e164
            )
        except Exception:
            # If we can't compare, assume they're different
            return False

    async def _get_whatsapp_credentials(
        self, merchant_id: UUID
    ) -> Optional[Dict[str, str]]:
        """Get WhatsApp credentials from meta_integrations table"""
        try:
            logger.debug(f"Retrieving WhatsApp credentials from database for merchant {merchant_id}")

            # Get credentials from meta_integrations table
            integration = await self._get_integration_by_merchant(merchant_id)

            if not integration:
                logger.warning(f"Meta integration not found for merchant {merchant_id}")
                return None

            # Check if required WhatsApp credential fields exist
            if not integration.app_id:
                logger.warning(f"Missing app_id for merchant {merchant_id}")
                return None

            if not integration.system_user_token_encrypted:
                logger.warning(f"Missing system_user_token_encrypted for merchant {merchant_id}")
                return None

            # Decrypt credentials safely
            try:
                app_id = integration.app_id  # Already decrypted/unencrypted
                if not app_id or not app_id.strip():
                    logger.warning(f"App_id is empty for merchant {merchant_id}")
                    return None
            except Exception as e:
                logger.error(f"Failed to get app_id for merchant {merchant_id}: {str(e)}")
                return None

            try:
                system_user_token = decrypt_key(integration.system_user_token_encrypted)
                if not system_user_token or not system_user_token.strip():
                    logger.warning(f"Decrypted system_user_token is empty for merchant {merchant_id}")
                    return None
            except Exception as e:
                logger.error(f"Failed to decrypt system_user_token for merchant {merchant_id}: {str(e)}")
                return None

            # Handle optional waba_id
            waba_id = integration.waba_id  # Already unencrypted
            if waba_id:
                try:
                    # waba_id is already decrypted, no need to decrypt
                    pass
                except Exception as e:
                    logger.warning(f"Failed to decrypt waba_id for merchant {merchant_id}: {str(e)}")
                    # Don't fail for optional field

            logger.debug(f"Successfully retrieved and decrypted WhatsApp credentials for merchant {merchant_id}")

            return {
                "app_id": app_id,
                "system_user_token": system_user_token,
                "waba_id": waba_id,
            }

        except Exception as e:
            logger.error(
                f"Unexpected error getting WhatsApp credentials for merchant {merchant_id}: {str(e)}",
                exc_info=True
            )
            return None

    async def _verify_credentials(
        self, request: MetaCredentialsRequest
    ) -> Dict[str, Any]:
        """Verify Meta credentials with Graph API"""
        start_time = datetime.now()

        try:
            async with self.circuit_breaker.guard_async():
                # Test catalog access
                url = (
                    f"{self.meta_base_url}/{self.meta_api_version}/{request.catalog_id}"
                )
                params = {"access_token": request.system_user_token, "fields": "name"}

                async with httpx.AsyncClient(timeout=self.meta_timeout) as client:
                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        catalog_name = data.get("name", "Unknown Catalog")

                        # Log successful verification
                        duration_ms = int(
                            (datetime.now() - start_time).total_seconds() * 1000
                        )
                        logger.info(
                            "Meta credentials verified",
                            extra={
                                "event": "meta_credentials_verified",
                                "catalog_id": f"***{request.catalog_id[-4:]}",
                                "verification_result": "success",
                                "catalog_name": catalog_name,
                                "duration_ms": duration_ms,
                            },
                        )

                        increment_counter(
                            "meta_verification_success", "meta_integrations"
                        )

                        return {
                            "status": MetaIntegrationStatus.VERIFIED,
                            "catalog_name": catalog_name,
                            "verified_at": datetime.utcnow(),
                        }

                    elif response.status_code == 401:
                        error_data = response.json().get("error", {})
                        error_code = str(error_data.get("code", "AUTH_FAILED"))
                        error_message = error_data.get(
                            "message", "Invalid access token"
                        )

                        logger.warning(
                            f"Meta API authentication failed: {error_message}"
                        )
                        increment_counter(
                            "meta_verification_auth_failed", "meta_integrations"
                        )
                        increment_counter(
                            "meta_api_auth_error", "meta_integrations"
                        )

                        return {
                            "status": MetaIntegrationStatus.INVALID,
                            "error": error_message,
                            "error_code": f"META_{error_code}",
                        }

                    elif response.status_code == 404:
                        logger.warning(f"Meta catalog not found: {request.catalog_id}")
                        increment_counter(
                            "meta_verification_catalog_not_found", "meta_integrations"
                        )

                        return {
                            "status": MetaIntegrationStatus.INVALID,
                            "error": "Catalog not found or inaccessible",
                            "error_code": "META_CATALOG_NOT_FOUND",
                        }

                    else:
                        error_message = f"HTTP {response.status_code}"
                        logger.error(f"Meta API verification failed: {error_message}")
                        increment_counter(
                            "meta_verification_error", "meta_integrations"
                        )

                        return {
                            "status": MetaIntegrationStatus.INVALID,
                            "error": error_message,
                            "error_code": f"META_HTTP_{response.status_code}",
                        }

        except httpx.RequestError as e:
            logger.error(f"Meta API request failed: {str(e)}")
            increment_counter(
                "meta_verification_request_error", "meta_integrations"
            )
            increment_counter(
                "meta_api_network_error", "meta_integrations"
            )

            return {
                "status": MetaIntegrationStatus.INVALID,
                "error": f"Network error: {str(e)}",
                "error_code": "META_NETWORK_ERROR",
            }

        except Exception as e:
            logger.error(f"Meta verification error: {str(e)}")
            increment_counter(
                "meta_verification_exception", "meta_integrations"
            )

            return {
                "status": MetaIntegrationStatus.INVALID,
                "error": f"Verification failed: {str(e)}",
                "error_code": "META_VERIFICATION_ERROR",
            }

    async def _get_integration_by_merchant(
        self, merchant_id: UUID
    ) -> Optional[MetaIntegrationDB]:
        """Get Meta integration record for merchant"""
        stmt = select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        result = await self.db.execute(stmt)
        row = result.first()

        if row:
            return MetaIntegrationDB.from_orm(row[0])
        return None

    async def _credentials_unchanged(
        self, existing: MetaIntegrationDB, request: MetaCredentialsRequest
    ) -> bool:
        """Check if credentials are unchanged (for idempotency)"""
        try:
            # Decrypt existing token to compare
            existing_token = decrypt_key(existing.system_user_token_encrypted)

            return (
                existing.catalog_id == request.catalog_id
                and existing_token == request.system_user_token
                and existing.app_id == request.app_id
                and existing.waba_id == request.waba_id
            )
        except Exception:
            # If decryption fails, assume changed
            return False

    def _build_response_from_db(
        self, integration: MetaIntegrationDB
    ) -> MetaCredentialsResponse:
        """Build response from database record"""
        return MetaCredentialsResponse(
            success=True,
            message="Meta credentials already configured",
            status=integration.status,
            catalog_name=integration.catalog_name,
            verification_timestamp=integration.last_verified_at,
        )

    def _get_cached_status(
        self, merchant_id: str
    ) -> Optional[MetaIntegrationStatusResponse]:
        """Get cached status response"""
        if merchant_id in self._status_cache:
            response, timestamp = self._status_cache[merchant_id]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return response
            else:
                # Expired, remove from cache
                del self._status_cache[merchant_id]
        return None

    def _cache_status(self, merchant_id: str, response: MetaIntegrationStatusResponse):
        """Cache status response"""
        self._status_cache[merchant_id] = (response, datetime.now())

    def _clear_cache(self, merchant_id: str):
        """Clear cached status for merchant"""
        if merchant_id in self._status_cache:
            del self._status_cache[merchant_id]

    def _get_user_friendly_error(self, error: str, error_code: str) -> str:
        """Convert technical errors to user-friendly messages"""
        if not error:
            return "Please re-enter and verify your catalog ID again"

        # Check error codes first (more specific)
        if error_code:
            if "META_HTTP_400" in error_code or "META_HTTP_404" in error_code:
                return "Please re-enter and verify your catalog ID again"
            elif "META_HTTP_401" in error_code or "AUTH_FAILED" in error_code:
                return "Please check your access permissions and verify again"
            elif "NETWORK_ERROR" in error_code:
                return "Connection issue - please try verifying again"

        # Check error messages (fallback)
        error_lower = error.lower()
        if any(keyword in error_lower for keyword in ["400", "404", "not found", "catalog"]):
            return "Please re-enter and verify your catalog ID again"
        elif any(keyword in error_lower for keyword in ["401", "unauthorized", "access", "token", "permission"]):
            return "Please check your access permissions and verify again"
        elif any(keyword in error_lower for keyword in ["network", "connection", "timeout", "request"]):
            return "Connection issue - please try verifying again"

        # Default fallback
        return "Please re-enter and verify your catalog ID again"
