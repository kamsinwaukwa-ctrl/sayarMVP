"""
Rate limiting middleware for Sayar platform.
"""
from typing import Optional, Dict, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.models.rate_limiting import RateLimitConfig, RateLimitInfo
from src.models.errors import RateLimitedError
from src.utils.rate_limiter import get_rate_limiter
from src.utils.logger import get_logger
from src.utils.metrics import increment_counter
from src.dependencies.auth import get_current_merchant_id

logger = get_logger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing rate limits on API endpoints."""
    
    def __init__(
        self,
        app: ASGIApp,
        default_config: Optional[RateLimitConfig] = None,
        route_configs: Optional[Dict[str, RateLimitConfig]] = None
    ):
        super().__init__(app)
        self.default_config = default_config or RateLimitConfig()
        self.route_configs = route_configs or {}
        self.limiter = get_rate_limiter()
    
    async def _get_rate_limit_key(self, request: Request) -> str:
        """Get rate limit key based on merchant ID or IP."""
        try:
            merchant_id = await get_current_merchant_id(request)
            return f"merchant:{merchant_id}"
        except:
            # Fall back to IP-based limiting for unauthenticated requests
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host
            return f"ip:{ip}"
    
    def _get_config_for_route(self, path: str) -> RateLimitConfig:
        """Get rate limit config for the current route."""
        # Check for exact path match
        if path in self.route_configs:
            return self.route_configs[path]
        
        # Check for pattern matches (e.g., /api/v1/products/{id})
        for pattern, config in self.route_configs.items():
            if "{" in pattern:  # Simple pattern detection
                base_pattern = pattern.split("{")[0]
                if path.startswith(base_pattern):
                    return config
        
        return self.default_config
    
    def _add_rate_limit_headers(
        self,
        response: Response,
        info: RateLimitInfo
    ) -> None:
        """Add rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(info.limit)
        response.headers["X-RateLimit-Remaining"] = str(info.remaining)
        response.headers["X-RateLimit-Reset"] = info.reset_time.isoformat()
        if info.retry_after is not None:
            response.headers["Retry-After"] = str(info.retry_after)
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for certain paths
        if request.url.path in ["/healthz", "/readyz", "/metrics"]:
            return await call_next(request)
        
        key = await self._get_rate_limit_key(request)
        config = self._get_config_for_route(request.url.path)
        
        try:
            # Check and consume rate limit
            info = await self.limiter.check_and_consume(key, config)
            
            # Log rate limit check (debug level)
            logger.debug(
                "rate_limit_checked",
                extra={
                    "key": key,
                    "type": "api",
                    "remaining": info.remaining
                }
            )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            self._add_rate_limit_headers(response, info)
            return response
            
        except RateLimitedError as e:
            # Log rate limit exceeded
            logger.info(
                "rate_limit_exceeded",
                extra={
                    "key": key,
                    "type": "api",
                    "limit": config.requests_per_minute,
                    "remaining": 0,
                    "retry_after": e.details.get("retry_after")
                }
            )
            
            # Increment rate limit violation metric
            increment_counter(
                "rate_limit_violations_total",
                labels={"type": "api"}
            )
            
            # Create 429 response with rate limit info
            info = RateLimitInfo(
                limit=e.details["limit"],
                remaining=e.details["remaining"],
                reset_time=e.details["reset_time"],
                retry_after=e.details["retry_after"]
            )
            
            response = Response(
                status_code=429,
                content=e.json(),
                media_type="application/json"
            )
            self._add_rate_limit_headers(response, info)
            return response

def create_rate_limit_middleware() -> Callable[[ASGIApp], RateLimitMiddleware]:
    """Create rate limit middleware with default configuration."""
    default_config = RateLimitConfig(
        requests_per_minute=60,
        burst_limit=15,
        window_size=60
    )
    
    # Define stricter limits for auth endpoints
    route_configs = {
        "/api/v1/auth/login": RateLimitConfig(
            requests_per_minute=30,
            burst_limit=10,
            window_size=60
        ),
        "/api/v1/auth/register": RateLimitConfig(
            requests_per_minute=10,
            burst_limit=5,
            window_size=60
        )
    }
    
    def create(app: ASGIApp) -> RateLimitMiddleware:
        return RateLimitMiddleware(app, default_config, route_configs)
    
    return create

