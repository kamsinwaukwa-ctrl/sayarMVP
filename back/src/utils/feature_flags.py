"""
Feature flags module with merchant override evaluation.

This module provides runtime feature flag evaluation with support for
global flags, merchant-specific overrides, and environment-based configuration.
"""

import os
from typing import Dict, Any, Optional, Set, List, Callable
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import get_merchant_config, get_feature_flag
from src.models.config import MergedConfigurationResponse
from src.utils.logger import log


class FeatureFlagStrategy(str, Enum):
    """Feature flag evaluation strategies."""

    BOOLEAN = "boolean"  # Simple on/off
    PERCENTAGE = "percentage"  # Percentage-based rollout
    USER_LIST = "user_list"  # Specific user allowlist
    MERCHANT_LIST = "merchant_list"  # Specific merchant allowlist
    AB_TEST = "ab_test"  # A/B testing support


@dataclass
class FeatureFlagConfig:
    """Configuration for feature flag evaluation."""

    name: str
    enabled: bool = False
    strategy: FeatureFlagStrategy = FeatureFlagStrategy.BOOLEAN
    config: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.strategy == FeatureFlagStrategy.PERCENTAGE:
            percentage = self.config.get("percentage", 0)
            if not 0 <= percentage <= 100:
                raise ValueError("Percentage must be between 0 and 100")

        elif self.strategy in [
            FeatureFlagStrategy.USER_LIST,
            FeatureFlagStrategy.MERCHANT_LIST,
        ]:
            allowed_list = self.config.get("allowed_list", [])
            if not isinstance(allowed_list, list):
                raise ValueError("allowed_list must be a list")


class FeatureFlagManager:
    """
    Feature flag manager with caching and merchant override support.
    """

    def __init__(self):
        """Initialize feature flag manager."""
        self._cache: Dict[str, MergedConfigurationResponse] = {}
        self._flag_configs: Dict[str, FeatureFlagConfig] = {}
        self._listeners: List[Callable[[str, bool, Optional[UUID]], None]] = []

        # Initialize built-in feature flags
        self._initialize_builtin_flags()

    def register_flag(self, flag_config: FeatureFlagConfig) -> None:
        """
        Register a feature flag configuration.

        Args:
            flag_config: Feature flag configuration
        """
        self._flag_configs[flag_config.name] = flag_config
        log.info(
            "feature_flag_registered",
            extra={
                "flag_name": flag_config.name,
                "strategy": flag_config.strategy,
                "enabled": flag_config.enabled,
            },
        )

    def add_listener(
        self, callback: Callable[[str, bool, Optional[UUID]], None]
    ) -> None:
        """
        Add a listener for feature flag changes.

        Args:
            callback: Callback function (flag_name, enabled, merchant_id)
        """
        self._listeners.append(callback)

    async def is_enabled(
        self,
        flag_name: str,
        merchant_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
        use_cache: bool = True,
    ) -> bool:
        """
        Check if a feature flag is enabled for the given context.

        Args:
            flag_name: Feature flag name
            merchant_id: Optional merchant ID for merchant-specific evaluation
            user_id: Optional user ID for user-specific evaluation
            db: Optional database session for fresh data
            use_cache: Whether to use cached configuration

        Returns:
            True if feature flag is enabled, False otherwise
        """

        # Get merchant configuration if merchant_id provided
        merchant_config = None
        if merchant_id and db:
            try:
                merchant_config = await get_merchant_config(db, merchant_id, use_cache)
            except Exception as e:
                log.warning(
                    "feature_flag_config_load_failed",
                    extra={
                        "flag_name": flag_name,
                        "merchant_id": str(merchant_id),
                        "error": str(e),
                    },
                )

        # Get base flag value (handles environment overrides and merchant config)
        base_enabled = get_feature_flag(flag_name, False, merchant_config)

        # Get flag configuration for advanced evaluation
        flag_config = self._flag_configs.get(flag_name)
        if not flag_config:
            # No advanced config, return base value
            return base_enabled

        # Apply strategy-based evaluation
        try:
            result = await self._evaluate_flag_strategy(
                flag_config, base_enabled, merchant_id, user_id, merchant_config
            )

            log.debug(
                "feature_flag_evaluated",
                extra={
                    "flag_name": flag_name,
                    "merchant_id": str(merchant_id) if merchant_id else None,
                    "user_id": str(user_id) if user_id else None,
                    "strategy": flag_config.strategy,
                    "result": result,
                },
            )

            return result

        except Exception as e:
            log.error(
                "feature_flag_evaluation_error",
                extra={
                    "flag_name": flag_name,
                    "merchant_id": str(merchant_id) if merchant_id else None,
                    "error": str(e),
                },
            )
            # Fall back to base value on error
            return base_enabled

    def is_enabled_sync(
        self,
        flag_name: str,
        merchant_config: Optional[MergedConfigurationResponse] = None,
    ) -> bool:
        """
        Synchronous version of feature flag evaluation.

        Note: This only supports basic boolean flags without advanced strategies.

        Args:
            flag_name: Feature flag name
            merchant_config: Pre-loaded merchant configuration

        Returns:
            True if feature flag is enabled, False otherwise
        """
        return get_feature_flag(flag_name, False, merchant_config)

    def get_enabled_flags(
        self, merchant_config: Optional[MergedConfigurationResponse] = None
    ) -> Set[str]:
        """
        Get set of all enabled feature flags.

        Args:
            merchant_config: Pre-loaded merchant configuration

        Returns:
            Set of enabled flag names
        """
        enabled_flags = set()

        # Check registered flags
        for flag_name in self._flag_configs.keys():
            if self.is_enabled_sync(flag_name, merchant_config):
                enabled_flags.add(flag_name)

        # Check merchant config for additional flags
        if merchant_config:
            for flag_name, enabled in merchant_config.feature_flags.items():
                if enabled:
                    enabled_flags.add(flag_name)

        return enabled_flags

    def get_flag_config(self, flag_name: str) -> Optional[FeatureFlagConfig]:
        """Get feature flag configuration."""
        return self._flag_configs.get(flag_name)

    def list_registered_flags(self) -> List[FeatureFlagConfig]:
        """Get list of all registered feature flags."""
        return list(self._flag_configs.values())

    # =========================================================================
    # Decorators and Context Managers
    # =========================================================================

    def requires_feature(
        self, flag_name: str, fallback_response: Any = None
    ) -> Callable:
        """
        Decorator to require a feature flag for function execution.

        Args:
            flag_name: Required feature flag name
            fallback_response: Response to return if flag is disabled

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    # Try to extract merchant_id from kwargs or function signature
                    merchant_id = kwargs.get("merchant_id")
                    db = kwargs.get("db")

                    if await self.is_enabled(flag_name, merchant_id, db=db):
                        return await func(*args, **kwargs)
                    else:
                        log.info(
                            "feature_flag_blocked_execution",
                            extra={
                                "flag_name": flag_name,
                                "function": func.__name__,
                                "merchant_id": (
                                    str(merchant_id) if merchant_id else None
                                ),
                            },
                        )
                        return fallback_response

                return async_wrapper
            else:

                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    merchant_config = kwargs.get("merchant_config")

                    if self.is_enabled_sync(flag_name, merchant_config):
                        return func(*args, **kwargs)
                    else:
                        log.info(
                            "feature_flag_blocked_execution",
                            extra={"flag_name": flag_name, "function": func.__name__},
                        )
                        return fallback_response

                return sync_wrapper

        return decorator

    @asynccontextmanager
    async def feature_context(
        self,
        flag_name: str,
        merchant_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
    ):
        """
        Context manager for feature flag evaluation.

        Args:
            flag_name: Feature flag name
            merchant_id: Optional merchant ID
            db: Optional database session

        Yields:
            bool: Whether the feature is enabled
        """
        enabled = await self.is_enabled(flag_name, merchant_id, db=db)

        log.debug(
            "feature_context_entered",
            extra={
                "flag_name": flag_name,
                "merchant_id": str(merchant_id) if merchant_id else None,
                "enabled": enabled,
            },
        )

        try:
            yield enabled
        finally:
            log.debug(
                "feature_context_exited",
                extra={
                    "flag_name": flag_name,
                    "merchant_id": str(merchant_id) if merchant_id else None,
                },
            )

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _initialize_builtin_flags(self) -> None:
        """Initialize built-in feature flags."""

        builtin_flags = [
            FeatureFlagConfig(
                name="enhanced_analytics",
                description="Enhanced analytics dashboard with advanced metrics",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="bulk_import",
                description="Bulk product import functionality",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="advanced_inventory",
                description="Advanced inventory management features",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="custom_webhooks",
                description="Custom webhook configuration",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="multi_currency",
                description="Multi-currency support",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="subscription_billing",
                description="Subscription-based billing",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="ai_recommendations",
                description="AI-powered product recommendations",
                strategy=FeatureFlagStrategy.PERCENTAGE,
                config={"percentage": 10},  # 10% rollout
            ),
            FeatureFlagConfig(
                name="social_media_integration",
                description="Social media platform integration",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="loyalty_program",
                description="Customer loyalty program features",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
            FeatureFlagConfig(
                name="advanced_reporting",
                description="Advanced reporting and export features",
                strategy=FeatureFlagStrategy.BOOLEAN,
            ),
        ]

        for flag in builtin_flags:
            self.register_flag(flag)

    async def _evaluate_flag_strategy(
        self,
        flag_config: FeatureFlagConfig,
        base_enabled: bool,
        merchant_id: Optional[UUID],
        user_id: Optional[UUID],
        merchant_config: Optional[MergedConfigurationResponse],
    ) -> bool:
        """Evaluate feature flag based on strategy."""

        # If base flag is disabled, don't proceed with advanced evaluation
        if not base_enabled and flag_config.strategy != FeatureFlagStrategy.BOOLEAN:
            return False

        if flag_config.strategy == FeatureFlagStrategy.BOOLEAN:
            return base_enabled

        elif flag_config.strategy == FeatureFlagStrategy.PERCENTAGE:
            if not base_enabled:
                return False

            percentage = flag_config.config.get("percentage", 0)
            # Simple hash-based percentage calculation
            if merchant_id:
                hash_value = hash(str(merchant_id)) % 100
                return hash_value < percentage
            return False

        elif flag_config.strategy == FeatureFlagStrategy.MERCHANT_LIST:
            if not base_enabled:
                return False

            allowed_merchants = flag_config.config.get("allowed_list", [])
            return str(merchant_id) in allowed_merchants if merchant_id else False

        elif flag_config.strategy == FeatureFlagStrategy.USER_LIST:
            if not base_enabled:
                return False

            allowed_users = flag_config.config.get("allowed_list", [])
            return str(user_id) in allowed_users if user_id else False

        elif flag_config.strategy == FeatureFlagStrategy.AB_TEST:
            if not base_enabled:
                return False

            # Simple A/B test based on merchant ID hash
            if merchant_id:
                hash_value = hash(str(merchant_id))
                group = "A" if hash_value % 2 == 0 else "B"
                enabled_groups = flag_config.config.get("enabled_groups", ["A"])
                return group in enabled_groups
            return False

        # Default fallback
        return base_enabled

    def _notify_listeners(
        self, flag_name: str, enabled: bool, merchant_id: Optional[UUID] = None
    ) -> None:
        """Notify registered listeners of flag changes."""
        for listener in self._listeners:
            try:
                listener(flag_name, enabled, merchant_id)
            except Exception as e:
                log.error(
                    "feature_flag_listener_error",
                    extra={
                        "flag_name": flag_name,
                        "listener": listener.__name__,
                        "error": str(e),
                    },
                )


# =========================================================================
# Global Feature Flag Manager
# =========================================================================

# Global instance for easy access throughout the application
feature_flags = FeatureFlagManager()


# =========================================================================
# Convenience Functions and Decorators
# =========================================================================


async def is_feature_enabled(
    flag_name: str,
    merchant_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Convenience function to check if a feature is enabled."""
    return await feature_flags.is_enabled(flag_name, merchant_id, user_id, db)


def is_feature_enabled_sync(
    flag_name: str, merchant_config: Optional[MergedConfigurationResponse] = None
) -> bool:
    """Synchronous convenience function to check if a feature is enabled."""
    return feature_flags.is_enabled_sync(flag_name, merchant_config)


def requires_feature(flag_name: str, fallback_response: Any = None) -> Callable:
    """Convenience decorator for requiring feature flags."""
    return feature_flags.requires_feature(flag_name, fallback_response)


def get_enabled_features(
    merchant_config: Optional[MergedConfigurationResponse] = None,
) -> Set[str]:
    """Convenience function to get all enabled features."""
    return feature_flags.get_enabled_flags(merchant_config)


# =========================================================================
# Feature Flag Utilities
# =========================================================================


def create_feature_flag_middleware():
    """Create middleware to inject feature flags into request context."""

    async def feature_flag_middleware(request, call_next):
        """Middleware to add feature flag context to requests."""

        # Extract merchant_id from request context if available
        merchant_id = getattr(request.state, "merchant_id", None)

        if merchant_id:
            # Load merchant configuration
            try:
                db = getattr(request.state, "db", None)
                if db:
                    merchant_config = await get_merchant_config(db, merchant_id)
                    request.state.feature_flags = get_enabled_features(merchant_config)
                    request.state.merchant_config = merchant_config
            except Exception as e:
                log.warning(
                    "feature_flag_middleware_error",
                    extra={"merchant_id": str(merchant_id), "error": str(e)},
                )
                request.state.feature_flags = set()

        response = await call_next(request)
        return response

    return feature_flag_middleware
