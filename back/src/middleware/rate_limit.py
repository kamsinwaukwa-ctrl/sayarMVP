"""
Rate limiting middleware for authentication endpoints
"""

import time
from typing import Dict, NamedTuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

class RateLimitRecord(NamedTuple):
    """Rate limit record with timestamp"""
    timestamp: float

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):  # 5 attempts per 5 minutes
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, deque] = defaultdict(deque)
    
    def _cleanup_old_attempts(self, key: str, current_time: float) -> None:
        """Remove attempts older than the time window"""
        cutoff_time = current_time - self.window_seconds
        while self.attempts[key] and self.attempts[key][0] < cutoff_time:
            self.attempts[key].popleft()
    
    def is_rate_limited(self, key: str) -> bool:
        """
        Check if key is rate limited
        
        Args:
            key: Unique identifier (IP address, email, etc.)
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        self._cleanup_old_attempts(key, current_time)
        
        return len(self.attempts[key]) >= self.max_attempts
    
    def record_attempt(self, key: str) -> None:
        """
        Record an attempt for the given key
        
        Args:
            key: Unique identifier (IP address, email, etc.)
        """
        current_time = time.time()
        self._cleanup_old_attempts(key, current_time)
        self.attempts[key].append(current_time)
    
    def get_remaining_attempts(self, key: str) -> int:
        """
        Get remaining attempts for the key
        
        Args:
            key: Unique identifier
            
        Returns:
            Number of remaining attempts
        """
        current_time = time.time()
        self._cleanup_old_attempts(key, current_time)
        current_attempts = len(self.attempts[key])
        return max(0, self.max_attempts - current_attempts)
    
    def get_reset_time(self, key: str) -> float:
        """
        Get time when rate limit resets for the key
        
        Args:
            key: Unique identifier
            
        Returns:
            Timestamp when limit resets (0 if not rate limited)
        """
        current_time = time.time()
        self._cleanup_old_attempts(key, current_time)
        
        if not self.attempts[key]:
            return 0
            
        oldest_attempt = self.attempts[key][0]
        return oldest_attempt + self.window_seconds

# Global rate limiter instances
login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5 attempts per 5 minutes

def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded IP headers (common in production behind proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"

async def check_login_rate_limit(request: Request) -> None:
    """
    Check rate limit for login attempts
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = get_client_ip(request)
    
    # Check IP-based rate limit
    if login_rate_limiter.is_rate_limited(f"ip:{client_ip}"):
        reset_time = login_rate_limiter.get_reset_time(f"ip:{client_ip}")
        reset_in = int(reset_time - time.time())
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {reset_in} seconds.",
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Limit": str(login_rate_limiter.max_attempts),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time))
            }
        )

async def check_email_rate_limit(email: str) -> None:
    """
    Check rate limit for specific email
    
    Args:
        email: Email address
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if login_rate_limiter.is_rate_limited(f"email:{email}"):
        reset_time = login_rate_limiter.get_reset_time(f"email:{email}")
        reset_in = int(reset_time - time.time())
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts for this email. Try again in {reset_in} seconds.",
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Limit": str(login_rate_limiter.max_attempts),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time))
            }
        )

def record_login_attempt(request: Request, email: str, success: bool = False) -> None:
    """
    Record login attempt for rate limiting
    
    Args:
        request: FastAPI request object
        email: Email address used in login attempt
        success: Whether the login was successful
    """
    client_ip = get_client_ip(request)
    
    # Always record IP attempts
    login_rate_limiter.record_attempt(f"ip:{client_ip}")
    
    # Only record email attempts for failed logins
    if not success:
        login_rate_limiter.record_attempt(f"email:{email}")

def get_rate_limit_headers(key: str) -> Dict[str, str]:
    """
    Get rate limit headers for response
    
    Args:
        key: Rate limit key
        
    Returns:
        Dictionary of headers
    """
    remaining = login_rate_limiter.get_remaining_attempts(key)
    reset_time = login_rate_limiter.get_reset_time(key)
    
    headers = {
        "X-RateLimit-Limit": str(login_rate_limiter.max_attempts),
        "X-RateLimit-Remaining": str(remaining)
    }
    
    if reset_time > 0:
        headers["X-RateLimit-Reset"] = str(int(reset_time))
    
    return headers