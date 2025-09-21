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
    MetaCredentialsResponse,
    MetaIntegrationStatusResponse,
    MetaTokenRotateRequest,
    MetaCredentialsForWorker,
    MetaIntegrationStatus,
    MetaVerificationDetails
)
from ..utils.encryption import get_encryption_service, encrypt_key, decrypt_key
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer
from ..utils.error_handling import map_exception_to_response, create_error_response
from ..utils.circuit_breaker import CircuitBreaker
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
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=MetaIntegrationError
        )

        # Meta API configuration
        self.meta_api_version = os.getenv("META_GRAPH_API_VERSION", "v18.0")
        self.meta_base_url = os.getenv("META_GRAPH_BASE_URL", "https://graph.facebook.com")
        self.meta_timeout = int(os.getenv("META_API_TIMEOUT_SECONDS", "30"))
        self.meta_app_secret = os.getenv("META_APP_SECRET")

        # Cache configuration
        self.cache_ttl = int(os.getenv("META_CREDS_CACHE_TTL_SECONDS", "300"))
        self._status_cache: Dict[str, tuple] = {}  # {merchant_id: (response, timestamp)}

    async def store_credentials(
        self,
        merchant_id: UUID,
        request: MetaCredentialsRequest
    ) -> MetaCredentialsResponse:
        """Store and verify Meta credentials for a merchant"""
        start_time = datetime.now()

        try:
            logger.info(f"Storing Meta credentials for merchant: {merchant_id}")

            # Check if credentials are unchanged (idempotency)
            existing = await self._get_integration_by_merchant(merchant_id)
            if existing and await self._credentials_unchanged(existing, request):
                logger.info(f"Credentials unchanged for merchant {merchant_id}, returning cached status")
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
                "updated_at": datetime.utcnow()
            }

            # Upsert integration record
            stmt = insert(MetaIntegration).values(**integration_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['merchant_id'],
                set_=integration_data
            )

            result = await self.db.execute(stmt)
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            # Log metrics
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "store", "status": "success"}
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
                    "duration_ms": duration_ms
                }
            )

            return MetaCredentialsResponse(
                success=True,
                message="Meta credentials saved successfully",
                status=verification_result["status"],
                catalog_name=verification_result.get("catalog_name"),
                verification_timestamp=verification_result.get("verified_at")
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store Meta credentials for merchant {merchant_id}: {str(e)}")
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "store", "status": "error"}
            )
            raise MetaIntegrationError(f"Failed to store credentials: {str(e)}")

    async def get_integration_status(self, merchant_id: UUID) -> MetaIntegrationStatusResponse:
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
                response = MetaIntegrationStatusResponse.invalid_credentials(
                    error=integration.last_error or "Invalid credentials",
                    error_code=integration.error_code or "META_AUTH_FAILED",
                    last_error_at=integration.updated_at
                )
            else:
                # Build successful response
                verification_details = None
                if integration.status == MetaIntegrationStatus.VERIFIED:
                    verification_details = MetaVerificationDetails(
                        token_valid=True,
                        catalog_accessible=True,
                        permissions_valid=True
                    )

                response = MetaIntegrationStatusResponse(
                    status=integration.status,
                    catalog_id=integration.catalog_id,
                    catalog_name=integration.catalog_name,
                    app_id=integration.app_id,
                    waba_id=integration.waba_id,
                    last_verified_at=integration.last_verified_at,
                    verification_details=verification_details
                )

            # Cache response
            self._cache_status(str(merchant_id), response)

            return response

        except Exception as e:
            logger.error(f"Failed to get integration status for merchant {merchant_id}: {str(e)}")
            raise MetaIntegrationError(f"Failed to get status: {str(e)}")

    async def delete_integration(self, merchant_id: UUID) -> bool:
        """Delete Meta integration for a merchant"""
        try:
            logger.info(f"Deleting Meta integration for merchant: {merchant_id}")

            stmt = delete(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
            result = await self.db.execute(stmt)
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            # Log metrics
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "delete", "status": "success"}
            )

            logger.info(f"Meta integration deleted for merchant: {merchant_id}")
            return result.rowcount > 0

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete Meta integration for merchant {merchant_id}: {str(e)}")
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "delete", "status": "error"}
            )
            raise MetaIntegrationError(f"Failed to delete integration: {str(e)}")

    async def rotate_token(
        self,
        merchant_id: UUID,
        request: MetaTokenRotateRequest
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
                waba_id=integration.waba_id
            )

            # Use store_credentials which will update existing record
            response = await self.store_credentials(merchant_id, updated_request)

            logger.info(f"Meta token rotated for merchant: {merchant_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to rotate Meta token for merchant {merchant_id}: {str(e)}")
            increment_counter(
                "meta_credentials_operations_total",
                tags={"operation": "rotate", "status": "error"}
            )
            raise MetaIntegrationError(f"Failed to rotate token: {str(e)}")

    async def load_credentials_for_worker(self, merchant_id: UUID) -> Optional[MetaCredentialsForWorker]:
        """Load decrypted credentials for sync worker"""
        try:
            integration = await self._get_integration_by_merchant(merchant_id)
            if not integration:
                logger.debug(f"No Meta integration found for merchant: {merchant_id}")
                return None

            if integration.status != MetaIntegrationStatus.VERIFIED:
                logger.warning(f"Meta integration not verified for merchant: {merchant_id}")
                return None

            # Decrypt token
            decrypted_token = decrypt_key(integration.system_user_token_encrypted)

            return MetaCredentialsForWorker(
                catalog_id=integration.catalog_id,
                system_user_token=decrypted_token,
                app_id=integration.app_id,
                waba_id=integration.waba_id,
                status=integration.status,
                last_verified_at=integration.last_verified_at
            )

        except Exception as e:
            logger.error(f"Failed to load credentials for worker, merchant {merchant_id}: {str(e)}")
            return None

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def update_catalog_only(self, merchant_id: UUID, catalog_id: str) -> MetaCredentialsResponse:
        """
        Update only catalog_id, reusing WhatsApp credentials

        This method:
        1. Gets app_id and system_user_token from WhatsApp integration
        2. Updates the Meta catalog_id only
        3. Verifies the connection with existing credentials
        """
        try:
            # First, get WhatsApp credentials (app_id, system_user_token)
            whatsapp_creds = await self._get_whatsapp_credentials(merchant_id)
            if not whatsapp_creds:
                raise MetaIntegrationError(
                    "WhatsApp integration not found. Please complete WhatsApp setup first.",
                    "WHATSAPP_NOT_CONFIGURED"
                )

            # Check if we have existing Meta integration
            existing = await self._get_integration_by_merchant(merchant_id)

            # Create full request using WhatsApp credentials + new catalog_id
            full_request = MetaCredentialsRequest(
                catalog_id=catalog_id,
                system_user_token=whatsapp_creds['system_user_token'],
                app_id=whatsapp_creds['app_id'],
                waba_id=whatsapp_creds.get('waba_id')
            )

            # If catalog_id is the same and credentials unchanged, return early
            if existing and existing.catalog_id == catalog_id:
                if await self._credentials_unchanged(existing, full_request):
                    logger.info(f"Meta catalog already configured with same credentials for merchant {merchant_id}")
                    return self._build_response_from_db(existing)

            # Verify the new credentials
            verification_result = await self._verify_credentials(full_request)

            if verification_result["status"] != MetaIntegrationStatus.VERIFIED:
                raise MetaIntegrationError(
                    f"Credential verification failed: {verification_result.get('error', 'Unknown error')}",
                    verification_result.get('error_code', 'VERIFICATION_FAILED')
                )

            # Store/update the integration
            integration_data = {
                "merchant_id": merchant_id,
                "catalog_id": catalog_id,
                "system_user_token_encrypted": encrypt_key(full_request.system_user_token),
                "app_id": full_request.app_id,
                "waba_id": full_request.waba_id,
                "status": MetaIntegrationStatus.VERIFIED,
                "catalog_name": verification_result.get("catalog_name"),
                "last_verified_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if existing:
                # Update existing
                stmt = (
                    update(MetaIntegration)
                    .where(MetaIntegration.merchant_id == merchant_id)
                    .values(**integration_data)
                    .returning(MetaIntegration)
                )
            else:
                # Insert new
                integration_data["created_at"] = datetime.utcnow()
                stmt = (
                    insert(MetaIntegration)
                    .values(**integration_data)
                    .returning(MetaIntegration)
                )

            result = await self.db.execute(stmt)
            integration_row = result.first()
            await self.db.commit()

            # Clear cache
            self._clear_cache(str(merchant_id))

            logger.info(f"Meta catalog updated successfully for merchant {merchant_id}")

            return MetaCredentialsResponse(
                success=True,
                message="Meta catalog connected successfully",
                status=MetaIntegrationStatus.VERIFIED,
                catalog_name=verification_result.get("catalog_name"),
                verification_timestamp=datetime.utcnow()
            )

        except MetaIntegrationError:
            raise
        except Exception as e:
            logger.error(f"Error updating catalog for merchant {merchant_id}: {str(e)}")
            raise MetaIntegrationError(f"Failed to update catalog: {str(e)}")

    async def _get_whatsapp_credentials(self, merchant_id: UUID) -> Optional[Dict[str, str]]:
        """Get WhatsApp credentials from merchants table"""
        try:
            # Import here to avoid circular imports
            from ..models.sqlalchemy_models import Merchant

            stmt = select(Merchant).where(Merchant.id == merchant_id)
            result = await self.db.execute(stmt)
            merchant = result.scalar_one_or_none()

            if not merchant:
                return None

            # Check if WhatsApp credentials exist
            if not merchant.app_id_enc or not merchant.system_user_token_enc:
                return None

            return {
                'app_id': decrypt_key(merchant.app_id_enc),
                'system_user_token': decrypt_key(merchant.system_user_token_enc),
                'waba_id': decrypt_key(merchant.waba_id_enc) if merchant.waba_id_enc else None
            }

        except Exception as e:
            logger.error(f"Error getting WhatsApp credentials for merchant {merchant_id}: {str(e)}")
            return None

    async def _verify_credentials(self, request: MetaCredentialsRequest) -> Dict[str, Any]:
        """Verify Meta credentials with Graph API"""
        start_time = datetime.now()

        try:
            async with self.circuit_breaker:
                # Test catalog access
                url = f"{self.meta_base_url}/{self.meta_api_version}/{request.catalog_id}"
                params = {
                    "access_token": request.system_user_token,
                    "fields": "name"
                }

                async with httpx.AsyncClient(timeout=self.meta_timeout) as client:
                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        catalog_name = data.get("name", "Unknown Catalog")

                        # Log successful verification
                        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                        logger.info(
                            "Meta credentials verified",
                            extra={
                                "event": "meta_credentials_verified",
                                "catalog_id": f"***{request.catalog_id[-4:]}",
                                "verification_result": "success",
                                "catalog_name": catalog_name,
                                "duration_ms": duration_ms
                            }
                        )

                        increment_counter(
                            "meta_verification_attempts_total",
                            tags={"result": "verified"}
                        )

                        return {
                            "status": MetaIntegrationStatus.VERIFIED,
                            "catalog_name": catalog_name,
                            "verified_at": datetime.utcnow()
                        }

                    elif response.status_code == 401:
                        error_data = response.json().get("error", {})
                        error_code = str(error_data.get("code", "AUTH_FAILED"))
                        error_message = error_data.get("message", "Invalid access token")

                        logger.warning(f"Meta API authentication failed: {error_message}")
                        increment_counter(
                            "meta_verification_attempts_total",
                            tags={"result": "auth_failed"}
                        )
                        increment_counter(
                            "meta_api_errors_total",
                            tags={"error_code": error_code, "error_category": "auth"}
                        )

                        return {
                            "status": MetaIntegrationStatus.INVALID,
                            "error": error_message,
                            "error_code": f"META_{error_code}"
                        }

                    elif response.status_code == 404:
                        logger.warning(f"Meta catalog not found: {request.catalog_id}")
                        increment_counter(
                            "meta_verification_attempts_total",
                            tags={"result": "catalog_inaccessible"}
                        )

                        return {
                            "status": MetaIntegrationStatus.INVALID,
                            "error": "Catalog not found or inaccessible",
                            "error_code": "META_CATALOG_NOT_FOUND"
                        }

                    else:
                        error_message = f"HTTP {response.status_code}"
                        logger.error(f"Meta API verification failed: {error_message}")
                        increment_counter(
                            "meta_verification_attempts_total",
                            tags={"result": "error"}
                        )

                        return {
                            "status": MetaIntegrationStatus.INVALID,
                            "error": error_message,
                            "error_code": f"META_HTTP_{response.status_code}"
                        }

        except httpx.RequestError as e:
            logger.error(f"Meta API request failed: {str(e)}")
            increment_counter(
                "meta_verification_attempts_total",
                tags={"result": "error"}
            )
            increment_counter(
                "meta_api_errors_total",
                tags={"error_code": "network", "error_category": "network"}
            )

            return {
                "status": MetaIntegrationStatus.INVALID,
                "error": f"Network error: {str(e)}",
                "error_code": "META_NETWORK_ERROR"
            }

        except Exception as e:
            logger.error(f"Meta verification error: {str(e)}")
            increment_counter(
                "meta_verification_attempts_total",
                tags={"result": "error"}
            )

            return {
                "status": MetaIntegrationStatus.INVALID,
                "error": f"Verification failed: {str(e)}",
                "error_code": "META_VERIFICATION_ERROR"
            }

    async def _get_integration_by_merchant(self, merchant_id: UUID) -> Optional[MetaIntegrationDB]:
        """Get Meta integration record for merchant"""
        stmt = select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        result = await self.db.execute(stmt)
        row = result.first()

        if row:
            return MetaIntegrationDB.from_orm(row[0])
        return None

    async def _credentials_unchanged(
        self,
        existing: MetaIntegrationDB,
        request: MetaCredentialsRequest
    ) -> bool:
        """Check if credentials are unchanged (for idempotency)"""
        try:
            # Decrypt existing token to compare
            existing_token = decrypt_key(existing.system_user_token_encrypted)

            return (
                existing.catalog_id == request.catalog_id and
                existing_token == request.system_user_token and
                existing.app_id == request.app_id and
                existing.waba_id == request.waba_id
            )
        except Exception:
            # If decryption fails, assume changed
            return False

    def _build_response_from_db(self, integration: MetaIntegrationDB) -> MetaCredentialsResponse:
        """Build response from database record"""
        return MetaCredentialsResponse(
            success=True,
            message="Meta credentials already configured",
            status=integration.status,
            catalog_name=integration.catalog_name,
            verification_timestamp=integration.last_verified_at
        )

    def _get_cached_status(self, merchant_id: str) -> Optional[MetaIntegrationStatusResponse]:
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