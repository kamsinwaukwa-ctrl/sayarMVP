"""
Rate limiting API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rate_limiting import MerchantRateLimitConfig
from src.models.api import APIResponse
from src.dependencies.auth import get_current_merchant_id, require_admin
from src.database.connection import get_db
from src.utils.rate_limiter import get_rate_limiter
from src.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/rate-limits", tags=["rate-limits"])
logger = get_logger(__name__)

@router.get("/me", response_model=APIResponse[MerchantRateLimitConfig])
async def get_my_rate_limits(
    merchant_id: str = Depends(get_current_merchant_id),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MerchantRateLimitConfig]:
    """Get current merchant's rate limit configuration."""
    query = """
    SELECT 
        merchant_id,
        api_rate_limit_per_minute,
        api_burst_limit,
        wa_rate_limit_per_hour,
        rate_limit_enabled
    FROM merchants
    WHERE merchant_id = :merchant_id
    """
    result = await db.execute(query, {"merchant_id": merchant_id})
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return APIResponse(
        ok=True,
        data=MerchantRateLimitConfig(**row._asdict())
    )

@router.get("/{merchant_id}", response_model=APIResponse[MerchantRateLimitConfig])
async def get_merchant_rate_limits(
    merchant_id: str,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MerchantRateLimitConfig]:
    """Get rate limit configuration for any merchant (admin only)."""
    query = """
    SELECT 
        merchant_id,
        api_rate_limit_per_minute,
        api_burst_limit,
        wa_rate_limit_per_hour,
        rate_limit_enabled
    FROM merchants
    WHERE merchant_id = :merchant_id
    """
    result = await db.execute(query, {"merchant_id": merchant_id})
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return APIResponse(
        ok=True,
        data=MerchantRateLimitConfig(**row._asdict())
    )

@router.patch("/{merchant_id}", response_model=APIResponse[MerchantRateLimitConfig])
async def update_merchant_rate_limits(
    merchant_id: str,
    config: MerchantRateLimitConfig,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MerchantRateLimitConfig]:
    """Update rate limit configuration for a merchant (admin only)."""
    query = """
    UPDATE merchants
    SET 
        api_rate_limit_per_minute = :api_rate_limit_per_minute,
        api_burst_limit = :api_burst_limit,
        wa_rate_limit_per_hour = :wa_rate_limit_per_hour,
        rate_limit_enabled = :rate_limit_enabled
    WHERE merchant_id = :merchant_id
    RETURNING 
        merchant_id,
        api_rate_limit_per_minute,
        api_burst_limit,
        wa_rate_limit_per_hour,
        rate_limit_enabled
    """
    result = await db.execute(
        query,
        {
            "merchant_id": merchant_id,
            "api_rate_limit_per_minute": config.api_rate_limit_per_minute,
            "api_burst_limit": config.api_burst_limit,
            "wa_rate_limit_per_hour": config.wa_rate_limit_per_hour,
            "rate_limit_enabled": config.rate_limit_enabled
        }
    )
    await db.commit()
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    updated_config = MerchantRateLimitConfig(**row._asdict())
    
    # Log configuration change
    logger.info(
        "rate_limit_config_changed",
        extra={
            "merchant_id": merchant_id,
            "old": config.dict(),
            "new": updated_config.dict()
        }
    )
    
    return APIResponse(
        ok=True,
        data=updated_config
    )

@router.post("/{merchant_id}/reset", response_model=APIResponse[None])
async def reset_merchant_rate_limits(
    merchant_id: str,
    _: None = Depends(require_admin)
) -> APIResponse[None]:
    """Reset rate limit counters for a merchant (admin only)."""
    # Delete all buckets for this merchant
    limiter = get_rate_limiter()
    await limiter.store.delete_bucket(f"merchant:{merchant_id}")
    await limiter.store.delete_bucket(f"wa:merchant:{merchant_id}")
    
    logger.info(
        "rate_limit_reset",
        extra={
            "merchant_id": merchant_id
        }
    )
    
    return APIResponse(
        ok=True,
        message="Rate limit counters reset successfully"
    )

