"""
Centralized configuration loading with hierarchy and caching.

This module provides a settings loader that combines system settings,
merchant settings, and environment variables with proper precedence
and caching for performance.
"""

import os
import json
from typing import Any, Dict, Optional, Union, TypeVar, Generic
from datetime import datetime, timedelta
from uuid import UUID
from functools import lru_cache
from dataclasses import dataclass
import asyncio
from threading import Lock

from sqlalchemy.ext.asyncio import AsyncSession
from src.services.config_service import ConfigurationService
from src.models.config import MergedConfigurationResponse
from src.utils.logger import log

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with expiration."""

    value: T
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class SettingsLoader:
    """
    Centralized settings loader with caching and hierarchy support.

    Priority order (highest to lowest):
    1. Environment variables
    2. Merchant-specific settings
    3. System-wide settings
    4. Default values
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize settings loader with cache TTL."""
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = Lock()

        # Environment variable prefix for configuration
        self.env_prefix = "SAYAR_"

    async def get_merged_config(
        self, db: AsyncSession, merchant_id: UUID, use_cache: bool = True
    ) -> MergedConfigurationResponse:
        """
        Get merged configuration for a merchant with caching.

        Args:
            db: Database session
            merchant_id: Merchant ID
            use_cache: Whether to use cached values

        Returns:
            Merged configuration response
        """
        cache_key = f"config:{merchant_id}"

        # Check cache first
        if use_cache:
            cached_config = self._get_from_cache(cache_key)
            if cached_config:
                log.debug(
                    "configuration_cache_hit", extra={"merchant_id": str(merchant_id)}
                )
                return cached_config

        # Load from database
        config_service = ConfigurationService(db)
        merged_config = await config_service.get_merged_configuration(merchant_id)

        # Enhance with environment variables
        enhanced_config = self._apply_environment_overrides(merged_config)

        # Cache the result
        if use_cache:
            self._set_cache(cache_key, enhanced_config)

        log.debug(
            "configuration_loaded",
            extra={
                "merchant_id": str(merchant_id),
                "system_settings_count": len(enhanced_config.system_settings),
                "merchant_settings_count": len(enhanced_config.merchant_settings),
                "feature_flags_count": len(enhanced_config.feature_flags),
            },
        )

        return enhanced_config

    def get_setting(
        self,
        key: str,
        default: T = None,
        setting_type: type = str,
        merchant_config: Optional[MergedConfigurationResponse] = None,
    ) -> T:
        """
        Get a configuration setting with proper hierarchy.

        Args:
            key: Setting key
            default: Default value if not found
            setting_type: Expected type of the setting
            merchant_config: Pre-loaded merchant configuration

        Returns:
            Setting value with proper type conversion
        """

        # 1. Check environment variables first (highest priority)
        env_key = f"{self.env_prefix}{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._convert_value(env_value, setting_type, default)

        # 2. Check merchant configuration if provided
        if merchant_config:
            # Check effective config (already includes hierarchy)
            if key in merchant_config.effective_config:
                value = merchant_config.effective_config[key]
                return self._convert_value(value, setting_type, default)

        # 3. Fall back to default
        return default

    def get_feature_flag(
        self,
        flag_name: str,
        default: bool = False,
        merchant_config: Optional[MergedConfigurationResponse] = None,
    ) -> bool:
        """
        Get a feature flag value with merchant override support.

        Args:
            flag_name: Feature flag name
            default: Default value if flag not found
            merchant_config: Pre-loaded merchant configuration

        Returns:
            Feature flag value
        """

        # Check environment override first
        env_key = f"{self.env_prefix}FEATURE_{flag_name.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._convert_value(env_value, bool, default)

        # Check merchant configuration
        if merchant_config and flag_name in merchant_config.feature_flags:
            return merchant_config.feature_flags[flag_name]

        # Fall back to default
        return default

    def invalidate_cache(self, merchant_id: Optional[UUID] = None) -> None:
        """
        Invalidate configuration cache.

        Args:
            merchant_id: Specific merchant ID to invalidate, or None for all
        """
        with self._cache_lock:
            if merchant_id:
                cache_key = f"config:{merchant_id}"
                self._cache.pop(cache_key, None)
                log.info(
                    "configuration_cache_invalidated",
                    extra={"merchant_id": str(merchant_id)},
                )
            else:
                self._cache.clear()
                log.info("configuration_cache_cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values() if entry.is_expired()
            )

            return {
                "total_entries": total_entries,
                "active_entries": total_entries - expired_entries,
                "expired_entries": expired_entries,
                "cache_ttl_seconds": self.cache_ttl.total_seconds(),
            }

    # =========================================================================
    # Configuration Presets and Templates
    # =========================================================================

    def get_default_merchant_config(self) -> Dict[str, Any]:
        """Get default configuration template for new merchants."""
        return {
            # Business settings
            "business.currency": "NGN",
            "business.timezone": "Africa/Lagos",
            "business.language": "en",
            # WhatsApp settings
            "whatsapp.welcome_message": "Welcome to our store! How can we help you today?",
            "whatsapp.order_confirmation_template": True,
            "whatsapp.auto_reply_enabled": True,
            # Catalog settings
            "catalog.sync_enabled": True,
            "catalog.auto_update_inventory": True,
            "catalog.show_out_of_stock": False,
            # Payment settings
            "payments.auto_capture": True,
            "payments.receipt_enabled": True,
            "payments.refund_window_days": 7,
            # Notification settings
            "notifications.order_created": True,
            "notifications.payment_received": True,
            "notifications.low_stock_threshold": 5,
            # Rate limiting settings
            "rate_limits.api_requests_per_minute": 60,
            "rate_limits.whatsapp_messages_per_hour": 1000,
        }

    def get_default_feature_flags(self) -> Dict[str, bool]:
        """Get default feature flags for new merchants."""
        return {
            "enhanced_analytics": False,
            "bulk_import": True,
            "advanced_inventory": False,
            "custom_webhooks": False,
            "multi_currency": False,
            "subscription_billing": False,
            "ai_recommendations": False,
            "social_media_integration": True,
            "loyalty_program": False,
            "advanced_reporting": False,
        }

    # =========================================================================
    # Environment Configuration Loading
    # =========================================================================

    @lru_cache(maxsize=128)
    def get_environment_config(self) -> Dict[str, Any]:
        """Get all environment-based configuration with caching."""
        config = {}

        # Scan for all SAYAR_ prefixed environment variables
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Convert SAYAR_BUSINESS_CURRENCY to business.currency
                config_key = key[len(self.env_prefix) :].lower().replace("_", ".")
                config[config_key] = value

        return config

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_from_cache(self, key: str) -> Optional[MergedConfigurationResponse]:
        """Get value from cache if not expired."""
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return entry.value
            elif entry:  # Expired
                del self._cache[key]
            return None

    def _set_cache(self, key: str, value: MergedConfigurationResponse) -> None:
        """Set value in cache with expiration."""
        with self._cache_lock:
            expires_at = datetime.utcnow() + self.cache_ttl
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def _apply_environment_overrides(
        self, config: MergedConfigurationResponse
    ) -> MergedConfigurationResponse:
        """Apply environment variable overrides to configuration."""
        env_config = self.get_environment_config()

        # Create a copy of the effective config
        enhanced_effective_config = dict(config.effective_config)

        # Apply environment overrides
        for key, value in env_config.items():
            if key.startswith("feature."):
                # Handle feature flags
                flag_name = key[8:]  # Remove 'feature.' prefix
                config.feature_flags[flag_name] = self._convert_value(value, bool)
            else:
                # Handle regular settings
                enhanced_effective_config[key] = value

        # Create new response with environment overrides
        return MergedConfigurationResponse(
            system_settings=config.system_settings,
            merchant_settings=config.merchant_settings,
            feature_flags=config.feature_flags,
            effective_config=enhanced_effective_config,
            merchant_id=config.merchant_id,
        )

    def _convert_value(self, value: Any, target_type: type, default: Any = None) -> Any:
        """Convert value to target type with error handling."""
        if value is None:
            return default

        try:
            if target_type == bool:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on", "enabled")
                return bool(value)

            elif target_type == int:
                return int(value)

            elif target_type == float:
                return float(value)

            elif target_type == str:
                return str(value)

            elif target_type == dict or target_type == Dict:
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
                return dict(value)

            elif target_type == list or target_type == List:
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
                return list(value)

            else:
                return target_type(value)

        except (ValueError, TypeError, json.JSONDecodeError) as e:
            log.warning(
                "configuration_type_conversion_failed",
                extra={
                    "value": str(value),
                    "target_type": target_type.__name__,
                    "error": str(e),
                },
            )
            return default


# =========================================================================
# Global Settings Loader Instance
# =========================================================================

# Global instance for easy access throughout the application
settings_loader = SettingsLoader()


# =========================================================================
# Convenience Functions
# =========================================================================


async def get_merchant_config(
    db: AsyncSession, merchant_id: UUID, use_cache: bool = True
) -> MergedConfigurationResponse:
    """Convenience function to get merchant configuration."""
    return await settings_loader.get_merged_config(db, merchant_id, use_cache)


def get_setting(
    key: str,
    default: T = None,
    setting_type: type = str,
    merchant_config: Optional[MergedConfigurationResponse] = None,
) -> T:
    """Convenience function to get a setting value."""
    return settings_loader.get_setting(key, default, setting_type, merchant_config)


def get_feature_flag(
    flag_name: str,
    default: bool = False,
    merchant_config: Optional[MergedConfigurationResponse] = None,
) -> bool:
    """Convenience function to get a feature flag value."""
    return settings_loader.get_feature_flag(flag_name, default, merchant_config)


def invalidate_config_cache(merchant_id: Optional[UUID] = None) -> None:
    """Convenience function to invalidate configuration cache."""
    settings_loader.invalidate_cache(merchant_id)
