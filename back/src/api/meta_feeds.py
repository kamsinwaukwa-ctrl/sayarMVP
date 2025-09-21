"""
Meta Feeds API endpoints for CSV feed generation with rate limiting and caching
"""

import os
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db
from ..services.meta_feed_service import MetaFeedService
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer

logger = get_logger(__name__)
router = APIRouter(prefix="/meta/feeds", tags=["Meta Feeds"])

# Simple in-memory rate limiting (production should use Redis)
rate_limit_cache: Dict[str, Dict[str, float]] = {}
RATE_LIMIT_REQUESTS = 60  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(client_ip: str) -> bool:
    """
    Simple IP-based rate limiting: 60 requests per minute
    Production implementation should use Redis with sliding window
    """
    now = time.time()

    if client_ip not in rate_limit_cache:
        rate_limit_cache[client_ip] = {"count": 1, "window_start": now}
        return True

    client_data = rate_limit_cache[client_ip]

    # Reset window if expired
    if now - client_data["window_start"] >= RATE_LIMIT_WINDOW:
        rate_limit_cache[client_ip] = {"count": 1, "window_start": now}
        return True

    # Check if within limit
    if client_data["count"] >= RATE_LIMIT_REQUESTS:
        return False

    # Increment counter
    client_data["count"] += 1
    return True


def get_client_ip(request: Request) -> str:
    """Get client IP with proxy header support"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


@router.get("/{merchant_slug}/products.csv")
async def get_merchant_feed(
    merchant_slug: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate Meta Commerce CSV feed for merchant

    **Public Endpoint** - No authentication required (consumed by Meta)

    Features:
    - HTTP caching with ETag and Last-Modified headers
    - Rate limiting (60 requests/minute per IP)
    - Multi-tenant isolation via merchant slug
    - Streaming response for large catalogs
    - Comprehensive logging and metrics

    Returns CSV feed in Meta Commerce Catalog format
    """
    start_time = datetime.now()
    client_ip = get_client_ip(request)

    # Log request
    logger.info(
        "meta_feed_requested",
        extra={
            "merchant_slug": merchant_slug,
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
        },
    )

    increment_counter("meta_feeds_requested_total")

    try:
        # Rate limiting check
        if not check_rate_limit(client_ip):
            increment_counter("meta_feeds_rate_limited_total")
            logger.warning(
                "meta_feed_rate_limited",
                extra={"merchant_slug": merchant_slug, "client_ip": client_ip},
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Limit: 60 requests per minute per IP.",
                headers={"Retry-After": "60"},
            )

        # Initialize service
        service = MetaFeedService(db)

        # Check for conditional requests (caching)
        if_none_match = request.headers.get("If-None-Match")
        if_modified_since = request.headers.get("If-Modified-Since")

        # Generate feed
        csv_content, feed_metadata = await service.generate_feed_csv(merchant_slug)

        # Handle conditional requests for caching
        if if_none_match and if_none_match == feed_metadata.etag:
            increment_counter("meta_feeds_cached_total")
            logger.info(
                "meta_feed_cached",
                extra={
                    "merchant_slug": merchant_slug,
                    "etag": feed_metadata.etag,
                    "cache_hit": True,
                },
            )
            return Response(status_code=304)

        if if_modified_since:
            try:
                modified_since = datetime.fromisoformat(
                    if_modified_since.replace("Z", "+00:00")
                )
                if feed_metadata.last_updated <= modified_since:
                    increment_counter("meta_feeds_cached_total")
                    logger.info(
                        "meta_feed_cached",
                        extra={
                            "merchant_slug": merchant_slug,
                            "last_modified": feed_metadata.last_updated.isoformat(),
                            "cache_hit": True,
                        },
                    )
                    return Response(status_code=304)
            except ValueError:
                # Invalid date format, ignore
                pass

        # Set response headers
        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Cache-Control": f"public, max-age={feed_metadata.cache_ttl}",
            "ETag": feed_metadata.etag,
            "Last-Modified": feed_metadata.last_updated.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            ),
            "Content-Length": str(feed_metadata.content_length),
            "X-Product-Count": str(feed_metadata.product_count),
            "X-Generated-At": datetime.utcnow().isoformat() + "Z",
        }

        # Log successful generation
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.info(
            "meta_feed_generated_success",
            extra={
                "merchant_slug": merchant_slug,
                "product_count": feed_metadata.product_count,
                "content_size": feed_metadata.content_length,
                "etag": feed_metadata.etag,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "cache_hit": False,
            },
        )

        record_timer("meta_feed_response_duration_ms", duration_ms)

        # Stream response for large feeds
        def generate_csv():
            yield csv_content.encode("utf-8")

        return StreamingResponse(
            generate_csv(), media_type="text/csv", headers=headers, status_code=200
        )

    except ValueError as e:
        # Handle merchant not found
        if "not found" in str(e).lower():
            increment_counter("meta_feeds_not_found_total")
            logger.warning(
                "merchant_not_found",
                extra={
                    "merchant_slug": merchant_slug,
                    "client_ip": client_ip,
                    "error": str(e),
                },
            )
            raise HTTPException(
                status_code=404, detail=f"Merchant '{merchant_slug}' not found"
            )

        # Other validation errors
        increment_counter("meta_feeds_error_total")
        logger.error(
            "meta_feed_validation_error",
            extra={
                "merchant_slug": merchant_slug,
                "client_ip": client_ip,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Internal server errors
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        increment_counter("meta_feeds_error_total")
        logger.error(
            "meta_feed_internal_error",
            extra={
                "merchant_slug": merchant_slug,
                "client_ip": client_ip,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms,
            },
        )
        raise HTTPException(
            status_code=500, detail="Internal server error while generating feed"
        )


@router.get("/{merchant_slug}/stats")
async def get_feed_stats(
    merchant_slug: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Get feed statistics for merchant

    **Public Endpoint** - Basic stats for feed monitoring

    Returns:
    - Product counts (total, visible, in-stock)
    - Last update timestamp
    - Feed metadata
    """
    client_ip = get_client_ip(request)

    # Basic rate limiting for stats endpoint too
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Limit: 60 requests per minute per IP.",
            headers={"Retry-After": "60"},
        )

    try:
        service = MetaFeedService(db)
        stats = await service.get_feed_stats(merchant_slug)

        if not stats:
            raise HTTPException(
                status_code=404, detail=f"Merchant '{merchant_slug}' not found"
            )

        logger.info(
            "meta_feed_stats_requested",
            extra={"merchant_slug": merchant_slug, "client_ip": client_ip},
        )

        return {
            "merchant_slug": merchant_slug,
            "stats": stats.model_dump(),
            "feed_url": f"{request.base_url}api/v1/meta/feeds/{merchant_slug}/products.csv",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get feed stats",
            extra={
                "merchant_slug": merchant_slug,
                "client_ip": client_ip,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Internal server error")
