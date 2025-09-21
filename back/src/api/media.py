"""
Media management API endpoints for Sayar WhatsApp Commerce Platform
Handles logo upload and signed URL generation with role-based access control
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional

from ..database.connection import get_db
from ..dependencies.auth import CurrentUser, CurrentAdmin
from ..models.api import APIResponse
from ..models.media import MediaUploadResponse, SignedUrlResponse
from ..services.media_service import MediaService
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter

logger = get_logger(__name__)
router = APIRouter(tags=["media"])


@router.post(
    "/api/v1/media/logo",
    response_model=APIResponse[MediaUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload merchant logo",
    description="Upload a logo file for the current merchant. Only admin users can upload logos.",
    responses={
        201: {"description": "Logo uploaded successfully"},
        400: {"description": "Invalid file or validation error"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        500: {"description": "Internal server error"},
    },
)
async def upload_logo(
    file: Annotated[
        UploadFile, File(description="Logo image file (PNG, JPEG, or WebP)")
    ],
    current_user: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[MediaUploadResponse]:
    """
    Upload merchant logo with validation and storage.

    - **Allowed file types**: PNG, JPEG, WebP
    - **Maximum file size**: 5MB
    - **Authentication**: Admin role required
    - **Storage**: Private storage with signed URL access

    The uploaded file will be stored as `logo.<ext>` and any existing logo will be overwritten.
    """
    logger.info(
        f"Logo upload request from user {current_user.user_id} for merchant {current_user.merchant_id}"
    )
    increment_counter(
        "media_upload_requests_total",
        {
            "merchant_id": str(current_user.merchant_id),
            "user_id": str(current_user.user_id),
        },
    )

    try:
        # Initialize media service
        media_service = MediaService(db)

        # Upload logo
        result = await media_service.upload_logo(
            merchant_id=current_user.merchant_id, file=file, update_merchant_record=True
        )

        return APIResponse(ok=True, data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in logo upload: {str(e)}")
        increment_counter("media_upload_errors_total", {"error": "unexpected"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during upload",
        )


@router.get(
    "/api/v1/media/logo/signed-url",
    response_model=APIResponse[SignedUrlResponse],
    summary="Get logo signed URL",
    description="Generate a signed URL for accessing the merchant's logo. Both admin and staff users can access this endpoint.",
    responses={
        200: {"description": "Signed URL generated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Logo not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_logo_signed_url(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    expiry_seconds: Optional[int] = None,
) -> APIResponse[SignedUrlResponse]:
    """
    Generate a signed URL for accessing the merchant's logo.

    - **Authentication**: Admin or staff role required
    - **Expiry**: Default 15 minutes, customizable via query parameter
    - **Access**: Private storage access via signed URL

    The signed URL provides temporary access to the private logo file.
    """
    logger.info(
        f"Signed URL request from user {current_user.user_id} for merchant {current_user.merchant_id}"
    )
    increment_counter(
        "signed_url_requests_total",
        {
            "merchant_id": str(current_user.merchant_id),
            "user_id": str(current_user.user_id),
            "role": current_user.role.value,
        },
    )

    try:
        # Initialize media service
        media_service = MediaService(db)

        # Generate signed URL
        result = await media_service.get_logo_signed_url(
            merchant_id=current_user.merchant_id, expiry_seconds=expiry_seconds
        )

        return APIResponse(ok=True, data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating signed URL: {str(e)}")
        increment_counter("signed_url_errors_total", {"error": "unexpected"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error generating signed URL",
        )


@router.delete(
    "/api/v1/media/logo",
    response_model=APIResponse[dict],
    summary="Delete merchant logo",
    description="Delete the merchant's logo from storage. Only admin users can delete logos.",
    responses={
        200: {"description": "Logo deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "Logo not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_logo(
    current_user: CurrentAdmin, db: Annotated[AsyncSession, Depends(get_db)]
) -> APIResponse[dict]:
    """
    Delete merchant logo from storage.

    - **Authentication**: Admin role required
    - **Action**: Removes logo file from storage and clears database reference
    - **Idempotent**: Safe to call even if no logo exists

    This will permanently delete the logo file and cannot be undone.
    """
    logger.info(
        f"Logo deletion request from user {current_user.user_id} for merchant {current_user.merchant_id}"
    )
    increment_counter(
        "media_deletion_requests_total",
        {
            "merchant_id": str(current_user.merchant_id),
            "user_id": str(current_user.user_id),
        },
    )

    try:
        # Initialize media service
        media_service = MediaService(db)

        # Delete logo
        success = await media_service.delete_logo(
            merchant_id=current_user.merchant_id, update_merchant_record=True
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No logo found to delete"
            )

        return APIResponse(ok=True, data={"message": "Logo deleted successfully"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting logo: {str(e)}")
        increment_counter("media_deletion_errors_total", {"error": "unexpected"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during deletion",
        )


@router.get(
    "/api/v1/media/health",
    response_model=APIResponse[dict],
    summary="Media service health check",
    description="Check the health status of the media service and its dependencies.",
)
async def media_health_check(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> APIResponse[dict]:
    """
    Perform health check for media service dependencies.

    Checks:
    - Storage bucket accessibility
    - Database connectivity

    Returns overall health status and individual component status.
    """
    try:
        media_service = MediaService(db)
        health_status = await media_service.health_check()

        return APIResponse(
            ok=health_status["status"] != "unhealthy", data=health_status
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return APIResponse(
            ok=False,
            data={
                "service": "media_service",
                "status": "unhealthy",
                "error": str(e),
                "checks": {"storage_bucket": "unknown", "database": "unknown"},
            },
        )


# Add router to main application
# This should be done in main.py or wherever routers are registered:
# app.include_router(media.router)
