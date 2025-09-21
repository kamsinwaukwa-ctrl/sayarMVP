"""
Media service for handling file uploads and media operations
Provides business logic for media management with optional database updates
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, UploadFile

from ..models.media import MediaUploadResponse, SignedUrlResponse
from ..models.sqlalchemy_models import Merchant
from ..utils.storage import (
    validate_logo_file,
    upload_logo_to_storage,
    generate_signed_url,
    delete_logo_from_storage,
    ensure_bucket_exists,
)
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer

logger = get_logger(__name__)


class MediaService:
    """Service class for media operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_logo(
        self, merchant_id: UUID, file: UploadFile, update_merchant_record: bool = True
    ) -> MediaUploadResponse:
        """
        Upload merchant logo with validation and optional database update.

        Args:
            merchant_id: UUID of the merchant
            file: FastAPI UploadFile object
            update_merchant_record: Whether to update merchants.logo_url (default: True)

        Returns:
            MediaUploadResponse with upload details

        Raises:
            HTTPException: If upload fails or validation errors occur
        """
        logger.info(f"Starting logo upload for merchant {merchant_id}")
        increment_counter("media_upload_start_total", {"merchant_id": str(merchant_id)})

        with record_timer(
            "media_upload_duration_seconds", {"merchant_id": str(merchant_id)}
        ):
            try:
                # Validate merchant exists (if updating DB record)
                if update_merchant_record:
                    await self._validate_merchant_exists(merchant_id)

                # Validate the uploaded file
                normalized_filename, file_size = validate_logo_file(file)

                # Upload to Supabase Storage
                storage_path, content_type, actual_size = await upload_logo_to_storage(
                    merchant_id, file, normalized_filename
                )

                # Generate signed URL for immediate access
                signed_url, expires_at = await generate_signed_url(
                    merchant_id, normalized_filename
                )

                # Generate storage URL
                storage_url = (
                    f"/storage/v1/object/private/merchant-logos/{storage_path}"
                )

                # Optionally update merchant record with logo URL
                if update_merchant_record:
                    await self._update_merchant_logo_url(merchant_id, storage_url)

                response = MediaUploadResponse(
                    url=storage_url,
                    signed_url=signed_url,
                    filename=normalized_filename,
                    size=actual_size,
                    content_type=content_type,
                    expires_at=expires_at,
                )

                increment_counter(
                    "media_upload_success_total", {"merchant_id": str(merchant_id)}
                )
                logger.info(
                    f"Successfully uploaded logo for merchant {merchant_id}: {normalized_filename}"
                )

                return response

            except HTTPException:
                increment_counter(
                    "media_upload_failed_total",
                    {"merchant_id": str(merchant_id), "error": "validation_error"},
                )
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error uploading logo for merchant {merchant_id}: {str(e)}"
                )
                increment_counter(
                    "media_upload_failed_total",
                    {"merchant_id": str(merchant_id), "error": "unexpected_error"},
                )
                raise HTTPException(
                    status_code=500, detail="Internal server error during upload"
                )

    async def get_logo_signed_url(
        self, merchant_id: UUID, expiry_seconds: Optional[int] = None
    ) -> SignedUrlResponse:
        """
        Generate signed URL for accessing merchant logo.

        Args:
            merchant_id: UUID of the merchant
            expiry_seconds: Optional custom expiry time in seconds

        Returns:
            SignedUrlResponse with signed URL and expiry

        Raises:
            HTTPException: If signed URL generation fails
        """
        logger.info(f"Generating signed URL for merchant {merchant_id} logo")
        increment_counter(
            "signed_url_generation_start_total", {"merchant_id": str(merchant_id)}
        )

        try:
            # Validate merchant exists
            await self._validate_merchant_exists(merchant_id)

            # Try different possible logo filenames
            logo_filenames = ["logo.png", "logo.jpg", "logo.jpeg", "logo.webp"]
            signed_url = None
            expires_at = None

            for filename in logo_filenames:
                try:
                    signed_url, expires_at = await generate_signed_url(
                        merchant_id, filename, expiry_seconds
                    )
                    break  # Success, stop trying other filenames
                except HTTPException as e:
                    if e.status_code == 404:
                        continue  # Try next filename
                    raise  # Re-raise non-404 errors

            if not signed_url:
                logger.warning(f"No logo found for merchant {merchant_id}")
                raise HTTPException(
                    status_code=404, detail="No logo found for this merchant"
                )

            response = SignedUrlResponse(signed_url=signed_url, expires_at=expires_at)

            increment_counter(
                "signed_url_generated_total", {"merchant_id": str(merchant_id)}
            )
            logger.info(f"Successfully generated signed URL for merchant {merchant_id}")

            return response

        except HTTPException:
            increment_counter(
                "signed_url_generation_failed_total", {"merchant_id": str(merchant_id)}
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error generating signed URL for merchant {merchant_id}: {str(e)}"
            )
            increment_counter(
                "signed_url_generation_failed_total", {"merchant_id": str(merchant_id)}
            )
            raise HTTPException(
                status_code=500, detail="Internal server error generating signed URL"
            )

    async def delete_logo(
        self, merchant_id: UUID, update_merchant_record: bool = True
    ) -> bool:
        """
        Delete merchant logo from storage and optionally update database.

        Args:
            merchant_id: UUID of the merchant
            update_merchant_record: Whether to clear merchants.logo_url (default: True)

        Returns:
            True if deletion was successful

        Raises:
            HTTPException: If deletion fails or merchant not found
        """
        logger.info(f"Deleting logo for merchant {merchant_id}")
        increment_counter(
            "media_deletion_start_total", {"merchant_id": str(merchant_id)}
        )

        try:
            # Validate merchant exists (if updating DB record)
            if update_merchant_record:
                await self._validate_merchant_exists(merchant_id)

            # Try to delete all possible logo files
            logo_filenames = ["logo.png", "logo.jpg", "logo.jpeg", "logo.webp"]
            deletion_success = False

            for filename in logo_filenames:
                if await delete_logo_from_storage(merchant_id, filename):
                    deletion_success = True

            # Optionally clear merchant logo URL
            if update_merchant_record and deletion_success:
                await self._update_merchant_logo_url(merchant_id, None)

            if deletion_success:
                increment_counter(
                    "media_deletion_success_total", {"merchant_id": str(merchant_id)}
                )
                logger.info(f"Successfully deleted logo for merchant {merchant_id}")
            else:
                logger.warning(f"No logo found to delete for merchant {merchant_id}")

            return deletion_success

        except HTTPException:
            increment_counter(
                "media_deletion_failed_total", {"merchant_id": str(merchant_id)}
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error deleting logo for merchant {merchant_id}: {str(e)}"
            )
            increment_counter(
                "media_deletion_failed_total", {"merchant_id": str(merchant_id)}
            )
            raise HTTPException(
                status_code=500, detail="Internal server error during deletion"
            )

    async def _validate_merchant_exists(self, merchant_id: UUID) -> None:
        """
        Validate that merchant exists in the database.

        Args:
            merchant_id: UUID of the merchant to validate

        Raises:
            HTTPException: If merchant doesn't exist
        """
        result = await self.db.execute(
            select(Merchant.id).where(Merchant.id == merchant_id)
        )
        merchant = result.scalar_one_or_none()

        if not merchant:
            logger.warning(f"Merchant not found: {merchant_id}")
            raise HTTPException(status_code=404, detail="Merchant not found")

    async def _update_merchant_logo_url(
        self, merchant_id: UUID, logo_url: Optional[str]
    ) -> None:
        """
        Update merchant's logo_url in the database.

        Args:
            merchant_id: UUID of the merchant
            logo_url: New logo URL or None to clear it
        """
        try:
            # Check if logo_url column exists (it might not if migration hasn't been run)
            await self.db.execute(
                update(Merchant)
                .where(Merchant.id == merchant_id)
                .values(logo_url=logo_url, updated_at=datetime.utcnow())
            )
            await self.db.commit()

            action = "updated" if logo_url else "cleared"
            logger.info(f"Successfully {action} logo_url for merchant {merchant_id}")

        except Exception as e:
            await self.db.rollback()
            # Log the error but don't fail the operation if it's just the DB update
            logger.warning(
                f"Failed to update merchant logo_url (this may be expected if migration hasn't been run): {str(e)}"
            )

    async def health_check(self) -> dict:
        """
        Perform health check for media service dependencies.

        Returns:
            Dictionary with health check results
        """
        logger.info("Performing media service health check")

        health_status = {
            "service": "media_service",
            "status": "healthy",
            "checks": {"storage_bucket": "unknown", "database": "unknown"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Check storage bucket accessibility
        try:
            if ensure_bucket_exists():
                health_status["checks"]["storage_bucket"] = "healthy"
            else:
                health_status["checks"]["storage_bucket"] = "unhealthy"
                health_status["status"] = "degraded"
        except Exception as e:
            logger.error(f"Storage health check failed: {str(e)}")
            health_status["checks"]["storage_bucket"] = "unhealthy"
            health_status["status"] = "degraded"

        # Check database connectivity
        try:
            await self.db.execute(select(1))
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            health_status["checks"]["database"] = "unhealthy"
            health_status["status"] = "unhealthy"

        return health_status
