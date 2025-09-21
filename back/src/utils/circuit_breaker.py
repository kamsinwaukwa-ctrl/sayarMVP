"""
Circuit breaker utility for Sayar WhatsApp Commerce Platform
Prevents cascade failures by breaking connections to failing services
"""

import asyncio
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Dict, Optional, Callable, Any, Union
import threading

from ..utils.logger import log, log_error
from ..utils.metrics import (
    record_error,
    record_circuit_breaker_open,
    record_circuit_breaker_state,
)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""

    failure_threshold: int = 5  # Number of failures to trigger open state
    recovery_timeout: float = 60.0  # Seconds before transitioning to half-open
    success_threshold: int = 3  # Successful calls in half-open to close circuit
    timeout: float = 30.0  # Request timeout in seconds

    # Rolling window configuration
    window_size: int = 100  # Number of recent calls to track
    minimum_calls: int = 10  # Minimum calls before evaluating failure rate


@dataclass
class CircuitStats:
    """Statistics for circuit breaker decisions"""

    total_calls: int = 0
    failed_calls: int = 0
    successful_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None

    # Rolling window of recent calls (True = success, False = failure)
    recent_calls: list = field(default_factory=list)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""

    def __init__(self, key: str, state: CircuitState):
        self.key = key
        self.state = state
        super().__init__(f"Circuit breaker '{key}' is {state.value}")


class CircuitBreaker:
    """
    Circuit breaker implementation with configurable thresholds and recovery
    """

    def __init__(self, key: str, config: Optional[CircuitBreakerConfig] = None):
        self.key = key
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._lock = threading.RLock()

    def _should_open(self) -> bool:
        """Check if circuit should transition to open state"""
        # Need minimum calls before evaluating
        if self.stats.total_calls < self.config.minimum_calls:
            return False

        # Check failure rate in rolling window
        if len(self.stats.recent_calls) >= self.config.minimum_calls:
            failures = sum(1 for call in self.stats.recent_calls if not call)
            if failures >= self.config.failure_threshold:
                return True

        # Check consecutive failures
        return self.stats.consecutive_failures >= self.config.failure_threshold

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should transition from open to half-open"""
        if self.state != CircuitState.OPEN:
            return False

        if self.stats.last_failure_time is None:
            return True

        return (
            time.time() - self.stats.last_failure_time
        ) >= self.config.recovery_timeout

    def _should_close(self) -> bool:
        """Check if circuit should transition from half-open to closed"""
        return (
            self.state == CircuitState.HALF_OPEN
            and self.stats.consecutive_successes >= self.config.success_threshold
        )

    def _update_stats(self, success: bool):
        """Update circuit breaker statistics"""
        current_time = time.time()

        with self._lock:
            self.stats.total_calls += 1

            # Add to rolling window
            self.stats.recent_calls.append(success)
            if len(self.stats.recent_calls) > self.config.window_size:
                self.stats.recent_calls.pop(0)

            if success:
                self.stats.successful_calls += 1
                self.stats.consecutive_successes += 1
                self.stats.consecutive_failures = 0
                self.stats.last_success_time = current_time
            else:
                self.stats.failed_calls += 1
                self.stats.consecutive_failures += 1
                self.stats.consecutive_successes = 0
                self.stats.last_failure_time = current_time

    def _transition_state(self, new_state: CircuitState):
        """Transition to new circuit breaker state with logging"""
        if self.state == new_state:
            return

        old_state = self.state
        self.state = new_state

        log.info(
            f"Circuit breaker '{self.key}' transitioned from {old_state.value} to {new_state.value}",
            extra={
                "event_type": "circuit_breaker_transition",
                "circuit_key": self.key,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "total_calls": self.stats.total_calls,
                "failed_calls": self.stats.failed_calls,
                "consecutive_failures": self.stats.consecutive_failures,
                "consecutive_successes": self.stats.consecutive_successes,
            },
        )

        # Record metrics for state transitions
        record_circuit_breaker_state(self.key, new_state.value)

        if new_state == CircuitState.OPEN:
            record_circuit_breaker_open(self.key)

    def call(self, operation: Callable[[], Any]) -> Any:
        """
        Execute operation through circuit breaker (synchronous)

        Args:
            operation: Function to execute

        Returns:
            Result of operation

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from the operation
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            with self._lock:
                if self.state == CircuitState.OPEN:
                    self._transition_state(CircuitState.HALF_OPEN)

        # Reject calls if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(self.key, self.state)

        # Execute operation
        try:
            result = operation()
            self._update_stats(success=True)

            # Check if we should close the circuit
            if self._should_close():
                with self._lock:
                    self._transition_state(CircuitState.CLOSED)

            return result

        except Exception as e:
            self._update_stats(success=False)

            # Check if we should open the circuit
            if self._should_open():
                with self._lock:
                    self._transition_state(CircuitState.OPEN)

            raise

    async def call_async(self, operation: Callable[[], Any]) -> Any:
        """
        Execute async operation through circuit breaker

        Args:
            operation: Async function to execute

        Returns:
            Result of operation

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from the operation
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            with self._lock:
                if self.state == CircuitState.OPEN:
                    self._transition_state(CircuitState.HALF_OPEN)

        # Reject calls if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(self.key, self.state)

        # Execute operation with timeout
        try:
            result = await asyncio.wait_for(operation(), timeout=self.config.timeout)
            self._update_stats(success=True)

            # Check if we should close the circuit
            if self._should_close():
                with self._lock:
                    self._transition_state(CircuitState.CLOSED)

            return result

        except Exception as e:
            self._update_stats(success=False)

            # Check if we should open the circuit
            if self._should_open():
                with self._lock:
                    self._transition_state(CircuitState.OPEN)

            raise

    @contextmanager
    def guard(self):
        """
        Context manager for circuit breaker protection (synchronous)

        Usage:
            with breaker.guard():
                result = some_operation()
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            with self._lock:
                if self.state == CircuitState.OPEN:
                    self._transition_state(CircuitState.HALF_OPEN)

        # Reject calls if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(self.key, self.state)

        try:
            yield
            self._update_stats(success=True)

            # Check if we should close the circuit
            if self._should_close():
                with self._lock:
                    self._transition_state(CircuitState.CLOSED)

        except Exception as e:
            self._update_stats(success=False)

            # Check if we should open the circuit
            if self._should_open():
                with self._lock:
                    self._transition_state(CircuitState.OPEN)

            raise

    @asynccontextmanager
    async def guard_async(self):
        """
        Async context manager for circuit breaker protection

        Usage:
            async with breaker.guard_async():
                result = await some_async_operation()
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            with self._lock:
                if self.state == CircuitState.OPEN:
                    self._transition_state(CircuitState.HALF_OPEN)

        # Reject calls if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(self.key, self.state)

        try:
            yield
            self._update_stats(success=True)

            # Check if we should close the circuit
            if self._should_close():
                with self._lock:
                    self._transition_state(CircuitState.CLOSED)

        except Exception as e:
            self._update_stats(success=False)

            # Check if we should open the circuit
            if self._should_open():
                with self._lock:
                    self._transition_state(CircuitState.OPEN)

            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics"""
        return {
            "key": self.key,
            "state": self.state.value,
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "failure_rate": (
                self.stats.failed_calls / self.stats.total_calls
                if self.stats.total_calls > 0
                else 0.0
            ),
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
        }

    def reset(self):
        """Reset circuit breaker to closed state"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.stats = CircuitStats()

            log.info(
                f"Circuit breaker '{self.key}' manually reset",
                extra={"event_type": "circuit_breaker_reset", "circuit_key": self.key},
            )


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.RLock()


def get_circuit_breaker(
    key: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker for the given key

    Args:
        key: Unique identifier for the circuit breaker
        config: Configuration (only used when creating new circuit breaker)

    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if key not in _circuit_breakers:
            _circuit_breakers[key] = CircuitBreaker(key, config)
        return _circuit_breakers[key]


def circuit_breaker(key: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for adding circuit breaker protection to functions

    Args:
        key: Unique identifier for the circuit breaker
        config: Circuit breaker configuration
    """

    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(key, config)

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(lambda: func(*args, **kwargs))

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call(lambda: func(*args, **kwargs))

            return sync_wrapper

    return decorator


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all registered circuit breakers"""
    with _registry_lock:
        return {key: breaker.get_stats() for key, breaker in _circuit_breakers.items()}


def reset_all_circuit_breakers():
    """Reset all registered circuit breakers"""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()


def clear_circuit_breaker_registry():
    """Clear the circuit breaker registry (for testing)"""
    with _registry_lock:
        _circuit_breakers.clear()
