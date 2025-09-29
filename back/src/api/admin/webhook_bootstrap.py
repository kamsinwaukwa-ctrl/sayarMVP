"""
Admin API endpoints for webhook bootstrap and management
"""

import os
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ...database.connection import get_db
from ...dependencies.auth import get_current_admin
from ...models.auth import CurrentPrincipal
from ...models.errors import APIError, ErrorCode
from ...utils.logger import get_logger
from ...utils.db_session import setup_admin_session, DatabaseSessionHelper

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/webhooks", tags=["admin", "webhooks"])


class WebhookBootstrapRequest(BaseModel):
    """Request model for webhook bootstrap"""

    merchant_id: UUID = Field(..., description="Merchant UUID")
    app_id: str = Field(..., description="Meta App ID")
    app_secret: str = Field(..., min_length=1, description="Meta App Secret")
    phone_number_id: Optional[str] = Field(None, description="WhatsApp Phone Number ID")
    waba_id: Optional[str] = Field(None, description="WhatsApp Business Account ID")
    whatsapp_phone_e164: Optional[str] = Field(None, description="WhatsApp phone in E164 format")


class WebhookBootstrapResponse(BaseModel):
    """Response model for webhook bootstrap"""

    webhook_id: UUID = Field(..., description="Webhook endpoint ID")
    callback_url: str = Field(..., description="Webhook callback URL for Meta console")
    verify_token: str = Field(..., description="Verify token for Meta console (SAVE THIS - shown once only)")
    created_at: str = Field(..., description="Timestamp when created")

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_id": "123e4567-e89b-12d3-a456-426614174000",
                "callback_url": "https://api.example.com/api/webhooks/whatsapp/app/684132123456",
                "verify_token": "xYz123_AbC456_DeF789_secure_token_here",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class WebhookRotateTokenRequest(BaseModel):
    """Request model for rotating verify token"""

    app_id: str = Field(..., description="Meta App ID to rotate token for")


@router.post("/bootstrap", response_model=WebhookBootstrapResponse)
async def bootstrap_webhook(
    request: WebhookBootstrapRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Bootstrap or update webhook configuration for a merchant

    This admin-only endpoint:
    1. Encrypts the app_secret using PGP
    2. Generates and hashes a verify token
    3. Creates or updates the webhook endpoint record
    4. Returns the callback URL and verify token (shown once only)

    The verify token is only shown once - save it immediately!
    """
    try:
        # Setup database session with encryption key and base URL
        await setup_admin_session(db)

        # Get base URL for callback URL construction
        base_url = os.getenv("RAILWAY_STATIC_URL", "http://localhost:8000")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        # Call SQL admin function
        result = await db.execute(
            text("""
                SELECT * FROM admin_create_or_rotate_webhook(
                    p_merchant_id := :merchant_id,
                    p_provider := 'whatsapp',
                    p_app_id := :app_id,
                    p_app_secret_plain := :app_secret,
                    p_base_url := :base_url,
                    p_phone_number_id := :phone_number_id,
                    p_waba_id := :waba_id,
                    p_whatsapp_phone_e164 := :whatsapp_phone
                )
            """),
            {
                "merchant_id": request.merchant_id,
                "app_id": request.app_id,
                "app_secret": request.app_secret,
                "base_url": base_url,
                "phone_number_id": request.phone_number_id,
                "waba_id": request.waba_id,
                "whatsapp_phone": request.whatsapp_phone_e164,
            }
        )

        row = result.fetchone()
        if not row:
            raise APIError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to bootstrap webhook"
            )

        await db.commit()

        # Log audit event (without secrets!)
        logger.info(
            "Webhook bootstrapped successfully",
            extra={
                "event": "webhook_bootstrap_success",
                "merchant_id": str(request.merchant_id),
                "app_id": request.app_id,
                "webhook_id": str(row.id),
                # Never log the verify_token or app_secret!
            }
        )

        return WebhookBootstrapResponse(
            webhook_id=row.id,
            callback_url=row.callback_url,
            verify_token=row.verify_token,  # Show once only!
            created_at=datetime.utcnow().isoformat() + "Z"
        )

    except ValueError as e:
        logger.error(
            "Configuration error during webhook bootstrap",
            extra={
                "event": "webhook_bootstrap_config_error",
                "error": str(e),
                "merchant_id": str(request.merchant_id),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Unexpected error during webhook bootstrap",
            extra={
                "event": "webhook_bootstrap_error",
                "error": str(e),
                "merchant_id": str(request.merchant_id),
            }
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bootstrap webhook"
        )


@router.post("/rotate-token", response_model=WebhookBootstrapResponse)
async def rotate_verify_token(
    request: WebhookRotateTokenRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate the verify token for an existing webhook

    This admin-only endpoint:
    1. Generates a new verify token
    2. Updates the hash in the database
    3. Returns the new verify token (shown once only)

    The app_secret remains unchanged.
    """
    try:
        # Setup database session with encryption key and base URL
        await setup_admin_session(db)

        # Call SQL function to rotate token
        result = await db.execute(
            text("""
                SELECT * FROM admin_rotate_verify_token(:app_id)
            """),
            {"app_id": request.app_id}
        )

        row = result.fetchone()
        if not row:
            raise APIError(
                code=ErrorCode.NOT_FOUND,
                message=f"No active webhook found for app_id: {request.app_id}"
            )

        await db.commit()

        # Log audit event
        logger.info(
            "Webhook verify token rotated",
            extra={
                "event": "webhook_token_rotate_success",
                "app_id": request.app_id,
                "webhook_id": str(row.id),
            }
        )

        return WebhookBootstrapResponse(
            webhook_id=row.id,
            callback_url=row.callback_url,
            verify_token=row.verify_token,  # New token - show once only!
            created_at=datetime.utcnow().isoformat() + "Z"
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(
            "Error rotating verify token",
            extra={
                "event": "webhook_token_rotate_error",
                "error": str(e),
                "app_id": request.app_id,
            }
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate verify token"
        )