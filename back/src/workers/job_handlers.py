"""
Job handlers for outbox worker.
"""
import os
from typing import Any, Dict, Callable, Optional
from datetime import datetime
from uuid import UUID

from src.models.outbox import JobType
from src.models.errors import RetryableError, RateLimitedError
from src.utils.wa_rate_limiter import check_wa_rate_limit
from src.utils.logger import get_logger
from src.integrations.whatsapp import send_whatsapp_message
from src.integrations.meta_catalog import MetaCatalogClient, MetaCatalogConfig, MetaCatalogRateLimitError
from src.models.meta_catalog import MetaSyncStatus
from src.utils.metrics import increment_counter, record_timer

logger = get_logger(__name__)

async def handle_wa_send(
    merchant_id: str,
    payload: Dict[str, Any],
    wa_rate_limit_per_hour: int = 1000
) -> None:
    """Handle WhatsApp message sending with rate limiting."""
    # Check rate limit before sending
    try:
        await check_wa_rate_limit(merchant_id, wa_rate_limit_per_hour)
    except RateLimitedError as e:
        # If rate limited, reschedule the job
        logger.info(
            "wa_send_rescheduled",
            extra={
                "merchant_id": merchant_id,
                "next_run_at": e.details["reset_time"]
            }
        )
        # Re-raise as RetryableError to trigger job rescheduling
        raise RetryableError(
            message=e.message,
            next_run_at=datetime.fromisoformat(e.details["reset_time"])
        )
    
    # Rate limit passed, send the message
    await send_whatsapp_message(
        to=payload["to"],
        message_type=payload["type"],
        content=payload["content"]
    )

async def handle_catalog_sync(
    merchant_id: str,
    payload: Dict[str, Any]
) -> None:
    """Handle Meta Commerce Catalog synchronization with image update support."""
    start_time = datetime.now()

    try:
        # Import required services and models
        from ..database.connection import get_db_session
        from ..services.meta_catalog_service import MetaCatalogService
        from ..integrations.meta_catalog import MetaCatalogClient
        from ..models.meta_catalog import (
            MetaCatalogSyncPayload,
            CatalogSyncAction,
            CatalogSyncStatus,
            MetaCatalogImageUpdate,
            MetaCatalogConfig
        )
        from ..models.sqlalchemy_models import Product, Merchant, MetaCatalogSyncLog
        from sqlalchemy import select

        # Get database session
        db = next(get_db_session())

        try:
            # Initialize services
            catalog_service = MetaCatalogService(db)
            meta_client = MetaCatalogClient()

            # Normalize legacy payload format
            normalized_payload = catalog_service.normalize_legacy_payload(
                payload, UUID(merchant_id)
            )

            # Parse normalized payload
            sync_payload = MetaCatalogSyncPayload(**normalized_payload)

            logger.info(
                "catalog_sync_start",
                extra={
                    "event_type": "catalog_sync_start",
                    "merchant_id": merchant_id,
                    "product_id": str(sync_payload.product_id),
                    "retailer_id": sync_payload.retailer_id,
                    "action": sync_payload.action.value,
                    "trigger": sync_payload.triggered_by.value,
                    "idempotency_key": sync_payload.idempotency_key
                }
            )

            # Get merchant configuration for Meta catalog access
            merchant = db.query(Merchant).filter(Merchant.id == UUID(merchant_id)).first()
            if not merchant:
                raise ValueError(f"Merchant not found: {merchant_id}")

            # Load Meta credentials from BE-019 integration service
            from ..services.product_service import ProductService
            product_service = ProductService(db)
            meta_credentials = await product_service.load_meta_credentials_for_worker(UUID(merchant_id))

            if not meta_credentials or not meta_credentials.is_usable():
                # Log error and update sync status to indicate missing credentials
                error_message = "Meta credentials not configured or invalid"
                logger.error(
                    "catalog_sync_no_credentials",
                    extra={
                        "event_type": "catalog_sync_error",
                        "merchant_id": merchant_id,
                        "product_id": str(sync_payload.product_id),
                        "retailer_id": sync_payload.retailer_id,
                        "error": error_message,
                        "error_code": "no_catalog_credentials"
                    }
                )

                # Update product sync status to indicate credential error
                product = db.query(Product).filter(
                    Product.id == sync_payload.product_id,
                    Product.merchant_id == UUID(merchant_id)
                ).first()

                if product:
                    product.meta_sync_status = "error"
                    product.meta_sync_errors = {"error": error_message, "error_code": "no_catalog_credentials"}
                    db.commit()

                return  # Skip sync if no valid credentials

            # Build Meta catalog config from loaded credentials
            config = MetaCatalogConfig(
                catalog_id=meta_credentials.catalog_id,
                access_token=meta_credentials.system_user_token,
                app_id=meta_credentials.app_id,
                app_secret=os.getenv("META_APP_SECRET", "")
            )

            # Find existing sync log entry
            sync_log = db.query(MetaCatalogSyncLog).filter(
                MetaCatalogSyncLog.idempotency_key == sync_payload.idempotency_key,
                MetaCatalogSyncLog.merchant_id == UUID(merchant_id)
            ).first()

            result = None

            # Handle different sync actions
            if sync_payload.action == CatalogSyncAction.UPDATE_IMAGE:
                # Extract image data from changes
                changes = sync_payload.changes
                primary_image_url = changes.get("primary_image_url")
                additional_urls = changes.get("additional_image_urls", [])

                if not primary_image_url:
                    raise ValueError("Primary image URL required for image update")

                # Create image update data
                image_data = MetaCatalogImageUpdate(
                    image_url=primary_image_url,
                    additional_image_urls=additional_urls
                )

                # Update product images via Meta Catalog API
                result = await meta_client.update_product_images(
                    catalog_id=config.catalog_id,
                    retailer_id=sync_payload.retailer_id,
                    image_data=image_data,
                    config=config
                )

            elif sync_payload.action == CatalogSyncAction.CREATE:
                # Get product details for full catalog creation
                product = db.query(Product).filter(
                    Product.id == sync_payload.product_id,
                    Product.merchant_id == UUID(merchant_id)
                ).first()

                if not product:
                    raise ValueError(f"Product not found: {sync_payload.product_id}")

                # Convert to Meta catalog format
                meta_product = meta_client.format_product_for_meta(
                    product,
                    {"storefront_url": "https://example.com", "brand_name": merchant.name}
                )

                result = await meta_client.create_product(
                    config.catalog_id, meta_product, config
                )

            elif sync_payload.action == CatalogSyncAction.UPDATE:
                # Get product details for full catalog update
                product = db.query(Product).filter(
                    Product.id == sync_payload.product_id,
                    Product.merchant_id == UUID(merchant_id)
                ).first()

                if not product:
                    raise ValueError(f"Product not found: {sync_payload.product_id}")

                # Convert to Meta catalog format
                meta_product = meta_client.format_product_for_meta(
                    product,
                    {"storefront_url": "https://example.com", "brand_name": merchant.name}
                )

                result = await meta_client.update_product(
                    config.catalog_id, sync_payload.retailer_id, meta_product, config
                )

            elif sync_payload.action == CatalogSyncAction.DELETE:
                result = await meta_client.delete_product(
                    config.catalog_id, sync_payload.retailer_id, config
                )

            else:
                raise ValueError(f"Unknown catalog sync action: {sync_payload.action}")

            # Update idempotency key in result
            result.idempotency_key = sync_payload.idempotency_key

            # Update sync log status
            if sync_log:
                if result.success:
                    catalog_service.update_sync_status(
                        sync_log.id,
                        CatalogSyncStatus.SUCCESS,
                        response_data={"meta_product_id": result.meta_product_id},
                        retry_count=sync_log.retry_count
                    )
                else:
                    # Determine if error is retryable
                    is_retryable = True
                    if result.errors:
                        error_msg = " ".join(result.errors)
                        is_retryable = meta_client.classify_error(error_msg)

                    if result.rate_limited or is_retryable:
                        catalog_service.update_sync_status(
                            sync_log.id,
                            CatalogSyncStatus.RATE_LIMITED if result.rate_limited else CatalogSyncStatus.FAILED,
                            error_details={
                                "errors": result.errors,
                                "retryable": is_retryable,
                                "rate_limited": result.rate_limited
                            },
                            retry_count=sync_log.retry_count + 1,
                            next_retry_at=result.retry_after
                        )
                    else:
                        # Permanent failure
                        catalog_service.update_sync_status(
                            sync_log.id,
                            CatalogSyncStatus.FAILED,
                            error_details={
                                "errors": result.errors,
                                "retryable": False,
                                "permanent_failure": True
                            }
                        )

            # Update product meta_sync_status, meta_sync_errors, and meta_sync_reason in same transaction
            from ..services.meta_catalog_service import MetaSyncReasonNormalizer
            from sqlalchemy import update

            if result.success:
                # Update product to synced status
                update_stmt = (
                    update(Product)
                    .where(Product.id == sync_payload.product_id)
                    .values(
                        meta_sync_status=MetaSyncStatus.SYNCED.value,
                        meta_sync_errors=None,
                        meta_sync_reason=None,
                        meta_last_synced_at=datetime.now()
                    )
                )
                db.execute(update_stmt)
                db.commit()

                logger.info(
                    "meta_sync_reason_normalized",
                    extra={
                        "event_type": "meta_sync_reason_normalized",
                        "merchant_id": merchant_id,
                        "product_id": str(sync_payload.product_id),
                        "original_errors": None,
                        "normalized_reason": None,
                        "status": MetaSyncStatus.SYNCED.value
                    }
                )
            else:
                # Normalize errors to human-readable reason
                sync_reason = MetaSyncReasonNormalizer.normalize_errors(
                    result.errors or [],
                    MetaSyncStatus.ERROR.value
                )

                # Update product to error status
                update_stmt = (
                    update(Product)
                    .where(Product.id == sync_payload.product_id)
                    .values(
                        meta_sync_status=MetaSyncStatus.ERROR.value,
                        meta_sync_errors=result.errors or [],
                        meta_sync_reason=sync_reason
                    )
                )
                db.execute(update_stmt)
                db.commit()

                logger.info(
                    "meta_sync_reason_normalized",
                    extra={
                        "event_type": "meta_sync_reason_normalized",
                        "merchant_id": merchant_id,
                        "product_id": str(sync_payload.product_id),
                        "original_errors": result.errors or [],
                        "normalized_reason": sync_reason,
                        "status": MetaSyncStatus.ERROR.value
                    }
                )

            # Handle sync result
            if result.success:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                logger.info(
                    "catalog_sync_success",
                    extra={
                        "event_type": "catalog_sync_success",
                        "merchant_id": merchant_id,
                        "product_id": str(sync_payload.product_id),
                        "retailer_id": sync_payload.retailer_id,
                        "action": sync_payload.action.value,
                        "duration_ms": duration_ms,
                        "meta_product_id": result.meta_product_id,
                        "idempotency_key": sync_payload.idempotency_key
                    }
                )

                # Record success metrics
                increment_counter("catalog_sync_success_total", tags={
                    "merchant_id": merchant_id,
                    "action": sync_payload.action.value
                })
                record_timer("catalog_sync_duration_seconds", duration_ms / 1000.0)

            else:
                logger.error(
                    "catalog_sync_failed",
                    extra={
                        "event_type": "catalog_sync_failed",
                        "merchant_id": merchant_id,
                        "product_id": str(sync_payload.product_id),
                        "retailer_id": sync_payload.retailer_id,
                        "action": sync_payload.action.value,
                        "errors": result.errors,
                        "retry_after": result.retry_after.isoformat() if result.retry_after else None,
                        "rate_limited": result.rate_limited,
                        "idempotency_key": sync_payload.idempotency_key
                    }
                )

                # Record failure metrics
                if result.rate_limited:
                    increment_counter("catalog_sync_rate_limited_total", tags={
                        "merchant_id": merchant_id
                    })
                else:
                    increment_counter("catalog_sync_failed_total", tags={
                        "merchant_id": merchant_id,
                        "action": sync_payload.action.value
                    })

                # Handle retryable errors
                if result.should_retry:
                    if result.rate_limited and result.retry_after:
                        # Rate limited - retry after specified time
                        raise RetryableError(
                            message=f"Meta API rate limited: {result.errors}",
                            next_run_at=result.retry_after
                        )
                    elif result.errors:
                        # Other retryable error
                        error_msg = " ".join(result.errors)
                        raise RetryableError(
                            message=f"Retryable catalog sync error: {error_msg}"
                        )
                else:
                    # Non-retryable error, mark as permanently failed
                    error_msg = " ".join(result.errors) if result.errors else "Unknown error"
                    raise ValueError(f"Permanent catalog sync failure: {error_msg}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Catalog sync error: {str(e)}", extra={
            "merchant_id": merchant_id,
            "payload": payload,
            "error": str(e)
        })
        raise

async def handle_image_cleanup(
    merchant_id: str,
    payload: Dict[str, Any]
) -> None:
    """Handle cleanup of orphaned Cloudinary images."""
    try:
        from src.integrations.cloudinary_client import CloudinaryClient

        cloudinary_public_id = payload["cloudinary_public_id"]
        reason = payload.get("reason", "orphaned_image")

        logger.info(
            "image_cleanup_start",
            extra={
                "event_type": "image_cleanup_start",
                "merchant_id": merchant_id,
                "cloudinary_public_id": cloudinary_public_id,
                "reason": reason
            }
        )

        # Initialize Cloudinary client
        client = CloudinaryClient()

        # Attempt to delete the image
        success = client.delete_image(cloudinary_public_id)

        if success:
            logger.info(
                "image_cleanup_success",
                extra={
                    "event_type": "image_cleanup_success",
                    "merchant_id": merchant_id,
                    "cloudinary_public_id": cloudinary_public_id,
                    "reason": reason
                }
            )

            increment_counter("image_cleanup_success_total", tags={
                "merchant_id": merchant_id,
                "reason": reason
            })
        else:
            logger.warning(
                "image_cleanup_failed",
                extra={
                    "event_type": "image_cleanup_failed",
                    "merchant_id": merchant_id,
                    "cloudinary_public_id": cloudinary_public_id,
                    "reason": reason
                }
            )

            increment_counter("image_cleanup_failed_total", tags={
                "merchant_id": merchant_id,
                "reason": reason
            })

            # Don't retry image cleanup failures - they might be already deleted
            # or the image might not exist

    except Exception as e:
        logger.error(f"Image cleanup error: {str(e)}", extra={
            "merchant_id": merchant_id,
            "cloudinary_public_id": payload.get("cloudinary_public_id"),
            "reason": payload.get("reason"),
            "error": str(e)
        })

        # Don't raise for image cleanup - these are best-effort operations
        # Log and continue

async def handle_catalog_unpublish(
    merchant_id: str,
    payload: Dict[str, Any]
) -> None:
    """Handle Meta Commerce Catalog unpublish operations."""
    start_time = datetime.now()

    try:
        # Import required services and models
        from ..database.connection import get_db_session
        from ..services.product_service import ProductService
        from ..integrations.meta_catalog import MetaCatalogClient, MetaCatalogConfig
        from ..models.sqlalchemy_models import Product
        from sqlalchemy import select

        # Get database session
        db = next(get_db_session())

        try:
            # Extract payload data
            product_id = UUID(payload["product_id"])
            retailer_id = payload["retailer_id"]
            trigger = payload.get("trigger", "unknown")

            logger.info(
                "catalog_unpublish_start",
                extra={
                    "event": "catalog_unpublish_start",
                    "merchant_id": merchant_id,
                    "product_id": str(product_id),
                    "retailer_id": retailer_id,
                    "trigger": trigger
                }
            )

            # Load Meta credentials using BE-019 integration service
            product_service = ProductService(db)
            meta_credentials = await product_service.load_meta_credentials_for_worker(UUID(merchant_id))

            if not meta_credentials or not meta_credentials.is_usable():
                # Credentials guard rail - short-circuit with error
                error_message = "Meta credentials not configured or invalid"
                error_code = "no_catalog_credentials"

                logger.error(
                    "catalog_unpublish_no_credentials",
                    extra={
                        "event": "catalog_unpublish_error",
                        "merchant_id": merchant_id,
                        "product_id": str(product_id),
                        "retailer_id": retailer_id,
                        "error": error_message,
                        "error_code": error_code
                    }
                )

                # Update product sync status to indicate credential error
                product = db.query(Product).filter(
                    Product.id == product_id,
                    Product.merchant_id == UUID(merchant_id)
                ).first()

                if product:
                    product.meta_sync_status = "error"
                    product.meta_sync_errors = {"error": error_message, "error_code": error_code}
                    db.commit()

                return  # Skip unpublish if no valid credentials

            # Build Meta catalog config from loaded credentials
            config = MetaCatalogConfig(
                catalog_id=meta_credentials.catalog_id,
                access_token=meta_credentials.system_user_token,
                app_id=meta_credentials.app_id,
                app_secret=os.getenv("META_APP_SECRET", "")
            )

            # Initialize Meta catalog client and call unpublish
            meta_client = MetaCatalogClient()
            result = await meta_client.unpublish_product(
                catalog_id=config.catalog_id,
                retailer_id=retailer_id,
                config=config
            )

            # Update product sync status based on result
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.merchant_id == UUID(merchant_id)
            ).first()

            if product:
                if result.success:
                    # For unpublish, we keep status as current but mark sync as successful
                    product.meta_sync_status = "synced"
                    product.meta_sync_errors = None
                    product.meta_last_synced_at = datetime.now()

                    logger.info(
                        "catalog_unpublish_success",
                        extra={
                            "event": "meta_catalog_unpublish_success",
                            "merchant_id": merchant_id,
                            "product_id": str(product_id),
                            "retailer_id": retailer_id,
                            "duration_ms": result.sync_duration_ms or 0,
                            "trigger": trigger
                        }
                    )

                    increment_counter("meta_unpublish_success_total")

                else:
                    # Handle unpublish errors
                    error_message = "; ".join(result.errors) if result.errors else "Unknown unpublish error"
                    product.meta_sync_status = "error"
                    product.meta_sync_errors = {"error": error_message, "error_code": "meta_unpublish_failed"}

                    logger.error(
                        "catalog_unpublish_failed",
                        extra={
                            "event": "meta_catalog_unpublish_failed",
                            "merchant_id": merchant_id,
                            "product_id": str(product_id),
                            "retailer_id": retailer_id,
                            "error_message": error_message,
                            "trigger": trigger
                        }
                    )

                    increment_counter("meta_unpublish_errors_total", tags={"error_type": "api_error"})

                    # Re-raise for retry if it's a retryable error
                    if result.retry_after:
                        raise RetryableError(
                            message=error_message,
                            next_run_at=result.retry_after
                        )

                db.commit()

            # Record timing metrics
            duration_seconds = (datetime.now() - start_time).total_seconds()
            record_timer("meta_unpublish_duration_seconds", duration_seconds)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Fatal error in catalog unpublish handler: {str(e)}")
        increment_counter("meta_unpublish_errors_total", tags={"error_type": "handler_error"})
        raise

# Map job types to their handlers
JOB_HANDLERS = {
    JobType.WA_SEND: handle_wa_send,
    JobType.CATALOG_SYNC: handle_catalog_sync,
    "catalog_unpublish": handle_catalog_unpublish,  # String key for catalog unpublish jobs
    "image_cleanup": handle_image_cleanup,  # String key for image cleanup jobs
    # Add other job handlers here
}

def get_job_handler(job_type: JobType) -> Optional[Callable]:
    """
    Get handler function for job type
    
    Args:
        job_type: Type of job to handle
        
    Returns:
        Handler function if available, None if no handler found
    """
    return JOB_HANDLERS.get(job_type)