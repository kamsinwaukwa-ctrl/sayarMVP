"""
Job handlers for outbox worker.
"""
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
    """Handle Meta Commerce Catalog synchronization."""
    start_time = datetime.now()
    
    try:
        # Extract payload data
        action = payload["action"]  # create, update, delete
        product_id = UUID(payload["product_id"])
        retailer_id = payload["retailer_id"]
        merchant_meta_config = payload["merchant_meta_config"]
        
        logger.info(
            "catalog_sync_start",
            extra={
                "event_type": "catalog_sync_start",
                "merchant_id": merchant_id,
                "product_id": str(product_id),
                "retailer_id": retailer_id,
                "action": action
            }
        )
        
        # Initialize Meta catalog client
        meta_client = MetaCatalogClient()
        
        # Create Meta catalog config
        config = MetaCatalogConfig(
            catalog_id=merchant_meta_config["catalog_id"],
            access_token=merchant_meta_config["access_token"],
            app_id=merchant_meta_config.get("app_id", ""),
            app_secret=merchant_meta_config.get("app_secret", "")
        )
        
        # Get product from database for create/update operations
        from src.database.connection import AsyncSessionLocal
        from src.models.sqlalchemy_models import Product, Merchant
        from sqlalchemy import select, update, and_
        
        async with AsyncSessionLocal() as db:
            if action in ["create", "update"]:
                # Get product details
                stmt = (
                    select(Product, Merchant)
                    .join(Merchant, Product.merchant_id == Merchant.id)
                    .where(Product.id == product_id)
                )
                result = await db.execute(stmt)
                row = result.fetchone()
                
                if not row:
                    raise ValueError(f"Product not found: {product_id}")
                
                product, merchant = row
                
                # Convert to Meta catalog format
                meta_product = meta_client.format_product_for_meta(
                    product, 
                    {"storefront_url": "https://example.com", "brand_name": merchant.name}
                )
                
                # Perform sync operation
                if action == "create":
                    result = await meta_client.create_product(
                        config.catalog_id, meta_product, config
                    )
                else:  # update
                    result = await meta_client.update_product(
                        config.catalog_id, retailer_id, meta_product, config
                    )
                
                # Update product sync status in database
                if result.success:
                    sync_status = MetaSyncStatus.SYNCED.value
                    sync_errors = None
                    last_synced_at = datetime.now()
                else:
                    sync_status = MetaSyncStatus.ERROR.value
                    sync_errors = result.errors
                    last_synced_at = None
                
                update_stmt = (
                    update(Product)
                    .where(Product.id == product_id)
                    .values(
                        meta_sync_status=sync_status,
                        meta_sync_errors=sync_errors,
                        meta_last_synced_at=last_synced_at,
                        updated_at=datetime.now()
                    )
                )
                await db.execute(update_stmt)
                await db.commit()
                
            elif action == "delete":
                # Delete product from catalog
                result = await meta_client.delete_product(
                    config.catalog_id, retailer_id, config
                )
            
            else:
                raise ValueError(f"Unknown catalog sync action: {action}")
        
        # Handle sync result
        if result.success:
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                "catalog_sync_success",
                extra={
                    "event_type": "catalog_sync_success",
                    "merchant_id": merchant_id,
                    "product_id": str(product_id),
                    "retailer_id": retailer_id,
                    "action": action,
                    "duration_seconds": duration_seconds,
                    "meta_product_id": result.meta_product_id
                }
            )
            
            # Record success metrics
            increment_counter("catalog_sync_success_total", tags={
                "merchant_id": merchant_id,
                "action": action
            })
            record_timer("catalog_sync_duration_seconds", duration_seconds)
            
        else:
            logger.error(
                "catalog_sync_failed",
                extra={
                    "event_type": "catalog_sync_failed",
                    "merchant_id": merchant_id,
                    "product_id": str(product_id),
                    "retailer_id": retailer_id,
                    "action": action,
                    "errors": result.errors,
                    "retry_after": result.retry_after.isoformat() if result.retry_after else None
                }
            )
            
            # Record failure metrics
            increment_counter("catalog_sync_failed_total", tags={
                "merchant_id": merchant_id,
                "action": action
            })
            
            # Handle rate limiting with retry
            if result.retry_after:
                raise RetryableError(
                    message=f"Meta API rate limited: {result.errors}",
                    next_run_at=result.retry_after
                )
            else:
                # Non-retryable error, mark as failed
                raise ValueError(f"Catalog sync failed: {result.errors}")
    
    except MetaCatalogRateLimitError as e:
        logger.warning(f"Meta API rate limit hit: {e.message}")
        raise RetryableError(
            message=e.message,
            next_run_at=e.retry_after
        )
    
    except Exception as e:
        logger.error(f"Catalog sync error: {str(e)}", extra={
            "merchant_id": merchant_id,
            "product_id": payload.get("product_id"),
            "action": payload.get("action"),
            "error": str(e)
        })
        raise

# Map job types to their handlers
JOB_HANDLERS = {
    JobType.WA_SEND: handle_wa_send,
    JobType.CATALOG_SYNC: handle_catalog_sync,
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