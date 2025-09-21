"""
CloudinaryService for managing product images with business logic
"""

import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from ..models.sqlalchemy_models import ProductImage, Product
from ..models.api import (
    ProductImageResponse,
    CloudinaryWebhookPayload,
    SetPrimaryImageResponse,
)
from ..models.cloudinary import (
    PresetProfile,
    ProductImageWithVariantsResponse,
    ImageVariant,
    ImageDimensions,
    UploadWithPresetsRequest,
)
from ..models.errors import APIError, ErrorCode, NotFoundError
from ..integrations.cloudinary_client import CloudinaryClient, CloudinaryConfig
from ..utils.outbox import OutboxUtils
from .meta_catalog_service import MetaCatalogService
from ..models.meta_catalog import CatalogSyncTrigger
from ..config.cloudinary_presets import (
    get_profile_by_id,
    get_all_presets_for_profile,
    PRESETS_VERSION,
)


class CloudinaryService:
    """Service for managing product images with Cloudinary integration"""

    def __init__(self, db: Session):
        self.db = db
        self.cloudinary_client = CloudinaryClient()
        self.outbox = OutboxUtils(db)
        self.catalog_service = MetaCatalogService(db)

    def health_check(self) -> Dict[str, Any]:
        """
        Check Cloudinary platform health
        Returns configuration status and verification timestamp
        """
        try:
            health_data = self.cloudinary_client.verify_health()
            return {
                "configured": health_data["configured"],
                "cloud_name": health_data["cloud_name"],
                "verified_at": datetime.fromtimestamp(health_data["verified_at"]),
            }
        except APIError as e:
            if e.code == ErrorCode.CLOUDINARY_NOT_CONFIGURED:
                return {"configured": False, "cloud_name": None, "verified_at": None}
            raise

    def upload_product_image_with_presets(
        self,
        product_id: UUID,
        merchant_id: UUID,
        file_content: bytes,
        filename: str,
        request: UploadWithPresetsRequest,
        webhook_url: Optional[str] = None,
    ) -> ProductImageWithVariantsResponse:
        """
        Upload product image with preset-based transformations
        Returns enhanced response with all variants
        """
        # Verify product exists and belongs to merchant
        product = (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.merchant_id == merchant_id)
            .first()
        )

        if not product:
            raise NotFoundError("Product", product_id)

        try:
            # Upload to Cloudinary with presets
            upload_result = self.cloudinary_client.upload_image_with_presets(
                file_content=file_content,
                merchant_id=str(merchant_id),
                product_id=str(product_id),
                filename=filename,
                preset_profile=request.preset_profile,
                webhook_url=webhook_url,
            )

            # Create database record with preset information
            image_id = uuid.uuid4()

            # Convert variants to JSON for database storage
            variants_json = {}
            for variant_name, variant in upload_result["variants"].items():
                variants_json[variant_name] = {
                    "url": variant.url,
                    "preset_id": variant.preset_id,
                    "file_size_kb": variant.file_size_kb,
                    "dimensions": (
                        {
                            "width": variant.dimensions.width,
                            "height": variant.dimensions.height,
                        }
                        if variant.dimensions
                        else None
                    ),
                    "format": variant.format,
                    "quality_score": variant.quality_score,
                    "processing_time_ms": variant.processing_time_ms,
                }

            # Create optimization stats
            optimization_stats = {
                "preset_profile": request.preset_profile.value,
                "preset_version": PRESETS_VERSION,
                "eager_variants_count": len(
                    [v for v in upload_result["variants"].values() if v.file_size_kb]
                ),
                "on_demand_variants_count": len(
                    [
                        v
                        for v in upload_result["variants"].values()
                        if not v.file_size_kb
                    ]
                ),
                "upload_timestamp": datetime.utcnow().isoformat(),
            }

            # Get main variant URL for backward compatibility
            main_url = None
            thumbnail_url = None
            if "main" in upload_result["variants"]:
                main_url = upload_result["variants"]["main"].url
            if "thumb" in upload_result["variants"]:
                thumbnail_url = upload_result["variants"]["thumb"].url

            product_image = ProductImage(
                id=image_id,
                product_id=product_id,
                merchant_id=merchant_id,
                cloudinary_public_id=upload_result["public_id"],
                secure_url=main_url or upload_result.get("secure_url", ""),
                thumbnail_url=thumbnail_url,
                width=upload_result.get("width"),
                height=upload_result.get("height"),
                format=upload_result.get("format"),
                bytes=upload_result.get("bytes"),
                is_primary=request.is_primary,
                alt_text=request.alt_text,
                upload_status="uploading",  # Will be updated by webhook
                cloudinary_version=upload_result.get("version"),
                preset_profile=request.preset_profile.value,
                variants=variants_json,
                optimization_stats=optimization_stats,
                preset_version=PRESETS_VERSION,
            )

            self.db.add(product_image)

            # Handle primary image logic
            if request.is_primary:
                # Unset any existing primary image
                self.db.query(ProductImage).filter(
                    ProductImage.product_id == product_id,
                    ProductImage.is_primary == True,
                    ProductImage.id != image_id,
                ).update({"is_primary": False})

                # Update product primary_image_id
                product.primary_image_id = image_id

            self.db.commit()

            # If primary image, trigger catalog sync using main variant
            catalog_sync_triggered = False
            if request.is_primary and main_url:
                try:
                    # Verify main URL exists before syncing
                    if self.cloudinary_client.verify_variant_url_exists(main_url):
                        job_id = self.catalog_service.handle_image_upload(
                            product_id=product_id,
                            merchant_id=merchant_id,
                            uploaded_image_url=main_url,
                            is_primary=True,
                        )
                        catalog_sync_triggered = job_id is not None
                    else:
                        # Delay sync if URL not ready
                        self.outbox.add_job(
                            job_type="delayed_catalog_sync",
                            payload={
                                "product_id": str(product_id),
                                "merchant_id": str(merchant_id),
                                "image_url": main_url,
                                "retry_count": 0,
                            },
                            delay_seconds=30,
                        )
                except Exception:
                    # Don't fail upload if catalog sync queueing fails
                    pass

            # Update preset statistics
            try:
                self._update_preset_statistics(
                    merchant_id=merchant_id,
                    variants=upload_result["variants"],
                    processing_time_ms=optimization_stats.get(
                        "total_processing_time_ms", 0
                    ),
                )
            except Exception:
                # Don't fail upload if stats update fails
                pass

            return ProductImageWithVariantsResponse(
                id=image_id,
                product_id=product_id,
                cloudinary_public_id=upload_result["public_id"],
                preset_profile=request.preset_profile,
                variants=upload_result["variants"],
                is_primary=request.is_primary,
                alt_text=request.alt_text,
                upload_status="uploading",
                preset_version=PRESETS_VERSION,
                optimization_stats=optimization_stats,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        except IntegrityError:
            self.db.rollback()
            raise APIError(
                code=ErrorCode.DUPLICATE_RESOURCE,
                message="Image with this public_id already exists",
            )
        except Exception:
            self.db.rollback()
            raise

    def upload_product_image(
        self,
        product_id: UUID,
        merchant_id: UUID,
        file_content: bytes,
        filename: str,
        is_primary: bool = False,
        alt_text: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> ProductImageResponse:
        """
        Upload product image to Cloudinary and save metadata to database
        """
        # Verify product exists and belongs to merchant
        product = (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.merchant_id == merchant_id)
            .first()
        )

        if not product:
            raise NotFoundError("Product", product_id)

        try:
            # Upload to Cloudinary
            upload_result = self.cloudinary_client.upload_image(
                file_content=file_content,
                merchant_id=str(merchant_id),
                product_id=str(product_id),
                filename=filename,
                webhook_url=webhook_url,
            )

            # Create database record
            image_id = uuid.uuid4()
            product_image = ProductImage(
                id=image_id,
                product_id=product_id,
                merchant_id=merchant_id,
                cloudinary_public_id=upload_result["public_id"],
                secure_url=upload_result["secure_url"],
                thumbnail_url=upload_result.get("thumbnail_url"),
                width=upload_result.get("width"),
                height=upload_result.get("height"),
                format=upload_result.get("format"),
                bytes=upload_result.get("bytes"),
                is_primary=is_primary,
                alt_text=alt_text,
                upload_status="uploading",  # Will be updated by webhook
                cloudinary_version=upload_result.get("version"),
            )

            self.db.add(product_image)

            # Handle primary image logic
            if is_primary:
                # Unset any existing primary image
                self.db.query(ProductImage).filter(
                    ProductImage.product_id == product_id,
                    ProductImage.is_primary == True,
                    ProductImage.id != image_id,
                ).update({"is_primary": False})

                # Update product primary_image_id
                product.primary_image_id = image_id

            self.db.commit()

            # If primary image, trigger catalog sync
            catalog_sync_triggered = False
            if is_primary:
                try:
                    job_id = self.catalog_service.handle_image_upload(
                        product_id=product_id,
                        merchant_id=merchant_id,
                        uploaded_image_url=upload_result["secure_url"],
                        is_primary=True,
                    )
                    catalog_sync_triggered = job_id is not None
                except Exception:
                    # Don't fail upload if catalog sync queueing fails
                    pass

            return ProductImageResponse(
                id=image_id,
                product_id=product_id,
                cloudinary_public_id=upload_result["public_id"],
                secure_url=upload_result["secure_url"],
                thumbnail_url=upload_result.get("thumbnail_url"),
                width=upload_result.get("width"),
                height=upload_result.get("height"),
                format=upload_result.get("format"),
                bytes=upload_result.get("bytes"),
                is_primary=is_primary,
                alt_text=alt_text,
                upload_status="uploading",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        except IntegrityError:
            self.db.rollback()
            raise APIError(
                code=ErrorCode.DUPLICATE_RESOURCE,
                message="Image with this public_id already exists",
            )
        except Exception:
            self.db.rollback()
            raise

    def delete_product_image(self, image_id: UUID, merchant_id: UUID) -> bool:
        """
        Delete product image from both database and Cloudinary
        """
        # Find image and verify ownership
        image = (
            self.db.query(ProductImage)
            .filter(
                ProductImage.id == image_id, ProductImage.merchant_id == merchant_id
            )
            .first()
        )

        if not image:
            raise NotFoundError("ProductImage", image_id)

        was_primary = image.is_primary
        product_id = image.product_id
        public_id = image.cloudinary_public_id

        try:
            # Delete from Cloudinary
            self.cloudinary_client.delete_image(public_id)

            # Delete from database
            self.db.delete(image)

            # If this was the primary image, clear product primary_image_id
            if was_primary:
                product = (
                    self.db.query(Product).filter(Product.id == product_id).first()
                )
                if product:
                    product.primary_image_id = None

            self.db.commit()

            # If primary image was deleted, trigger catalog sync to clear image
            if was_primary:
                try:
                    # Find next available image to set as primary, or None if no images
                    next_image = (
                        self.db.query(ProductImage)
                        .filter(
                            ProductImage.product_id == product_id,
                            ProductImage.upload_status == "completed",
                        )
                        .first()
                    )

                    if next_image:
                        next_image.is_primary = True
                        product = (
                            self.db.query(Product)
                            .filter(Product.id == product_id)
                            .first()
                        )
                        if product:
                            product.primary_image_id = next_image.id
                        self.db.commit()

                        # Trigger sync with new primary image
                        self.catalog_service.handle_primary_image_change(
                            product_id=product_id,
                            merchant_id=merchant_id,
                            new_primary_url=next_image.secure_url,
                        )
                    else:
                        # No images left, sync with empty image
                        self.catalog_service.handle_primary_image_change(
                            product_id=product_id,
                            merchant_id=merchant_id,
                            new_primary_url="",  # Empty URL indicates no image
                        )
                except Exception:
                    # Don't fail deletion if catalog sync queueing fails
                    pass

            return True

        except Exception:
            self.db.rollback()
            raise

    def set_primary_image(
        self, image_id: UUID, product_id: UUID, merchant_id: UUID
    ) -> SetPrimaryImageResponse:
        """
        Set an image as the primary image for a product
        """
        # Verify image exists and belongs to merchant/product
        image = (
            self.db.query(ProductImage)
            .filter(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
                ProductImage.merchant_id == merchant_id,
                ProductImage.upload_status == "completed",
            )
            .first()
        )

        if not image:
            raise NotFoundError("ProductImage", image_id)

        try:
            # Unset any existing primary image for this product
            self.db.query(ProductImage).filter(
                ProductImage.product_id == product_id,
                ProductImage.is_primary == True,
                ProductImage.id != image_id,
            ).update({"is_primary": False})

            # Set this image as primary
            image.is_primary = True

            # Update product primary_image_id
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if product:
                product.primary_image_id = image_id

            self.db.commit()

            # Trigger catalog sync with new primary image
            catalog_sync_triggered = False
            try:
                job_id = self.catalog_service.handle_primary_image_change(
                    product_id=product_id,
                    merchant_id=merchant_id,
                    new_primary_url=image.secure_url,
                )
                catalog_sync_triggered = job_id is not None
            except Exception:
                # Don't fail primary image setting if catalog sync queueing fails
                pass

            return SetPrimaryImageResponse(
                id=image_id,
                is_primary=True,
                catalog_sync_triggered=catalog_sync_triggered,
            )

        except Exception:
            self.db.rollback()
            raise

    def process_webhook(
        self,
        payload: CloudinaryWebhookPayload,
        signature: str,
        timestamp: str,
        raw_body: bytes,
    ) -> Dict[str, str]:
        """
        Process Cloudinary webhook callback
        Verify signature and update image metadata
        """
        # Verify webhook signature
        if not self.cloudinary_client.verify_webhook_signature(
            raw_body, signature, timestamp
        ):
            raise APIError(
                code=ErrorCode.WEBHOOK_SIGNATURE_INVALID,
                message="Invalid webhook signature or timestamp",
            )

        # Find image by public_id
        image = (
            self.db.query(ProductImage)
            .filter(ProductImage.cloudinary_public_id == payload.public_id)
            .first()
        )

        if not image:
            # Image not found - might be a different notification or test
            return {"success": True, "message": "Image not found, ignoring webhook"}

        try:
            # Update image metadata based on webhook type
            if payload.notification_type == "upload":
                # Update with final metadata
                image.upload_status = "completed"
                image.width = payload.width
                image.height = payload.height
                image.format = payload.format
                image.bytes = payload.bytes
                image.cloudinary_version = payload.version

                # Update URLs from eager transformations if available
                if payload.eager:
                    for eager in payload.eager:
                        transformation = eager.get("transformation", "")
                        if "c_limit,w_1600,h_1600" in transformation:
                            image.secure_url = eager.get("secure_url", image.secure_url)
                        elif "c_fill,w_600,h_600" in transformation:
                            image.thumbnail_url = eager.get("secure_url")

                # If this is the primary image, trigger catalog sync
                if image.is_primary:
                    try:
                        self.catalog_service.handle_webhook_update(
                            product_id=image.product_id,
                            merchant_id=image.merchant_id,
                            image_metadata={
                                "secure_url": image.secure_url,
                                "width": payload.width,
                                "height": payload.height,
                                "format": payload.format,
                                "bytes": payload.bytes,
                                "version": payload.version,
                            },
                        )
                    except Exception:
                        # Don't fail webhook processing if catalog sync queueing fails
                        pass

            elif payload.notification_type == "destroy":
                # Mark as deleted
                image.upload_status = "deleted"

            self.db.commit()

            return {"success": True, "message": "Webhook processed"}

        except Exception:
            self.db.rollback()
            raise

    def get_product_images(
        self, product_id: UUID, merchant_id: UUID
    ) -> List[ProductImageResponse]:
        """
        Get all images for a product
        """
        images = (
            self.db.query(ProductImage)
            .filter(
                ProductImage.product_id == product_id,
                ProductImage.merchant_id == merchant_id,
                ProductImage.upload_status != "deleted",
            )
            .order_by(ProductImage.is_primary.desc(), ProductImage.created_at.desc())
            .all()
        )

        return [
            ProductImageResponse(
                id=img.id,
                product_id=img.product_id,
                cloudinary_public_id=img.cloudinary_public_id,
                secure_url=img.secure_url,
                thumbnail_url=img.thumbnail_url,
                width=img.width,
                height=img.height,
                format=img.format,
                bytes=img.bytes,
                is_primary=img.is_primary,
                alt_text=img.alt_text,
                upload_status=img.upload_status,
                created_at=img.created_at,
                updated_at=img.updated_at,
            )
            for img in images
        ]

    def _update_preset_statistics(
        self,
        merchant_id: UUID,
        variants: Dict[str, ImageVariant],
        processing_time_ms: int = 0,
    ) -> None:
        """
        Update preset usage statistics in the database
        """
        try:
            for variant_name, variant in variants.items():
                if variant.file_size_kb and variant.processing_time_ms:
                    # Call the database function to update stats
                    self.db.execute(
                        "SELECT update_preset_stats(%s, %s, %s, %s, %s)",
                        (
                            str(merchant_id),
                            variant.preset_id,
                            variant.file_size_kb,
                            variant.processing_time_ms
                            or 500,  # Default if not provided
                            variant.quality_score or 75,  # Default if not provided
                        ),
                    )
            self.db.commit()
        except Exception:
            # Don't fail the main operation if stats update fails
            self.db.rollback()

    def get_preset_statistics(
        self, merchant_id: UUID, preset_id: Optional[str] = None, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get preset usage statistics for a merchant
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = """
        SELECT
            preset_id,
            usage_count,
            avg_file_size_kb,
            avg_processing_time_ms,
            quality_score_avg,
            last_used_at
        FROM cloudinary_preset_stats
        WHERE merchant_id = %s
        AND (last_used_at >= %s OR last_used_at IS NULL)
        """

        params = [str(merchant_id), cutoff_date]

        if preset_id:
            query += " AND preset_id = %s"
            params.append(preset_id)

        query += " ORDER BY usage_count DESC, last_used_at DESC"

        result = self.db.execute(query, params).fetchall()

        return [
            {
                "preset_id": row[0],
                "usage_count": row[1],
                "avg_file_size_kb": row[2],
                "avg_processing_time_ms": row[3],
                "quality_score_avg": float(row[4]) if row[4] else None,
                "last_used_at": row[5].isoformat() if row[5] else None,
            }
            for row in result
        ]

    def regenerate_variants_for_profile(
        self, image_id: UUID, merchant_id: UUID, new_profile: PresetProfile
    ) -> ProductImageWithVariantsResponse:
        """
        Regenerate variants for an existing image with a new preset profile
        """
        # Find the image
        image = (
            self.db.query(ProductImage)
            .filter(
                ProductImage.id == image_id, ProductImage.merchant_id == merchant_id
            )
            .first()
        )

        if not image:
            raise NotFoundError("ProductImage", image_id)

        try:
            # Generate new variants
            all_presets = get_all_presets_for_profile(new_profile)
            new_variants = {}

            for variant_name, preset in all_presets.items():
                variant_url = self.cloudinary_client.generate_variant_url(
                    public_id=image.cloudinary_public_id,
                    transformation=preset.transformation,
                    version=image.cloudinary_version,
                )

                new_variants[variant_name] = ImageVariant(
                    url=variant_url, preset_id=preset.id
                )

            # Convert to JSON for database storage
            variants_json = {}
            for variant_name, variant in new_variants.items():
                variants_json[variant_name] = {
                    "url": variant.url,
                    "preset_id": variant.preset_id,
                    "file_size_kb": variant.file_size_kb,
                    "dimensions": (
                        {
                            "width": variant.dimensions.width,
                            "height": variant.dimensions.height,
                        }
                        if variant.dimensions
                        else None
                    ),
                    "format": variant.format,
                    "quality_score": variant.quality_score,
                    "processing_time_ms": variant.processing_time_ms,
                }

            # Update database record
            optimization_stats = image.optimization_stats or {}
            optimization_stats.update(
                {
                    "profile_updated_at": datetime.utcnow().isoformat(),
                    "previous_profile": image.preset_profile,
                    "regeneration_reason": "profile_change",
                }
            )

            image.preset_profile = new_profile.value
            image.variants = variants_json
            image.optimization_stats = optimization_stats
            image.preset_version = PRESETS_VERSION

            # Update main URLs for backward compatibility
            if "main" in new_variants:
                image.secure_url = new_variants["main"].url
            if "thumb" in new_variants:
                image.thumbnail_url = new_variants["thumb"].url

            self.db.commit()

            # If this is a primary image, trigger catalog sync
            if image.is_primary and "main" in new_variants:
                try:
                    self.catalog_service.handle_primary_image_change(
                        product_id=image.product_id,
                        merchant_id=merchant_id,
                        new_primary_url=new_variants["main"].url,
                    )
                except Exception:
                    # Don't fail if catalog sync fails
                    pass

            return ProductImageWithVariantsResponse(
                id=image.id,
                product_id=image.product_id,
                cloudinary_public_id=image.cloudinary_public_id,
                preset_profile=new_profile,
                variants=new_variants,
                is_primary=image.is_primary,
                alt_text=image.alt_text,
                upload_status=image.upload_status,
                preset_version=PRESETS_VERSION,
                optimization_stats=optimization_stats,
                created_at=image.created_at,
                updated_at=datetime.utcnow(),
            )

        except Exception:
            self.db.rollback()
            raise
