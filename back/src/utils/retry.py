"""
Retry utilities for Sayar WhatsApp Commerce Platform
Provides exponential backoff with jitter for reliable operation retry
"""

import asyncio
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import Optional, Callable, Any, Union, Type, Tuple
import logging

from ..models.errors import RetryableError
from ..utils.logger import log, log_error
from ..utils.metrics import record_error, record_retry_attempt, record_retry_failure


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 8
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds (5 minutes)
    exponential_base: float = 2.0
    jitter: bool = True


def is_retryable_exception(exception: Exception) -> bool:
    """
    Default classifier for retryable exceptions

    Args:
        exception: The exception to classify

    Returns:
        True if the exception should trigger a retry
    """
    # Always retry RetryableError
    if isinstance(exception, RetryableError):
        return True

    # Retry common network/timeout errors
    if isinstance(
        exception,
        (
            ConnectionError,
            TimeoutError,
            OSError,
        ),
    ):
        return True

    # Check for common HTTP client errors that are retryable
    if hasattr(exception, "status_code"):
        status = getattr(exception, "status_code")
        # Retry 5xx server errors and 429 rate limits
        return status >= 500 or status == 429

    return False


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for retry attempt with exponential backoff and jitter

    Args:
        attempt: Current attempt number (1-based)
        config: Retry configuration

    Returns:
        Delay in seconds before next retry
    """
    if attempt <= 1:
        return 0

    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = config.base_delay * (config.exponential_base ** (attempt - 2))

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd
    if config.jitter:
        # Use full jitter: multiply by random factor between 0 and 1
        delay = delay * random.random()

    return delay


def retryable(
    config: Optional[RetryConfig] = None,
    classify: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    Decorator for adding retry logic to functions

    Args:
        config: Retry configuration (uses defaults if None)
        classify: Function to determine if exception is retryable
        on_retry: Callback called before each retry attempt
    """
    if config is None:
        config = RetryConfig()

    if classify is None:
        classify = is_retryable_exception

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return _async_retryable_wrapper(func, config, classify, on_retry)
        else:
            return _sync_retryable_wrapper(func, config, classify, on_retry)

    return decorator


def _sync_retryable_wrapper(
    func: Callable,
    config: RetryConfig,
    classify: Callable[[Exception], bool],
    on_retry: Optional[Callable[[int, Exception, float], None]],
) -> Callable:
    """Synchronous retry wrapper"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if this exception should trigger a retry
                if not classify(e):
                    log_error(
                        "retry_not_retryable",
                        f"Exception not retryable: {type(e).__name__}",
                        exception=e,
                        function=func.__name__,
                        attempt=attempt,
                    )
                    raise

                # Don't retry on last attempt
                if attempt >= config.max_attempts:
                    break

                # Calculate delay and log retry attempt
                delay = calculate_delay(attempt, config)

                log.warning(
                    f"Retry attempt {attempt}/{config.max_attempts} for {func.__name__}",
                    extra={
                        "event_type": "retry_attempt",
                        "function": func.__name__,
                        "attempt": attempt,
                        "max_attempts": config.max_attempts,
                        "delay_seconds": delay,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                    },
                )

                # Call retry callback if provided
                if on_retry:
                    on_retry(attempt, e, delay)

                # Record metrics
                record_retry_attempt(func.__name__)

                # Wait before retrying
                if delay > 0:
                    time.sleep(delay)

        # All retries exhausted
        log_error(
            "retry_failed",
            f"All retry attempts exhausted for {func.__name__}",
            exception=last_exception,
            function=func.__name__,
            total_attempts=config.max_attempts,
        )

        record_retry_failure(func.__name__)

        # Raise RetryableError to signal that this operation failed after retries
        if isinstance(last_exception, RetryableError):
            raise last_exception
        else:
            raise RetryableError(
                service=func.__name__,
                message=f"Operation failed after {config.max_attempts} attempts: {str(last_exception)}",
            )

    return wrapper


def _async_retryable_wrapper(
    func: Callable,
    config: RetryConfig,
    classify: Callable[[Exception], bool],
    on_retry: Optional[Callable[[int, Exception, float], None]],
) -> Callable:
    """Asynchronous retry wrapper"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if this exception should trigger a retry
                if not classify(e):
                    log_error(
                        "retry_not_retryable",
                        f"Exception not retryable: {type(e).__name__}",
                        exception=e,
                        function=func.__name__,
                        attempt=attempt,
                    )
                    raise

                # Don't retry on last attempt
                if attempt >= config.max_attempts:
                    break

                # Calculate delay and log retry attempt
                delay = calculate_delay(attempt, config)

                log.warning(
                    f"Retry attempt {attempt}/{config.max_attempts} for {func.__name__}",
                    extra={
                        "event_type": "retry_attempt",
                        "function": func.__name__,
                        "attempt": attempt,
                        "max_attempts": config.max_attempts,
                        "delay_seconds": delay,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                    },
                )

                # Call retry callback if provided
                if on_retry:
                    on_retry(attempt, e, delay)

                # Record metrics
                record_retry_attempt(func.__name__)

                # Wait before retrying
                if delay > 0:
                    await asyncio.sleep(delay)

        # All retries exhausted
        log_error(
            "retry_failed",
            f"All retry attempts exhausted for {func.__name__}",
            exception=last_exception,
            function=func.__name__,
            total_attempts=config.max_attempts,
        )

        record_retry_failure(func.__name__)

        # Raise RetryableError to signal that this operation failed after retries
        if isinstance(last_exception, RetryableError):
            raise last_exception
        else:
            raise RetryableError(
                service=func.__name__,
                message=f"Operation failed after {config.max_attempts} attempts: {str(last_exception)}",
            )

    return wrapper


class RetryableOperation:
    """Context manager for manual retry logic"""

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        operation_name: str = "operation",
        classify: Optional[Callable[[Exception], bool]] = None,
    ):
        self.config = config or RetryConfig()
        self.operation_name = operation_name
        self.classify = classify or is_retryable_exception
        self.attempt = 0
        self.last_exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and exc_value:
            self.last_exception = exc_value

            if self.classify(exc_value):
                # This exception is retryable
                return True  # Suppress the exception
            else:
                # This exception should not be retried
                return False  # Let the exception propagate

        return False

    def should_retry(self) -> bool:
        """Check if operation should be retried"""
        return (
            self.last_exception
            and self.attempt < self.config.max_attempts
            and self.classify(self.last_exception)
        )

    def next_attempt(self) -> float:
        """
        Prepare for next retry attempt

        Returns:
            Delay in seconds before next attempt
        """
        self.attempt += 1
        delay = calculate_delay(self.attempt, self.config)

        log.warning(
            f"Retry attempt {self.attempt}/{self.config.max_attempts} for {self.operation_name}",
            extra={
                "event_type": "retry_attempt",
                "operation": self.operation_name,
                "attempt": self.attempt,
                "max_attempts": self.config.max_attempts,
                "delay_seconds": delay,
                "exception_type": type(self.last_exception).__name__,
                "exception_message": str(self.last_exception),
            },
        )

        record_retry_attempt(self.operation_name)
        return delay

    def exhausted(self) -> RetryableError:
        """
        Create error for exhausted retries

        Returns:
            RetryableError indicating all retries failed
        """
        log_error(
            "retry_failed",
            f"All retry attempts exhausted for {self.operation_name}",
            exception=self.last_exception,
            operation=self.operation_name,
            total_attempts=self.config.max_attempts,
        )

        record_retry_failure(self.operation_name)

        if isinstance(self.last_exception, RetryableError):
            return self.last_exception
        else:
            return RetryableError(
                service=self.operation_name,
                message=f"Operation failed after {self.config.max_attempts} attempts: {str(self.last_exception)}",
            )


# Convenience function for simple retry operations
async def retry_async(
    operation: Callable,
    config: Optional[RetryConfig] = None,
    classify: Optional[Callable[[Exception], bool]] = None,
    operation_name: str = "async_operation",
) -> Any:
    """
    Retry an async operation with exponential backoff

    Args:
        operation: Async callable to retry
        config: Retry configuration
        classify: Function to determine if exception is retryable
        operation_name: Name for logging/metrics

    Returns:
        Result of successful operation

    Raises:
        RetryableError: If all retry attempts are exhausted
    """
    config = config or RetryConfig()
    classify = classify or is_retryable_exception

    retry_op = RetryableOperation(config, operation_name, classify)

    while True:
        with retry_op:
            return await operation()

        if retry_op.should_retry():
            delay = retry_op.next_attempt()
            if delay > 0:
                await asyncio.sleep(delay)
        else:
            raise retry_op.exhausted()


# Alias for backward compatibility
retry_with_backoff = retryable


def retry_sync(
    operation: Callable,
    config: Optional[RetryConfig] = None,
    classify: Optional[Callable[[Exception], bool]] = None,
    operation_name: str = "sync_operation",
) -> Any:
    """
    Retry a sync operation with exponential backoff

    Args:
        operation: Callable to retry
        config: Retry configuration
        classify: Function to determine if exception is retryable
        operation_name: Name for logging/metrics

    Returns:
        Result of successful operation

    Raises:
        RetryableError: If all retry attempts are exhausted
    """
    config = config or RetryConfig()
    classify = classify or is_retryable_exception

    retry_op = RetryableOperation(config, operation_name, classify)

    while True:
        with retry_op:
            return operation()

        if retry_op.should_retry():
            delay = retry_op.next_attempt()
            if delay > 0:
                time.sleep(delay)
        else:
            raise retry_op.exhausted()
