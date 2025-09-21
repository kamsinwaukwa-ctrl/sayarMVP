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
    MetaCredentialsResponse,
    MetaIntegrationStatusResponse,
    MetaTokenRotateRequest,
    MetaIntegrationError
)
from ..models.api import ApiResponse, ApiErrorResponse
from ..services.meta_integration_service import MetaIntegrationService
from ..dependencies.auth import get_current_user, get_current_admin
from ..middleware.rate_limit import RateLimiter, get_client_ip
from ..database.connection import get_db
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter

logger = get_logger(__name__)
router = APIRouter(prefix="/integrations/meta", tags=["Meta Integration"])

# Rate limiters for Meta integration endpoints
meta_credentials_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5 per 5 minutes
meta_status_rate_limiter = RateLimiter(max_attempts=20, window_seconds=60)  # 20 per minute

async def check_meta_credentials_rate_limit(request: Request, merchant_id: UUID) -> None:
    """Check rate limit for credential modification endpoints"""
    client_ip = get_client_ip(request)
    merchant_key = f"meta_creds:merchant:{merchant_id}"
    ip_key = f"meta_creds:ip:{client_ip}"

    if (meta_credentials_rate_limiter.is_rate_limited(merchant_key) or
        meta_credentials_rate_limiter.is_rate_limited(ip_key)):

        reset_time = max(
            meta_credentials_rate_limiter.get_reset_time(merchant_key),
            meta_credentials_rate_limiter.get_reset_time(ip_key)
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many Meta credential requests. Try again in {reset_in} seconds.",
            headers={"Retry-After": str(reset_in)}
        )

    # Record attempt
    meta_credentials_rate_limiter.record_attempt(merchant_key)
    meta_credentials_rate_limiter.record_attempt(ip_key)

async def check_meta_status_rate_limit(request: Request, merchant_id: UUID) -> None:
    """Check rate limit for status check endpoints"""
    client_ip = get_client_ip(request)
    merchant_key = f"meta_status:merchant:{merchant_id}"
    ip_key = f"meta_status:ip:{client_ip}"

    if (meta_status_rate_limiter.is_rate_limited(merchant_key) or
        meta_status_rate_limiter.is_rate_limited(ip_key)):

        reset_time = max(
            meta_status_rate_limiter.get_reset_time(merchant_key),
            meta_status_rate_limiter.get_reset_time(ip_key)
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many status requests. Try again in {reset_in} seconds.",
            headers={"Retry-After": str(reset_in)}
        )

    # Record attempt
    meta_status_rate_limiter.record_attempt(merchant_key)
    meta_status_rate_limiter.record_attempt(ip_key)


@router.put(
    "/credentials",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Store Meta credentials",
    description="Store and verify Meta Commerce Catalog credentials for the current merchant"
)
async def store_credentials(
    request_data: MetaCredentialsRequest,
    request: Request,
    principal = Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db)
) -> MetaCredentialsResponse:
    """
    Store Meta Commerce Catalog credentials.

    Requires admin role. Encrypts and stores credentials, then verifies them
    with the Meta Graph API. Returns verification status.

    - **catalog_id**: Meta Commerce Catalog ID (numeric string)
    - **system_user_token**: Meta system user access token (starts with EAA)
    - **app_id**: Meta App ID (numeric string)
    - **waba_id**: WhatsApp Business Account ID (optional, numeric string)
    """
    try:
        # Apply rate limiting
        await check_meta_credentials_rate_limit(request, principal.merchant_id)

        service = MetaIntegrationService(db)
        result = await service.store_credentials(principal.merchant_id, request_data)

        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "store_credentials", "status": "success"}
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "store_credentials", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error storing Meta credentials: {str(e)}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "store_credentials", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store Meta credentials"
        )


@router.patch(
    "/catalog",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Update catalog ID only",
    description="Store only catalog_id, reusing existing WhatsApp credentials for Meta integration"
)
async def update_catalog_id(
    request_data: MetaCatalogOnlyRequest,
    request: Request,
    principal = Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db)
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
        result = await service.update_catalog_only(principal.merchant_id, request_data.catalog_id)

        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "update_catalog_id", "status": "success"}
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta catalog update error: {e.message}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "update_catalog_id", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error updating catalog ID: {str(e)}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "update_catalog_id", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update catalog ID"
        )


@router.get(
    "/status",
    response_model=MetaIntegrationStatusResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Get Meta integration status",
    description="Get the current Meta Commerce Catalog integration status for the merchant"
)
async def get_integration_status(
    request: Request,
    principal = Depends(get_current_user),  # Admin or staff
    db: AsyncSession = Depends(get_db)
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

        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "get_status", "status": "success"}
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "get_status", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error getting Meta status: {str(e)}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "get_status", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Meta integration status"
        )


@router.delete(
    "/credentials",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Delete Meta integration",
    description="Remove Meta Commerce Catalog integration for the current merchant"
)
async def delete_integration(
    request: Request,
    principal = Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db)
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

        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "delete_integration", "status": "success"}
        )

        if success:
            return {
                "success": True,
                "message": "Meta integration removed successfully"
            }
        else:
            return {
                "success": False,
                "message": "No Meta integration found to delete"
            }

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "delete_integration", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting Meta integration: {str(e)}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "delete_integration", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete Meta integration"
        )


@router.post(
    "/rotate",
    response_model=MetaCredentialsResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {"model": ApiErrorResponse, "description": "No existing integration found"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Rotate Meta credentials",
    description="Rotate the system user token for existing Meta integration"
)
async def rotate_credentials(
    request_data: MetaTokenRotateRequest,
    request: Request,
    principal = Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db)
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

        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "rotate_credentials", "status": "success"}
        )

        return result

    except MetaIntegrationError as e:
        logger.error(f"Meta integration error: {e.message}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "rotate_credentials", "status": "error"}
        )

        if "No existing Meta integration found" in e.message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existing Meta integration found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.message
            )
    except Exception as e:
        logger.error(f"Unexpected error rotating Meta credentials: {str(e)}")
        increment_counter(
            "meta_integration_api_requests_total",
            tags={"endpoint": "rotate_credentials", "status": "error"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate Meta credentials"
        )