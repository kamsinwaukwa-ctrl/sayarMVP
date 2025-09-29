"""
WhatsApp Credentials Service for secure credential verification and encrypted storage
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
import asyncio

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models.sqlalchemy_models import Merchant
from ..models.api import (
    WhatsAppCredentialsRequest,
    WhatsAppStatusResponse,
    WhatsAppVerifyResponse,
    WAEnvironment,
    WAConnectionStatus,
)
from ..models.errors import APIError, ErrorCode
from ..utils.encryption import get_encryption_service
from ..utils.logger import get_logger
from ..utils.retry import retryable, RetryConfig

logger = get_logger(__name__)


class WhatsAppCredentialsService:
    """Service for managing WhatsApp Business API credentials"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph_api_version = os.getenv("META_GRAPH_API_VERSION", "v18.0")
        self.graph_api_base_url = f"https://graph.facebook.com/{self.graph_api_version}"

    async def save_credentials(
        self, merchant_id: UUID, request: WhatsAppCredentialsRequest
    ) -> WhatsAppStatusResponse:
        """
        Save and encrypt WhatsApp credentials for a merchant

        Args:
            merchant_id: The merchant's UUID
            request: WhatsApp credentials to save

        Returns:
            WhatsAppStatusResponse with current status

        Raises:
            APIError: If merchant not found or encryption fails
        """
        logger.info(
            "Saving WhatsApp credentials",
            extra={
                "event": "whatsapp_credentials_save_started",
                "merchant_id": str(merchant_id),
                "environment": request.environment.value,
            },
        )

        # Get merchant
        result = await self.db.execute(
            select(Merchant).where(Merchant.id == merchant_id)
        )
        merchant = result.scalar_one_or_none()

        if not merchant:
            raise APIError(
                code=ErrorCode.MERCHANT_NOT_FOUND,
                message="Merchant not found",
                details={"merchant_id": str(merchant_id)},
            )

        try:
            # Encrypt credentials
            encryption_service = get_encryption_service()
            waba_id_enc = encryption_service.encrypt_data(
                request.waba_id
            ).encrypted_data
            phone_number_id_enc = encryption_service.encrypt_data(
                request.phone_number_id
            ).encrypted_data
            app_id_enc = encryption_service.encrypt_data(request.app_id).encrypted_data
            system_user_token_enc = encryption_service.encrypt_data(
                request.system_user_token
            ).encrypted_data

            # Update merchant with encrypted credentials
            await self.db.execute(
                update(Merchant)
                .where(Merchant.id == merchant_id)
                .values(
                    waba_id_enc=waba_id_enc,
                    phone_number_id_enc=phone_number_id_enc,
                    app_id_enc=app_id_enc,
                    system_user_token_enc=system_user_token_enc,
                    wa_environment=request.environment.value,
                    wa_connection_status="not_connected",
                    wa_verified_at=None,
                    wa_last_error=None,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.db.commit()

            logger.info(
                "WhatsApp credentials saved successfully",
                extra={
                    "event": "whatsapp_credentials_saved",
                    "merchant_id": str(merchant_id),
                    "environment": request.environment.value,
                },
            )

            return WhatsAppStatusResponse(
                connection_status=WAConnectionStatus.NOT_CONNECTED,
                environment=request.environment,
                phone_number_id=self._mask_phone_number_id(request.phone_number_id),
                verified_at=None,
                last_error=None,
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to save WhatsApp credentials",
                extra={
                    "event": "whatsapp_credentials_save_failed",
                    "merchant_id": str(merchant_id),
                    "error": str(e),
                },
            )
            raise APIError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to save credentials",
                details={"error": str(e)},
            )

    async def verify_connection(self, merchant_id: UUID) -> WhatsAppVerifyResponse:
        """
        Verify WhatsApp credentials by making Graph API call

        Args:
            merchant_id: The merchant's UUID

        Returns:
            WhatsAppVerifyResponse with verification results

        Raises:
            APIError: If credentials not found or verification fails
        """
        logger.info(
            "Starting WhatsApp verification",
            extra={
                "event": "whatsapp_verification_started",
                "merchant_id": str(merchant_id),
            },
        )

        # Get WhatsApp integration from meta_integrations table
        from ..models.meta_integrations import MetaIntegration

        result = await self.db.execute(
            select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise APIError(
                code=ErrorCode.WHATSAPP_CREDENTIALS_NOT_FOUND,
                message="WhatsApp integration not configured",
            )

        if not integration.system_user_token_encrypted:
            raise APIError(
                code=ErrorCode.WHATSAPP_CREDENTIALS_NOT_FOUND,
                message="WhatsApp system user token not configured",
            )

        try:
            # Decrypt system user token
            encryption_service = get_encryption_service()
            system_user_token = encryption_service.decrypt_data(
                integration.system_user_token_encrypted
            )

            # Use phone_number_id directly (not encrypted in meta_integrations)
            phone_number_id = integration.phone_number_id

            if not phone_number_id:
                raise APIError(
                    code=ErrorCode.WHATSAPP_CREDENTIALS_NOT_FOUND,
                    message="Phone number ID not configured",
                )

            # Call Graph API to verify
            verification_result = await self._call_graph_api(
                phone_number_id, system_user_token
            )

            # Determine connection status (default to test for now)
            connection_status = WAConnectionStatus.VERIFIED_TEST

            # Update verification status in meta_integrations table
            await self.db.execute(
                update(MetaIntegration)
                .where(MetaIntegration.merchant_id == merchant_id)
                .values(
                    status="verified",
                    last_verified_at=datetime.utcnow(),
                    last_error=None,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.db.commit()

            logger.info(
                "WhatsApp verification successful",
                extra={
                    "event": "whatsapp_verification_success",
                    "merchant_id": str(merchant_id),
                    "business_name": verification_result.get("verified_name"),
                },
            )

            return WhatsAppVerifyResponse(
                connection_status=connection_status,
                environment=WAEnvironment.TEST,  # Default to test for now
                phone_number_id=self._mask_phone_number_id(phone_number_id),
                verified_at=datetime.utcnow(),
                last_error=None,
                phone_number_display=verification_result.get("display_phone_number"),
                business_name=verification_result.get("verified_name"),
            )

        except APIError:
            # Re-raise API errors (already logged in _call_graph_api)
            raise
        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"

            # Update error status in meta_integrations table
            await self.db.execute(
                update(MetaIntegration)
                .where(MetaIntegration.merchant_id == merchant_id)
                .values(
                    status="invalid",
                    last_error=error_msg,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.db.commit()

            logger.error(
                "WhatsApp verification failed",
                extra={
                    "event": "whatsapp_verification_failed",
                    "merchant_id": str(merchant_id),
                    "error": str(e),
                },
            )

            raise APIError(
                code=ErrorCode.WHATSAPP_VERIFICATION_FAILED,
                message="WhatsApp verification failed",
                details={"error": str(e)},
            )

    async def get_status(self, merchant_id: UUID) -> WhatsAppStatusResponse:
        """
        Get current WhatsApp connection status for merchant

        Args:
            merchant_id: The merchant's UUID

        Returns:
            WhatsAppStatusResponse with current status

        Raises:
            APIError: If merchant not found
        """
        # Import here to avoid circular imports
        from ..models.meta_integrations import MetaIntegration
        from ..models.sqlalchemy_models import WebhookEndpoint

        result = await self.db.execute(
            select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        )
        integration = result.scalar_one_or_none()

        # Get webhook configuration if exists
        webhook_result = await self.db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.merchant_id == merchant_id,
                WebhookEndpoint.provider == "whatsapp",
                WebhookEndpoint.active == True
            )
        )
        webhook = webhook_result.scalar_one_or_none()

        if not integration:
            # Return default status if no integration exists
            webhook_url = None
            if webhook:
                # Generate webhook URL even if no integration (webhook might be pre-configured)
                railway_url = os.getenv("RAILWAY_STATIC_URL", "http://localhost:8000")
                if not railway_url.startswith("http"):
                    railway_url = f"https://{railway_url}"
                webhook_url = f"{railway_url}{webhook.callback_path}"

            return WhatsAppStatusResponse(
                connection_status=WAConnectionStatus.NOT_CONNECTED,
                environment=WAEnvironment.TEST,
                app_id_masked=None,
                waba_id_masked=None,
                phone_number_id_masked=None,
                whatsapp_phone_e164=None,
                verified_at=None,
                last_error=None,
                token_last_updated=None,
                webhook_url=webhook_url,
                last_webhook_at=webhook.last_webhook_at if webhook else None,
            )

        # Mask phone number ID if available (don't decrypt, just mask the stored value)
        phone_number_id_masked = None
        if integration.phone_number_id:
            phone_number_id_masked = self._mask_phone_number_id(integration.phone_number_id)

        # Determine connection status based on integration status
        connection_status = WAConnectionStatus.NOT_CONNECTED
        if integration.status == "verified":
            connection_status = WAConnectionStatus.VERIFIED_TEST  # Default to test environment
        elif integration.status == "invalid":
            connection_status = WAConnectionStatus.NOT_CONNECTED  # Treat invalid as not connected

        # Generate webhook URL if webhook configured
        webhook_url = None
        last_webhook_at = None
        if webhook:
            railway_url = os.getenv("RAILWAY_STATIC_URL", "http://localhost:8000")
            if not railway_url.startswith("http"):
                railway_url = f"https://{railway_url}"
            webhook_url = f"{railway_url}{webhook.callback_path}"
            last_webhook_at = webhook.last_webhook_at

        return WhatsAppStatusResponse(
            connection_status=connection_status,
            environment=WAEnvironment.TEST,  # Default to test for now
            app_id_masked=self._mask_app_id(integration.app_id) if integration.app_id else None,
            waba_id_masked=self._mask_waba_id(integration.waba_id) if integration.waba_id else None,
            phone_number_id_masked=phone_number_id_masked,
            whatsapp_phone_e164=integration.whatsapp_phone_e164,
            verified_at=integration.last_verified_at,
            last_error=integration.last_error,
            token_last_updated=integration.updated_at,  # Use updated_at as proxy for token update
            webhook_url=webhook_url,
            last_webhook_at=last_webhook_at,
        )

    @retryable(config=RetryConfig(max_attempts=3, base_delay=1.0))
    async def _call_graph_api(
        self, phone_number_id: str, system_user_token: str
    ) -> Dict[str, Any]:
        """
        Make Graph API call to verify credentials

        Args:
            phone_number_id: Phone number ID to verify
            system_user_token: System user access token

        Returns:
            Dict with verification response data

        Raises:
            APIError: If Graph API call fails
        """
        url = f"{self.graph_api_base_url}/{phone_number_id}"
        params = {"fields": "display_phone_number,verified_name"}
        headers = {"Authorization": f"Bearer {system_user_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 200:
                    return response.json()

                # Handle Graph API errors
                error_data = response.json() if response.content else {}
                error_code = error_data.get("error", {}).get(
                    "code", response.status_code
                )
                error_message = error_data.get("error", {}).get(
                    "message", "Unknown error"
                )
                error_subcode = error_data.get("error", {}).get("error_subcode")

                logger.error(
                    "Graph API verification failed",
                    extra={
                        "event": "graph_api_verification_failed",
                        "status_code": response.status_code,
                        "error_code": error_code,
                        "error_message": error_message,
                        "error_subcode": error_subcode,
                        # Never log the actual token
                        "phone_number_id": self._mask_phone_number_id(phone_number_id),
                    },
                )

                raise APIError(
                    code=ErrorCode.WHATSAPP_VERIFICATION_FAILED,
                    message="Invalid WhatsApp credentials or permissions",
                    details={
                        "graph_error": error_message,
                        "error_code": error_code,
                        "error_subcode": error_subcode,
                    },
                )

            except httpx.TimeoutException:
                logger.error(
                    "Graph API request timeout", extra={"event": "graph_api_timeout"}
                )
                raise APIError(
                    code=ErrorCode.WHATSAPP_VERIFICATION_FAILED,
                    message="WhatsApp verification timeout",
                )
            except httpx.RequestError as e:
                logger.error(
                    "Graph API request failed",
                    extra={"event": "graph_api_request_failed", "error": str(e)},
                )
                raise APIError(
                    code=ErrorCode.WHATSAPP_VERIFICATION_FAILED,
                    message="WhatsApp verification network error",
                )

    def _mask_phone_number_id(self, phone_number_id: str) -> str:
        """
        Mask phone number ID for security (show last 4 digits)

        Args:
            phone_number_id: Full phone number ID

        Returns:
            Masked phone number ID
        """
        if len(phone_number_id) <= 4:
            return "*" * len(phone_number_id)

        return "*" * (len(phone_number_id) - 4) + phone_number_id[-4:]

    def _mask_app_id(self, app_id: str) -> str:
        """
        Mask app ID for security (show first 6 and last 4 digits)

        Args:
            app_id: Full app ID

        Returns:
            Masked app ID (e.g., 684132••••••5988)
        """
        if len(app_id) <= 10:
            return "*" * len(app_id)

        return app_id[:6] + "•" * (len(app_id) - 10) + app_id[-4:]

    def _mask_waba_id(self, waba_id: str) -> str:
        """
        Mask WABA ID for security (show first 4 and last 4 digits)

        Args:
            waba_id: Full WABA ID

        Returns:
            Masked WABA ID (e.g., 1871••••••8542)
        """
        if len(waba_id) <= 8:
            return "*" * len(waba_id)

        return waba_id[:4] + "•" * (len(waba_id) - 8) + waba_id[-4:]
