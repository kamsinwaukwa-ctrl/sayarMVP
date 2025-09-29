"""
API endpoints for third-party integrations (WhatsApp, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.connection import get_db
from ..dependencies.auth import get_current_admin
from ..models.api import (
    ApiResponse,
    WhatsAppCredentialsRequest,
    WhatsAppCredentialsPartialRequest,
    WhatsAppStatusResponse,
    WhatsAppVerifyResponse,
)
from ..models.auth import CurrentPrincipal
from ..models.errors import APIError, ErrorCode
from ..services.whatsapp_credentials_service import WhatsAppCredentialsService
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.post(
    "/whatsapp/credentials", response_model=ApiResponse[WhatsAppStatusResponse]
)
async def save_whatsapp_credentials(
    request: WhatsAppCredentialsRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Save WhatsApp Business API credentials for merchant

    Requires admin role. Encrypts and stores WABA credentials for future use.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.save_credentials(principal.merchant_id, request)

        return ApiResponse(
            data=result, message="WhatsApp credentials saved successfully"
        )

    except APIError as e:
        logger.error(
            "API error saving WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code), detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error saving WhatsApp credentials",
            extra={"merchant_id": str(principal.merchant_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {},
                },
            },
        )


@router.put("/whatsapp/credentials", response_model=ApiResponse[WhatsAppStatusResponse])
async def update_whatsapp_credentials(
    request: WhatsAppCredentialsRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update WhatsApp Business API credentials for merchant

    Requires admin role. Updates existing credentials with new values.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.save_credentials(principal.merchant_id, request)

        return ApiResponse(
            data=result, message="WhatsApp credentials updated successfully"
        )

    except APIError as e:
        logger.error(
            "API error updating WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code), detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating WhatsApp credentials",
            extra={"merchant_id": str(principal.merchant_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {},
                },
            },
        )


@router.patch("/whatsapp/credentials", response_model=ApiResponse[WhatsAppStatusResponse])
async def update_whatsapp_credentials_partial(
    request: WhatsAppCredentialsPartialRequest,
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update WhatsApp Business API credentials for merchant

    Requires admin role. Updates only the provided fields, leaving others unchanged.
    Supports separate flows for updating IDs vs replacing tokens.
    """
    try:
        # Import here to avoid circular imports
        from ..models.meta_integrations import MetaIntegration
        from ..utils.encryption import get_encryption_service
        from sqlalchemy import update
        from datetime import datetime

        # Get existing integration
        result = await db.execute(
            select(MetaIntegration).where(MetaIntegration.merchant_id == principal.merchant_id)
        )
        integration = result.scalar_one_or_none()

        if not integration and not request.system_user_token:
            raise APIError(
                code=ErrorCode.WHATSAPP_NOT_CONFIGURED,
                message="No WhatsApp integration found. Please provide a system_user_token to create one."
            )

        # Prepare update data
        update_data = {
            "updated_at": datetime.utcnow(),
        }

        # Update IDs if provided (non-sensitive data)
        if request.app_id is not None:
            update_data["app_id"] = request.app_id
        if request.waba_id is not None:
            update_data["waba_id"] = request.waba_id
        if request.phone_number_id is not None:
            update_data["phone_number_id"] = request.phone_number_id
        if request.whatsapp_phone_e164 is not None:
            update_data["whatsapp_phone_e164"] = request.whatsapp_phone_e164

        # Handle token replacement (sensitive data)
        if request.system_user_token is not None:
            encryption_service = get_encryption_service()
            encrypted_token = encryption_service.encrypt_data(request.system_user_token)
            update_data["system_user_token_encrypted"] = encrypted_token.encrypted_data

        if integration:
            # Update existing integration
            stmt = (
                update(MetaIntegration)
                .where(MetaIntegration.merchant_id == principal.merchant_id)
                .values(**update_data)
                .returning(MetaIntegration)
            )
            result = await db.execute(stmt)
            updated_integration = result.scalar_one()
        else:
            # Create new integration (only if token provided)
            if not request.system_user_token:
                raise APIError(
                    code=ErrorCode.WHATSAPP_NOT_CONFIGURED,
                    message="Cannot create integration without system_user_token"
                )

            integration_data = {
                "merchant_id": principal.merchant_id,
                "status": "pending",
                **update_data
            }

            from sqlalchemy.dialects.postgresql import insert
            stmt = insert(MetaIntegration).values(**integration_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["merchant_id"], set_=integration_data
            ).returning(MetaIntegration)

            result = await db.execute(stmt)
            updated_integration = result.scalar_one()

        await db.commit()

        # Get updated status using the service
        service = WhatsAppCredentialsService(db)
        status_response = await service.get_status(principal.merchant_id)

        # Perform auto-validation if requested
        validation_result = None
        if request.validate_after_save:
            try:
                logger.info(
                    "Auto-validating WhatsApp credentials after save",
                    extra={
                        "merchant_id": str(principal.merchant_id),
                        "event": "whatsapp_auto_validation_started"
                    }
                )

                # Attempt to verify the connection
                verify_response = await service.verify_connection(principal.merchant_id)

                # Import ValidationResult here to avoid circular imports
                from ..models.api import ValidationResult
                validation_result = ValidationResult(
                    is_valid=True,
                    tested_at=datetime.utcnow(),
                    business_name=verify_response.business_name,
                    phone_number_display=verify_response.phone_number_display
                )

                logger.info(
                    "Auto-validation successful",
                    extra={
                        "merchant_id": str(principal.merchant_id),
                        "event": "whatsapp_auto_validation_success",
                        "business_name": verify_response.business_name
                    }
                )

            except APIError as validation_error:
                # Validation failed, but don't fail the save operation
                logger.warning(
                    "Auto-validation failed after credential save",
                    extra={
                        "merchant_id": str(principal.merchant_id),
                        "event": "whatsapp_auto_validation_failed",
                        "error_code": validation_error.code.value,
                        "error_message": str(validation_error)
                    }
                )

                from ..models.api import ValidationResult
                validation_result = ValidationResult(
                    is_valid=False,
                    tested_at=datetime.utcnow(),
                    error_message=str(validation_error),
                    error_code=validation_error.code.value
                )

            except Exception as validation_error:
                # Unexpected validation error, log but don't fail
                logger.error(
                    "Unexpected error during auto-validation",
                    extra={
                        "merchant_id": str(principal.merchant_id),
                        "event": "whatsapp_auto_validation_error",
                        "error": str(validation_error)
                    }
                )

                from ..models.api import ValidationResult
                validation_result = ValidationResult(
                    is_valid=False,
                    tested_at=datetime.utcnow(),
                    error_message=f"Validation error: {str(validation_error)}",
                    error_code="VALIDATION_ERROR"
                )

        # Add validation result to the response
        status_response.validation_result = validation_result

        # Determine response message based on validation
        if validation_result:
            if validation_result.is_valid:
                message = "WhatsApp credentials updated and verified successfully"
            else:
                message = "WhatsApp credentials updated but validation failed - please check configuration"
        else:
            message = "WhatsApp credentials updated successfully"

        return ApiResponse(
            data=status_response,
            message=message
        )

    except APIError as e:
        await db.rollback()
        logger.error(
            "API error updating WhatsApp credentials",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code), detail=e.to_dict()
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error updating WhatsApp credentials",
            extra={"merchant_id": str(principal.merchant_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {},
                },
            },
        )


@router.post("/whatsapp/verify", response_model=ApiResponse[WhatsAppVerifyResponse])
async def verify_whatsapp_connection(
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify WhatsApp Business API connection

    Requires admin role. Makes harmless Graph API call to verify credentials.
    """
    try:
        service = WhatsAppCredentialsService(db)
        result = await service.verify_connection(principal.merchant_id)

        return ApiResponse(
            data=result, message="WhatsApp connection verified successfully"
        )

    except APIError as e:
        logger.error(
            "API error verifying WhatsApp connection",
            extra={
                "merchant_id": str(principal.merchant_id),
                "error_code": e.code.value,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code), detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error verifying WhatsApp connection",
            extra={"merchant_id": str(principal.merchant_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {},
                },
            },
        )


@router.get("/whatsapp/status", response_model=ApiResponse[WhatsAppStatusResponse])
async def get_whatsapp_status(
    principal: CurrentPrincipal = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
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
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=_get_http_status_for_error_code(e.code), detail=e.to_dict()
        )
    except Exception as e:
        logger.error(
            "Unexpected error getting WhatsApp status",
            extra={"merchant_id": str(principal.merchant_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "ok": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {},
                },
            },
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
