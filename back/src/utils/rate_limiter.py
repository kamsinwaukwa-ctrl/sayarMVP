"""
Token bucket rate limiter implementation for Sayar platform.
"""
import time
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from src.models.rate_limiting import RateLimitConfig, RateLimitInfo
from src.models.errors import RateLimitedError

@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int  # Maximum number of tokens (burst limit)
    tokens: float  # Current number of tokens
    last_update: float  # Last update timestamp
    rate: float  # Token refill rate per second

class RateLimitStore(ABC):
    """Abstract base class for rate limit storage backends."""
    
    @abstractmethod
    async def get_bucket(self, key: str) -> Optional[TokenBucket]:
        """Get token bucket for key."""
        pass
    
    @abstractmethod
    async def set_bucket(self, key: str, bucket: TokenBucket) -> None:
        """Save token bucket for key."""
        pass
    
    @abstractmethod
    async def delete_bucket(self, key: str) -> None:
        """Delete token bucket for key."""
        pass

class MemoryStore(RateLimitStore):
    """In-memory implementation of rate limit storage."""
    
    def __init__(self):
        self._store: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
    
    async def get_bucket(self, key: str) -> Optional[TokenBucket]:
        async with self._lock:
            return self._store.get(key)
    
    async def set_bucket(self, key: str, bucket: TokenBucket) -> None:
        async with self._lock:
            self._store[key] = bucket
    
    async def delete_bucket(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

class RedisStore(RateLimitStore):
    """Redis-based implementation of rate limit storage (placeholder)."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        # TODO: Implement Redis connection and methods
    
    async def get_bucket(self, key: str) -> Optional[TokenBucket]:
        raise NotImplementedError("Redis store not implemented")
    
    async def set_bucket(self, key: str, bucket: TokenBucket) -> None:
        raise NotImplementedError("Redis store not implemented")
    
    async def delete_bucket(self, key: str) -> None:
        raise NotImplementedError("Redis store not implemented")

class RateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, store: RateLimitStore):
        self.store = store
    
    def _create_bucket(self, config: RateLimitConfig) -> TokenBucket:
        """Create a new token bucket from config."""
        return TokenBucket(
            capacity=config.burst_limit,
            tokens=float(config.burst_limit),
            last_update=time.time(),
            rate=config.requests_per_minute / 60.0  # Convert to per-second rate
        )
        
    def _reset_bucket(self, key: str) -> None:
        """Reset bucket for testing."""
        self.store._store.pop(key, None)
    
    def _update_tokens(self, bucket: TokenBucket) -> None:
        """Update token count based on time elapsed."""
        now = time.time()
        elapsed = now - bucket.last_update
        bucket.tokens = min(
            bucket.capacity,
            bucket.tokens + elapsed * bucket.rate
        )
        bucket.last_update = now
    
    async def check_and_consume(self, key: str, config: RateLimitConfig) -> RateLimitInfo:
        """Check if request is allowed and consume a token if it is."""
        bucket = await self.store.get_bucket(key)
        if not bucket:
            bucket = self._create_bucket(config)
        
        self._update_tokens(bucket)
        
        if bucket.tokens < 1:
            # Calculate time until next token
            time_until_next = (1 - bucket.tokens) / bucket.rate
            reset_time = datetime.fromtimestamp(bucket.last_update + time_until_next, timezone.utc)
            
            await self.store.set_bucket(key, bucket)
            
            raise RateLimitedError(
                message="Rate limit exceeded",
                details={
                    "limit": config.requests_per_minute,
                    "remaining": 0,
                    "reset_time": reset_time.isoformat(),
                    "retry_after": int(time_until_next)
                }
            )
        
        # Consume token
        bucket.tokens -= 1
        await self.store.set_bucket(key, bucket)
        
        return RateLimitInfo(
            limit=config.requests_per_minute,
            remaining=int(bucket.tokens),
            reset_time=datetime.fromtimestamp(
                bucket.last_update + (bucket.capacity - bucket.tokens) / bucket.rate,
                timezone.utc
            ),
            retry_after=None
        )
    
    async def peek(self, key: str) -> Optional[RateLimitInfo]:
        """Get current rate limit info without consuming a token."""
        bucket = await self.store.get_bucket(key)
        if not bucket:
            return None
        
        self._update_tokens(bucket)
        await self.store.set_bucket(key, bucket)
        
        return RateLimitInfo(
            limit=bucket.capacity,
            remaining=int(bucket.tokens),
            reset_time=datetime.fromtimestamp(
                bucket.last_update + (bucket.capacity - bucket.tokens) / bucket.rate,
                timezone.utc
            ),
            retry_after=None if bucket.tokens >= 1 else int((1 - bucket.tokens) / bucket.rate)
        )

# Global rate limiter instance using memory store
_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if not _rate_limiter:
        _rate_limiter = RateLimiter(MemoryStore())
    return _rate_limiter
