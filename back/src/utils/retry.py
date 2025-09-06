"""
Retry utilities with exponential backoff and jitter for reliable external service calls
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, TypeVar, Coroutine
from functools import wraps
import logging

from ..models.security import RetryConfig


T = TypeVar("T")


class RetryService:
    """Service for managing retry operations with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry service with configuration
        
        Args:
            config: Retry configuration (uses defaults if not provided)
        """
        self.config = config or RetryConfig()
    
    async def execute_with_retry(
        self, 
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with retry logic and exponential backoff
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retry attempts fail
        """
        attempt = 0
        delay = self.config.base_delay
        
        while True:
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                attempt += 1
                
                # Check if we should retry
                if attempt >= self.config.max_attempts:
                    logging.error(
                        f"Retry exhausted after {attempt} attempts",
                        extra={
                            "attempt": attempt,
                            "max_attempts": self.config.max_attempts,
                            "error": str(e)
                        }
                    )
                    raise
                
                # Calculate delay with jitter
                jitter = random.uniform(0, delay) if self.config.jitter else 0
                sleep_time = min(self.config.max_delay, delay + jitter)
                
                logging.warning(
                    f"Retry attempt {attempt}/{self.config.max_attempts} after error: {e}",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self.config.max_attempts,
                        "delay_seconds": sleep_time,
                        "error": str(e)
                    }
                )
                
                # Wait before retrying
                await asyncio.sleep(sleep_time)
                
                # Increase delay exponentially
                delay *= self.config.exponential_base
    
    def retry_decorator(self):
        """
        Create a decorator for retrying async functions
        
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., Coroutine[Any, Any, T]]):
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                return await self.execute_with_retry(func, *args, **kwargs)
            return wrapper
        return decorator


def retry_with_backoff(
    config: Optional[RetryConfig] = None
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        config: Retry configuration (optional)
        
    Returns:
        Decorator function
    """
    service = RetryService(config)
    return service.retry_decorator()


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable
    
    Args:
        error: Exception to check
        
    Returns:
        True if the error should be retried
    """
    retryable_errors = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        # HTTP 5xx errors (converted to exceptions)
        # Rate limiting errors
    )
    
    error_str = str(error).lower()
    
    # Check for retryable error patterns
    retryable_patterns = [
        'timeout',
        'connection',
        'network',
        'temporarily',
        'busy',
        'rate limit',
        'too many requests',
        'service unavailable',
        'gateway timeout',
        'internal server error'
    ]
    
    # Check if it's a known retryable error type
    if isinstance(error, retryable_errors):
        return True
    
    # Check error message for retryable patterns
    if any(pattern in error_str for pattern in retryable_patterns):
        return True
    
    return False


def calculate_backoff_delay(
    attempt: int, 
    base_delay: float = 1.0, 
    max_delay: float = 300.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> float:
    """
    Calculate backoff delay for a given attempt
    
    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential base for backoff
        jitter: Whether to add random jitter
        
    Returns:
        Delay in seconds
    """
    if attempt < 1:
        attempt = 1
    
    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = base_delay * (exponential_base ** (attempt - 1))
    
    # Add jitter (random value between 0 and delay)
    if jitter:
        delay += random.uniform(0, delay * 0.1)  # 10% jitter
    
    # Cap at maximum delay
    return min(delay, max_delay)


# Global retry service instance with default config
_default_retry_service = RetryService()


def execute_with_retry(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Execute a function with retry logic
    
    Args:
        func: Async function to execute
        *args: Function arguments
        config: Retry configuration (optional)
        **kwargs: Function keyword arguments
        
    Returns:
        Result of the function call
    """
    service = RetryService(config) if config else _default_retry_service
    return service.execute_with_retry(func, *args, **kwargs)