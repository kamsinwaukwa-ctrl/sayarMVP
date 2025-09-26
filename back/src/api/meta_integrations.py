"""
Meta Integration API endpoints for credential management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import time

from ..models.meta_integrations import (
    MetaCredentialsRequest,
    MetaCatalogOnlyRequest,
    MetaWhatsAppCredentialsRequest,
    MetaCredentialsResponse,
    MetaIntegrationStatusResponse,
    MetaTokenRotateRequest,
    MetaIntegrationError,
)
from ..models.api import ApiResponse, ApiErrorResponse, MetaIntegrationSummaryResponse
from ..services.meta_integration_service import MetaIntegrationService
from ..dependencies.auth import get_current_user, get_current_admin
from ..middleware.rate_limit import RateLimiter, get_client_ip
from ..database.connection import get_db
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter


def safe_increment(*args, **kwargs):
    """Safe wrapper for increment_counter that never crashes the request"""
    try:
        increment_counter(*args, **kwargs)
    except Exception:
        # Never let metrics crash business logic
        pass

logger = get_logger(__name__)
router = APIRouter(prefix="/integrations/meta", tags=["Meta Integration"])

# Rate limiters for Meta integration endpoints
meta_credentials_rate_limiter = RateLimiter(
    max_attempts=5, window_seconds=300
)  # 5 per 5 minutes
meta_status_rate_limiter = RateLimiter(
    max_attempts=20, window_seconds=60
)  # 20 per minute


async def check_meta_credentials_rate_limit(
    request: Request, merchant_id: UUID
) -> None:
    """Check rate limit for credential modification endpoints"""
    client_ip = get_client_ip(request)
    merchant_key = f"meta_creds:merchant:{merchant_id}"
    ip_key = f"meta_creds:ip:{client_ip}"

    if meta_credentials_rate_limiter.is_rate_limited(
        merchant_key
    ) or meta_credentials_rate_limiter.is_rate_limited(ip_key):

        reset_time = max(
            meta_credentials_rate_limiter.get_reset_time(merchant_key),
            meta_credentials_rate_limiter.get_reset_time(ip_key),
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many Meta credential requests. Try again in {reset_in} seconds.",
            headers={"Retry-After": str(reset_in)},
        )

    # Record attempt
    meta_credentials_rate_limiter.record_attempt(merchant_key)
    meta_credentials_rate_limiter.record_attempt(ip_key)


async def check_meta_status_rate_limit(request: Request, merchant_id: UUID) -> None:
    """Check rate limit for status check endpoints"""
    client_ip = get_client_ip(request)
    merchant_key = f"meta_status:merchant:{merchant_id}"
    ip_key = f"meta_status:ip:{client_ip}"

    if meta_status_rate_limiter.is_rate_limited(
        merchant_key
    ) or meta_status_rate_limiter.is_rate_limited(ip_key):

        reset_time = max(
            meta_status_rate_limiter.get_reset_time(merchant_key),
            meta_status_rate_limiter.get_reset_time(ip_key),
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many status requests. Try again in {reset_in} seconds.",
            headers={"Retry-After": str(reset_in)},
        )

    # Record attempt
    meta_status_rate_limiter.record_attempt(merchant_key)
    meta_status_rate_limiter.record_attempt(ip_key)


@router.patch(
    "/credentials",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Update Meta credentials (all-in-one)",
    description="Update Meta Commerce Catalog credentials for the current merchant (partial updates supported)",
)
async def update_credentials(
    request_data: MetaCredentialsRequest,
    request: Request,
    principal=Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db),
) -> MetaCredentialsResponse:
    """
    Update Meta Commerce Catalog credentials (all-in-one).

    Requires admin role. Performs partial updates - only provided fields are updated.
    Encrypts and stores credentials, then verifies them with the Meta Graph API.
    Ideal for settings pages where users edit all credentials at once.

    - **catalog_id**: Meta Commerce Catalog ID (numeric string, optional)
    - **system_user_token**: Meta system user access token (starts with EAA, optional)
    - **app_id**: Meta App ID (numeric string, optional)
    - **waba_id**: WhatsApp Business Account ID (optional, numeric string)
    """
    try:
        # Apply rate limiting
        await check_meta_credentials_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        result = await service.store_credentials(principal.merchant_id, request_data)

        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error storing Meta credentials: {str(e)}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store Meta credentials",
        )


@router.patch(
    "/catalog",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Update catalog ID only",
    description="Store only catalog_id, reusing existing WhatsApp credentials for Meta integration",
)
async def update_catalog_id(
    request_data: MetaCatalogOnlyRequest,
    request: Request,
    principal=Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db),
) -> MetaCredentialsResponse:
    """
    Update catalog ID only (reuses WhatsApp credentials).

    Simplified endpoint that only requires catalog_id. Will automatically
    use app_id and system_user_token from existing WhatsApp integration.

    - **catalog_id**: Meta Commerce Catalog ID (numeric string)
    """
    try:
        # Apply rate limiting
        await check_meta_credentials_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        result = await service.update_catalog_only(
            principal.merchant_id, request_data.catalog_id
        )

        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta catalog update error: {e.message}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        request_id = getattr(request.state, 'request_id', 'unknown')
        logger.exception(
            "catalog_update_failed",
            extra={
                "request_id": request_id,
                "merchant_id": str(principal.merchant_id),
                "catalog_id": request_data.catalog_id,
                "error": str(e)
            }
        )
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update catalog ID",
        )


@router.patch(
    "/whatsapp",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {"model": ApiErrorResponse, "description": "Meta integration not found"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Update WhatsApp credentials only",
    description="Store only WhatsApp credentials, preserving existing catalog_id from Meta integration",
)
async def update_whatsapp_credentials(
    request_data: MetaWhatsAppCredentialsRequest,
    request: Request,
    principal=Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db),
) -> MetaCredentialsResponse:
    """
    Update WhatsApp credentials only (preserves catalog_id).

    Simplified endpoint that only updates WhatsApp-related fields. Will automatically
    preserve the existing catalog_id from Meta Catalog integration.

    - **app_id**: Meta App ID (numeric string)
    - **system_user_token**: Meta system user access token (starts with EAA)
    - **waba_id**: WhatsApp Business Account ID (optional)
    - **phone_number_id**: WhatsApp Phone Number ID for API calls (optional)
    - **whatsapp_phone_e164**: WhatsApp phone number in E164 format (optional)
    """
    try:
        # Apply rate limiting
        await check_meta_credentials_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        result = await service.update_whatsapp_credentials(principal.merchant_id, request_data)

        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        return result

    except MetaIntegrationError as e:
        request_id = getattr(request.state, 'request_id', 'unknown')
        logger.warning(
            "whatsapp_update_failed",
            extra={
                "request_id": request_id,
                "merchant_id": str(principal.merchant_id),
                "error": e.message,
                "error_code": e.error_code
            }
        )
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        request_id = getattr(request.state, 'request_id', 'unknown')
        logger.exception(
            "whatsapp_update_failed",
            extra={
                "request_id": request_id,
                "merchant_id": str(principal.merchant_id),
                "app_id": request_data.app_id,
                "error": str(e)
            }
        )
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update WhatsApp credentials",
        )


@router.get(
    "/status",
    response_model=MetaIntegrationStatusResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Get Meta integration status",
    description="Get the current Meta Commerce Catalog integration status for the merchant",
)
async def get_integration_status(
    request: Request,
    principal=Depends(get_current_user),  # Admin or staff
    db: AsyncSession = Depends(get_db),
) -> MetaIntegrationStatusResponse:
    """
    Get Meta integration status.

    Returns the current status of Meta Commerce Catalog integration:
    - **not_configured**: No credentials stored
    - **verified**: Credentials are valid and working
    - **invalid**: Credentials are invalid or expired
    - **pending**: Verification in progress

    Staff users can view status but not credential details.
    """
    try:
        # Apply rate limiting
        await check_meta_status_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        result = await service.get_integration_status(principal.merchant_id)

        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error getting Meta status: {str(e)}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Meta integration status",
        )


@router.get(
    "/summary",
    response_model=MetaIntegrationSummaryResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Get safe Meta integration summary",
    description="Get a safe summary of Meta integration status without exposing sensitive data",
)
async def get_integration_summary(
    principal=Depends(get_current_user),  # Any authenticated user
    db: AsyncSession = Depends(get_db),
) -> MetaIntegrationSummaryResponse:
    """
    Get safe Meta integration summary.

    Returns only non-sensitive information about the Meta integration:
    - Whether catalog_id is present
    - Whether credentials (app_id, waba_id) are present
    - Whether integration is verified
    - Current status
    - Catalog name (safe to expose)

    Never returns tokens, keys, or other sensitive data.
    """
    try:
        service = MetaIntegrationService(db)
        integration = await service._get_integration_by_merchant(principal.merchant_id)

        # Default values if no integration found
        if not integration:
            return MetaIntegrationSummaryResponse(
                catalog_present=False,
                credentials_present=False,
                verified=False,
                status="pending",
                catalog_name=None
            )

        # Calculate safe boolean flags from database fields
        catalog_present = bool(integration.catalog_id)
        credentials_present = bool(integration.app_id and integration.waba_id)
        verified = (integration.status == "verified")

        # Log the summary fetch (without sensitive data)
        logger.info(
            "meta_summary_fetch",
            extra={
                "event": "meta_summary_fetch",
                "merchant_id": str(principal.merchant_id),
                "status": integration.status,
                "catalog_present": catalog_present,
                "credentials_present": credentials_present,
                "verified": verified,
            }
        )

        safe_increment(
            "meta_integration_summary_requests_total",
            component="meta_integrations"
        )

        return MetaIntegrationSummaryResponse(
            catalog_present=catalog_present,
            credentials_present=credentials_present,
            verified=verified,
            status=integration.status,
            catalog_name=integration.catalog_name  # Safe to expose
        )

    except Exception as e:
        logger.error(
            f"Unexpected error getting Meta integration summary: {str(e)}",
            extra={
                "event": "meta_summary_error",
                "merchant_id": str(principal.merchant_id),
                "error": str(e)
            }
        )
        safe_increment(
            "meta_integration_summary_errors_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Meta integration summary",
        )


@router.delete(
    "/credentials",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Delete Meta integration",
    description="Remove Meta Commerce Catalog integration for the current merchant",
)
async def delete_integration(
    request: Request,
    principal=Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete Meta integration.

    Requires admin role. Permanently removes Meta Commerce Catalog
    credentials and integration configuration.

    **Warning**: This action cannot be undone and will disable
    product synchronization to WhatsApp Catalog.
    """
    try:
        # Apply rate limiting
        await check_meta_credentials_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        success = await service.delete_integration(principal.merchant_id)

        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )

        if success:
            return {"success": True, "message": "Meta integration removed successfully"}
        else:
            return {"success": False, "message": "No Meta integration found to delete"}

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting Meta integration: {str(e)}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete Meta integration",
        )


@router.post(
    "/rotate",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {
            "model": ApiErrorResponse,
            "description": "No existing integration found",
        },
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"},
    },
    summary="Rotate Meta credentials",
    description="Rotate the system user token for existing Meta integration",
)
async def rotate_credentials(
    request_data: MetaTokenRotateRequest,
    request: Request,
    principal=Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db),
) -> MetaCredentialsResponse:
    """
    Rotate Meta system user token.

    Requires admin role and existing Meta integration. Updates the
    system user token while preserving other credentials, then
    verifies the new token with Meta Graph API.

    - **system_user_token**: New Meta system user access token (starts with EAA)
    """
    try:
        # Apply rate limiting
        await check_meta_credentials_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        result = await service.rotate_token(principal.merchant_id, request_data)

        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )

        if "No existing Meta integration found" in e.message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existing Meta integration found",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
            )
    except Exception as e:
        logger.error(f"Unexpected error rotating Meta credentials: {str(e)}")
        safe_increment(
            "meta_integration_api_requests_total",
            component="meta_integrations"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate Meta credentials",
        )
