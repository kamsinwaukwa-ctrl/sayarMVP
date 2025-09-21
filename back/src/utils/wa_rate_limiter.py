"""
WhatsApp-specific rate limiting utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from src.models.rate_limiting import RateLimitConfig, RateLimitInfo
from src.models.errors import RateLimitedError
from src.utils.rate_limiter import get_rate_limiter
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def check_wa_rate_limit(merchant_id: str, wa_rate_limit_per_hour: int) -> None:
    """
    Check WhatsApp rate limit for a merchant.
    Raises RateLimitedError if rate limited.
    """
    key = f"wa:merchant:{merchant_id}"
    config = RateLimitConfig(
        requests_per_minute=wa_rate_limit_per_hour / 60,  # Convert hourly to per-minute
        burst_limit=wa_rate_limit_per_hour // 4,  # Allow 25% burst
        window_size=3600,  # 1 hour window
    )

    try:
        info = await get_rate_limiter().check_and_consume(key, config)
        logger.debug(
            "wa_rate_limit_checked",
            extra={"merchant_id": merchant_id, "remaining": info.remaining},
        )
    except RateLimitedError as e:
        logger.info(
            "wa_rate_limit_exceeded",
            extra={"merchant_id": merchant_id, "retry_after": e.details["retry_after"]},
        )
        # Add jitter to prevent thundering herd
        retry_after = e.details["retry_after"]
        jitter = retry_after * 0.1  # 10% jitter
        next_run_at = datetime.now(timezone.utc) + timedelta(
            seconds=retry_after + jitter
        )
        raise RateLimitedError(
            message="WhatsApp rate limit exceeded",
            details={
                "limit": config.requests_per_minute,
                "remaining": 0,
                "reset_time": next_run_at.isoformat(),
                "retry_after": int(retry_after + jitter),
            },
        )
