"""
MetaCatalogService for managing image sync events and change detection
"""

import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from ..models.sqlalchemy_models import (
    Product,
    ProductImage,
    MetaCatalogSyncLog,
    Merchant,
)
from ..models.meta_catalog import (
    MetaCatalogSyncPayload,
    CatalogSyncAction,
    CatalogSyncTrigger,
    CatalogSyncStatus,
    MetaCatalogImageUpdate,
    IdempotencyCheck,
    LegacyEventNormalization,
)
from ..models.errors import APIError, ErrorCode, NotFoundError
from ..utils.outbox import enqueue_job
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetaCatalogService:
    """Service for managing Meta Catalog image synchronization"""

    def __init__(self, db: Session):
        self.db = db

    def detect_image_changes(
        self,
        product_id: UUID,
        merchant_id: UUID,
        primary_image_url: Optional[str] = None,
        additional_image_urls: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if product images have changed and require catalog sync
        Returns change data if sync is needed, None if no changes
        """
        product = (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.merchant_id == merchant_id)
            .first()
        )

        if not product:
            raise NotFoundError("Product", product_id)

        # Get current primary image for comparison
        current_primary = None
        if product.primary_image_id:
            current_primary = (
                self.db.query(ProductImage)
                .filter(ProductImage.id == product.primary_image_id)
                .first()
            )

        # Compare URLs to detect changes
        current_primary_url = current_primary.secure_url if current_primary else None

        # Detect primary image changes
        primary_changed = primary_image_url != current_primary_url

        if not primary_changed:
            logger.debug(
                "no_image_changes_detected",
                extra={
                    "product_id": str(product_id),
                    "merchant_id": str(merchant_id),
                    "current_url": current_primary_url,
                    "new_url": primary_image_url,
                },
            )
            return None

        # Build change data
        changes = {}
        if primary_image_url:
            changes["primary_image_url"] = primary_image_url

        if additional_image_urls:
            changes["additional_image_urls"] = additional_image_urls

        logger.info(
            "image_changes_detected",
            extra={
                "product_id": str(product_id),
                "merchant_id": str(merchant_id),
                "primary_changed": primary_changed,
                "changes_count": len(changes),
            },
        )

        return changes

    def enqueue_catalog_sync(
        self,
        product_id: UUID,
        merchant_id: UUID,
        action: CatalogSyncAction,
        changes: Dict[str, Any],
        triggered_by: CatalogSyncTrigger,
        meta_catalog_id: Optional[str] = None,
    ) -> Optional[UUID]:
        """
        Enqueue catalog sync job with idempotency checking
        Returns job ID if enqueued, None if skipped due to idempotency
        """
        # Get product details
        product = (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.merchant_id == merchant_id)
            .first()
        )

        if not product:
            raise NotFoundError("Product", product_id)

        # Get merchant for catalog configuration
        merchant = self.db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            raise NotFoundError("Merchant", merchant_id)

        # Use provided catalog_id or get from merchant configuration
        if not meta_catalog_id:
            # This would come from merchant's WhatsApp/Meta configuration
            # For now, use a placeholder - in real implementation, this would be
            # retrieved from merchant's Meta credentials
            meta_catalog_id = f"catalog_{merchant_id}"

        # Generate idempotency key
        idempotency_key = MetaCatalogSyncPayload.generate_idempotency_key(
            product_id, action, changes
        )

        # Check for existing sync with same idempotency key in last 24 hours
        idempotency_check = self._check_idempotency(idempotency_key, merchant_id)
        if idempotency_check.should_skip:
            logger.info(
                "catalog_sync_skipped_idempotent",
                extra={
                    "product_id": str(product_id),
                    "merchant_id": str(merchant_id),
                    "idempotency_key": idempotency_key,
                    "existing_sync_id": str(idempotency_check.existing_sync_id),
                },
            )
            return None

        # Create sync payload
        payload_data = MetaCatalogSyncPayload(
            action=action,
            product_id=product_id,
            retailer_id=product.retailer_id,
            meta_catalog_id=meta_catalog_id,
            changes=changes,
            idempotency_key=idempotency_key,
            triggered_by=triggered_by,
        )

        # Create sync log entry
        sync_log = MetaCatalogSyncLog(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            product_id=product_id,
            action=action.value,
            retailer_id=product.retailer_id,
            catalog_id=meta_catalog_id,
            status=CatalogSyncStatus.PENDING.value,
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.db.add(sync_log)

        # Enqueue outbox job
        job_id = self.outbox.enqueue_job(
            merchant_id=merchant_id,
            job_type="catalog_sync",
            payload=payload_data.dict(),
            max_attempts=8,
        )

        # Update sync log with job ID
        sync_log.outbox_job_id = job_id

        try:
            self.db.commit()

            logger.info(
                "catalog_sync_triggered",
                extra={
                    "event_type": "catalog_sync_triggered",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "retailer_id": product.retailer_id,
                    "action": action.value,
                    "trigger": triggered_by.value,
                    "idempotency_key": idempotency_key,
                    "image_urls_count": len(changes.get("additional_image_urls", []))
                    + (1 if "primary_image_url" in changes else 0),
                    "job_id": str(job_id),
                    "sync_log_id": str(sync_log.id),
                },
            )

            return job_id

        except IntegrityError:
            self.db.rollback()
            logger.warning(
                "catalog_sync_duplicate_avoided",
                extra={
                    "product_id": str(product_id),
                    "merchant_id": str(merchant_id),
                    "idempotency_key": idempotency_key,
                },
            )
            return None

    def handle_primary_image_change(
        self,
        product_id: UUID,
        merchant_id: UUID,
        new_primary_url: str,
        additional_urls: Optional[List[str]] = None,
    ) -> Optional[UUID]:
        """
        Handle primary image change event
        """
        # Detect changes
        changes = self.detect_image_changes(
            product_id=product_id,
            merchant_id=merchant_id,
            primary_image_url=new_primary_url,
            additional_image_urls=additional_urls,
        )

        if not changes:
            return None

        # Enqueue sync job
        return self.enqueue_catalog_sync(
            product_id=product_id,
            merchant_id=merchant_id,
            action=CatalogSyncAction.UPDATE_IMAGE,
            changes=changes,
            triggered_by=CatalogSyncTrigger.PRIMARY_CHANGE,
        )

    def handle_image_upload(
        self,
        product_id: UUID,
        merchant_id: UUID,
        uploaded_image_url: str,
        is_primary: bool = False,
    ) -> Optional[UUID]:
        """
        Handle new image upload event
        """
        if not is_primary:
            # Non-primary images don't trigger catalog sync
            return None

        changes = {"primary_image_url": uploaded_image_url}

        return self.enqueue_catalog_sync(
            product_id=product_id,
            merchant_id=merchant_id,
            action=CatalogSyncAction.UPDATE_IMAGE,
            changes=changes,
            triggered_by=CatalogSyncTrigger.IMAGE_UPLOAD,
        )

    def handle_webhook_update(
        self, product_id: UUID, merchant_id: UUID, image_metadata: Dict[str, Any]
    ) -> Optional[UUID]:
        """
        Handle webhook-triggered image update
        """
        # Extract image URL from webhook metadata
        primary_url = image_metadata.get("secure_url")
        if not primary_url:
            return None

        changes = {"primary_image_url": primary_url}

        return self.enqueue_catalog_sync(
            product_id=product_id,
            merchant_id=merchant_id,
            action=CatalogSyncAction.UPDATE_IMAGE,
            changes=changes,
            triggered_by=CatalogSyncTrigger.WEBHOOK_UPDATE,
        )

    def update_sync_status(
        self,
        sync_log_id: UUID,
        status: CatalogSyncStatus,
        response_data: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None,
        next_retry_at: Optional[datetime] = None,
    ) -> None:
        """
        Update sync log status after processing
        """
        sync_log = (
            self.db.query(MetaCatalogSyncLog)
            .filter(MetaCatalogSyncLog.id == sync_log_id)
            .first()
        )

        if not sync_log:
            raise NotFoundError("MetaCatalogSyncLog", sync_log_id)

        sync_log.status = status.value
        sync_log.updated_at = datetime.now(timezone.utc)

        if response_data:
            sync_log.response_data = response_data

        if error_details:
            sync_log.error_details = error_details

        if retry_count is not None:
            sync_log.retry_count = retry_count

        if next_retry_at:
            sync_log.next_retry_at = next_retry_at

        # Update product sync version on success
        if status == CatalogSyncStatus.SUCCESS:
            product = (
                self.db.query(Product).filter(Product.id == sync_log.product_id).first()
            )
            if product:
                product.meta_image_sync_version += 1
                product.meta_last_image_sync_at = datetime.now(timezone.utc)

        self.db.commit()

    def get_sync_logs(
        self,
        merchant_id: UUID,
        product_id: Optional[UUID] = None,
        status: Optional[CatalogSyncStatus] = None,
        limit: int = 50,
    ) -> List[MetaCatalogSyncLog]:
        """
        Get sync logs for debugging and monitoring
        """
        query = self.db.query(MetaCatalogSyncLog).filter(
            MetaCatalogSyncLog.merchant_id == merchant_id
        )

        if product_id:
            query = query.filter(MetaCatalogSyncLog.product_id == product_id)

        if status:
            query = query.filter(MetaCatalogSyncLog.status == status.value)

        return query.order_by(MetaCatalogSyncLog.created_at.desc()).limit(limit).all()

    def normalize_legacy_payload(
        self, payload: Dict[str, Any], merchant_id: UUID
    ) -> Dict[str, Any]:
        """
        Normalize legacy event payload formats
        """
        try:
            sync_payload = MetaCatalogSyncPayload(**payload)
            normalized_payload = sync_payload.normalize_legacy_shape()

            # Check if normalization occurred
            if sync_payload.changes != normalized_payload.changes:
                # Log normalization event
                normalization = LegacyEventNormalization(
                    merchant_id=merchant_id,
                    product_id=sync_payload.product_id,
                    legacy_shape=(
                        "image_url"
                        if "image_url" in payload.get("changes", {})
                        else "unknown"
                    ),
                    canonical_shape="changes.primary_image_url",
                    producer_hint="cloudinary_service_v1",  # Based on source analysis
                )

                logger.info(
                    "catalog_sync_legacy_normalized",
                    extra={
                        "event_type": "catalog_sync_legacy_normalized",
                        "merchant_id": str(merchant_id),
                        "product_id": str(sync_payload.product_id),
                        "legacy_shape": normalization.legacy_shape,
                        "canonical_shape": normalization.canonical_shape,
                        "producer_hint": normalization.producer_hint,
                    },
                )

            return normalized_payload.dict()

        except Exception as e:
            logger.error(
                "legacy_normalization_failed",
                extra={
                    "merchant_id": str(merchant_id),
                    "payload": payload,
                    "error": str(e),
                },
            )
            return payload

    def _check_idempotency(
        self, idempotency_key: str, merchant_id: UUID
    ) -> IdempotencyCheck:
        """
        Check if sync request is duplicate within TTL window
        """
        # Look for existing sync log with same idempotency key in last 24 hours
        cutoff_time = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_time = cutoff_time.replace(day=cutoff_time.day - 1)  # 24 hours ago

        existing_sync = (
            self.db.query(MetaCatalogSyncLog)
            .filter(
                MetaCatalogSyncLog.idempotency_key == idempotency_key,
                MetaCatalogSyncLog.merchant_id == merchant_id,
                MetaCatalogSyncLog.created_at >= cutoff_time,
            )
            .first()
        )

        return IdempotencyCheck(
            is_duplicate=existing_sync is not None,
            existing_sync_id=existing_sync.id if existing_sync else None,
            ttl_hours=24,
            key_generated_at=existing_sync.created_at if existing_sync else None,
        )

    def _get_catalog_config(self, merchant_id: UUID) -> Optional[str]:
        """
        Get Meta catalog configuration for merchant
        In a real implementation, this would retrieve from merchant's Meta credentials
        """
        # Placeholder implementation - would integrate with BE-015 WhatsApp credentials
        return f"catalog_{merchant_id}"


class MetaSyncReasonNormalizer:
    """Service for normalizing Meta API errors into human-readable reasons"""

    # Error reason mappings for common Meta API errors
    ERROR_REASON_MAP = {
        "auth": "Authentication failed. Reconnect catalog credentials.",
        "missing_image": "Missing image_link. Add a primary product image.",
        "price_format": "Price format invalid. Use like 123.45 NGN.",
        "policy_block": "Temporarily blocked by Meta. Try again later.",
        "image_url": "Product image is invalid or missing. Please upload a valid image and try again.",
        "invalid_parameter": "Product information contains invalid data. Please check all fields and try again.",
        "authentication": "Meta catalog connection expired. Please refresh your WhatsApp credentials.",
        "rate_limit": "Too many sync requests. Your product will be synced automatically in a few minutes.",
        "network": "Temporary connection issue with Meta. Your product will be synced automatically.",
        "validation": "Product data doesn't meet Meta catalog requirements. Please review product details.",
        "permission": "Your WhatsApp Business account doesn't have catalog access. Please check your Meta setup.",
        "catalog_not_found": "Your Meta catalog is not properly configured. Please check your WhatsApp integration.",
        "retailer_id_exists": "This product is already in your catalog. No action needed.",
        "unknown": "Sync failed due to an unexpected issue. Please try again or contact support.",
    }

    @staticmethod
    def normalize_errors(errors: List[str], status: str) -> Optional[str]:
        """
        Convert raw Meta API errors into user-friendly reason

        Args:
            errors: List of raw error messages from Meta API
            status: Current sync status (pending|syncing|synced|error)

        Returns:
            Human-readable reason string or None for non-error statuses
        """
        # No reason needed for successful or in-progress states
        if status in ("synced", "pending", "syncing"):
            return None

        # Handle empty or missing errors
        if not errors or not isinstance(errors, list):
            return MetaSyncReasonNormalizer.ERROR_REASON_MAP["unknown"]

        # Join all errors into single string for pattern matching
        error_text = " ".join(str(error).lower() for error in errors)

        try:
            # Deterministic matching heuristics (per specification)

            # Auth errors - check for OAuth code 190 or invalid oauth message
            if (
                "code" in error_text and "190" in error_text
            ) or "invalid oauth" in error_text:
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["auth"]

            # Missing image errors
            if (
                "missing" in error_text and "image_link" in error_text
            ) or "image_link" in error_text:
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["missing_image"]

            # Price format errors
            if "invalid" in error_text and "price" in error_text:
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["price_format"]

            # Policy block errors - check for code 368 or blocked message
            if (
                "code" in error_text and "368" in error_text
            ) or "blocked" in error_text:
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["policy_block"]

            # Image URL issues
            if "image_url" in error_text or (
                "image" in error_text
                and ("invalid" in error_text or "missing" in error_text)
            ):
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["image_url"]

            # Authentication issues (general)
            if (
                "authentication" in error_text
                or "unauthorized" in error_text
                or "auth" in error_text
            ):
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["authentication"]

            # Rate limiting
            if "rate" in error_text and "limit" in error_text:
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["rate_limit"]

            # Network issues
            if (
                "network" in error_text
                or "connection" in error_text
                or "timeout" in error_text
            ):
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["network"]

            # Validation errors
            if "validation" in error_text or "invalid_parameter" in error_text:
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["validation"]

            # Permission errors
            if (
                "permission" in error_text
                or "access" in error_text
                and "denied" in error_text
            ):
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["permission"]

            # Catalog not found
            if "catalog" in error_text and (
                "not found" in error_text or "missing" in error_text
            ):
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["catalog_not_found"]

            # Retailer ID exists (duplicate product)
            if "retailer_id" in error_text and (
                "exists" in error_text or "duplicate" in error_text
            ):
                return MetaSyncReasonNormalizer.ERROR_REASON_MAP["retailer_id_exists"]

            # Fallback to unknown error
            reason = MetaSyncReasonNormalizer.ERROR_REASON_MAP["unknown"]

            # Truncate reason to ≤ 140 chars as per spec
            if len(reason) > 140:
                reason = reason[:137] + "..."

            return reason

        except Exception as e:
            # If normalization fails, log and return generic message
            logger.error(
                f"Failed to normalize Meta sync errors: {str(e)}",
                extra={"error": str(e), "original_errors": errors, "status": status},
            )
            return MetaSyncReasonNormalizer.ERROR_REASON_MAP["unknown"]

    @staticmethod
    def get_reason_category(reason: Optional[str]) -> str:
        """
        Get reason category for metrics tracking

        Args:
            reason: Human-readable reason string

        Returns:
            Category name for metrics (auth|missing_image|price_format|policy_block|unknown)
        """
        if not reason:
            return "none"

        reason_lower = reason.lower()

        if "authentication" in reason_lower or "reconnect" in reason_lower:
            return "auth"
        elif "missing image" in reason_lower or "image_link" in reason_lower:
            return "missing_image"
        elif "price format" in reason_lower:
            return "price_format"
        elif "blocked" in reason_lower:
            return "policy_block"
        else:
            return "unknown"
