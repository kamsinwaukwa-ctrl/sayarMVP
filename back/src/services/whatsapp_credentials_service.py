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

        # Get merchant credentials
        result = await self.db.execute(
            select(Merchant).where(Merchant.id == merchant_id)
        )
        merchant = result.scalar_one_or_none()

        if not merchant:
            raise APIError(
                code=ErrorCode.MERCHANT_NOT_FOUND, message="Merchant not found"
            )

        if not merchant.system_user_token_enc:
            raise APIError(
                code=ErrorCode.WHATSAPP_CREDENTIALS_NOT_FOUND,
                message="WhatsApp credentials not configured",
            )

        try:
            # Decrypt credentials
            encryption_service = get_encryption_service()
            phone_number_id = encryption_service.decrypt_data(
                merchant.phone_number_id_enc
            )
            system_user_token = encryption_service.decrypt_data(
                merchant.system_user_token_enc
            )

            # Call Graph API to verify
            verification_result = await self._call_graph_api(
                phone_number_id, system_user_token
            )

            # Determine connection status based on environment
            connection_status = (
                WAConnectionStatus.VERIFIED_TEST
                if merchant.wa_environment == "test"
                else WAConnectionStatus.VERIFIED_PROD
            )

            # Update verification status
            await self.db.execute(
                update(Merchant)
                .where(Merchant.id == merchant_id)
                .values(
                    wa_connection_status=connection_status.value,
                    wa_verified_at=datetime.utcnow(),
                    wa_last_error=None,
                    updated_at=datetime.utcnow(),
                )
            )
            await self.db.commit()

            logger.info(
                "WhatsApp verification successful",
                extra={
                    "event": "whatsapp_verification_success",
                    "merchant_id": str(merchant_id),
                    "environment": merchant.wa_environment,
                    "business_name": verification_result.get("verified_name"),
                },
            )

            return WhatsAppVerifyResponse(
                connection_status=connection_status,
                environment=WAEnvironment(merchant.wa_environment),
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

            # Update error status
            await self.db.execute(
                update(Merchant)
                .where(Merchant.id == merchant_id)
                .values(
                    wa_connection_status="not_connected",
                    wa_last_error=error_msg,
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
        result = await self.db.execute(
            select(Merchant).where(Merchant.id == merchant_id)
        )
        merchant = result.scalar_one_or_none()

        if not merchant:
            raise APIError(
                code=ErrorCode.MERCHANT_NOT_FOUND, message="Merchant not found"
            )

        # Decrypt phone number ID for masking if available
        phone_number_id_masked = None
        if merchant.phone_number_id_enc:
            try:
                encryption_service = get_encryption_service()
                phone_number_id = encryption_service.decrypt_data(
                    merchant.phone_number_id_enc
                )
                phone_number_id_masked = self._mask_phone_number_id(phone_number_id)
            except Exception:
                # If decryption fails, just return None
                pass

        return WhatsAppStatusResponse(
            connection_status=WAConnectionStatus(
                merchant.wa_connection_status or "not_connected"
            ),
            environment=WAEnvironment(merchant.wa_environment or "test"),
            phone_number_id=phone_number_id_masked,
            verified_at=merchant.wa_verified_at,
            last_error=merchant.wa_last_error,
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
