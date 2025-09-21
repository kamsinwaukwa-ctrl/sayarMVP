"""
API endpoints for third-party integrations (WhatsApp, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..dependencies.auth import get_current_admin
from ..models.api import (
    ApiResponse,
    WhatsAppCredentialsRequest,
    WhatsAppStatusResponse,
    WhatsAppVerifyResponse
)
from ..models.auth import CurrentPrincipal
from ..models.errors import APIError, ErrorCode
from ..services.whatsapp_credentials_service import WhatsAppCredentialsService
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.post("/whatsapp/credentials", response_model=ApiResponse[WhatsAppStatusResponse])
async def save_whatsapp_credentials(
    request: WhatsAppCredentialsRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Save WhatsApp Business API credentials for merchant

    Requires admin role. Encrypts and stores WABA credentials for future use.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.save_credentials(principal.merchant_id, request)

        return ApiResponse(
            data=result,
            message="WhatsApp credentials saved successfully"
        )

    except APIError as e:
        logger.error(
            "API error saving WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code),
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error saving WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {}
                }
            }
        )


@router.put("/whatsapp/credentials", response_model=ApiResponse[WhatsAppStatusResponse])
async def update_whatsapp_credentials(
    request: WhatsAppCredentialsRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update WhatsApp Business API credentials for merchant

    Requires admin role. Updates existing credentials with new values.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.save_credentials(principal.merchant_id, request)

        return ApiResponse(
            data=result,
            message="WhatsApp credentials updated successfully"
        )

    except APIError as e:
        logger.error(
            "API error updating WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code),
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {}
                }
            }
        )


@router.post("/whatsapp/verify", response_model=ApiResponse[WhatsAppVerifyResponse])
async def verify_whatsapp_connection(
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify WhatsApp Business API connection

    Requires admin role. Makes harmless Graph API call to verify credentials.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.verify_connection(principal.merchant_id)

        return ApiResponse(
            data=result,
            message="WhatsApp connection verified successfully"
        )

    except APIError as e:
        logger.error(
            "API error verifying WhatsApp connection",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code),
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error verifying WhatsApp connection",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {}
                }
            }
        )


@router.get("/whatsapp/status", response_model=ApiResponse[WhatsAppStatusResponse])
async def get_whatsapp_status(
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current WhatsApp connection status

    Requires admin role. Returns current connection state and metadata.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.get_status(principal.merchant_id)

        return ApiResponse(data=result)

    except APIError as e:
        logger.error(
            "API error getting WhatsApp status",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code),
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error getting WhatsApp status",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {}
                }
            }
        )


def _get_http_status_for_error_code(error_code: ErrorCode) -> int:
    """Map error codes to appropriate HTTP status codes"""
    error_status_map = {
        ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
        ErrorCode.AUTHENTICATION_FAILED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.AUTHORIZATION_FAILED: status.HTTP_403_FORBIDDEN,
        ErrorCode.MERCHANT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.WHATSAPP_CREDENTIALS_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.DUPLICATE_RESOURCE: status.HTTP_409_CONFLICT,
        ErrorCode.WHATSAPP_VERIFICATION_FAILED: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
        ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    return error_status_map.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)