"""
Configuration management models for the Sayar platform.

This module provides Pydantic models for system settings, merchant settings,
and feature flags with proper validation and type safety.
"""

from typing import Any, Dict, Optional, List, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum


class ConfigValueType(str, Enum):
    """Supported configuration value types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


class ConfigScope(str, Enum):
    """Configuration scope levels."""

    SYSTEM = "system"
    MERCHANT = "merchant"


# =============================================================================
# System Settings Models
# =============================================================================


class SystemSettingCreate(BaseModel):
    """Model for creating system settings."""

    key: str = Field(..., min_length=1, max_length=255, description="Setting key")
    value: Union[str, int, float, bool, Dict[str, Any]] = Field(
        ..., description="Setting value"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Setting description"
    )

    @validator("key")
    def validate_key_format(cls, v):
        """Ensure key follows dot notation convention."""
        if not v.replace("_", "").replace(".", "").replace("-", "").isalnum():
            raise ValueError(
                "Key must contain only alphanumeric characters, dots, hyphens, and underscores"
            )
        return v.lower()


class SystemSettingUpdate(BaseModel):
    """Model for updating system settings."""

    value: Optional[Union[str, int, float, bool, Dict[str, Any]]] = Field(
        None, description="New setting value"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Updated description"
    )


class SystemSettingResponse(BaseModel):
    """Model for system setting responses."""

    id: UUID
    key: str
    value: Union[str, int, float, bool, Dict[str, Any]]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Merchant Settings Models
# =============================================================================


class MerchantSettingCreate(BaseModel):
    """Model for creating merchant settings."""

    key: str = Field(..., min_length=1, max_length=255, description="Setting key")
    value: Union[str, int, float, bool, Dict[str, Any]] = Field(
        ..., description="Setting value"
    )

    @validator("key")
    def validate_key_format(cls, v):
        """Ensure key follows dot notation convention."""
        if not v.replace("_", "").replace(".", "").replace("-", "").isalnum():
            raise ValueError(
                "Key must contain only alphanumeric characters, dots, hyphens, and underscores"
            )
        return v.lower()


class MerchantSettingUpdate(BaseModel):
    """Model for updating merchant settings."""

    value: Union[str, int, float, bool, Dict[str, Any]] = Field(
        ..., description="New setting value"
    )


class MerchantSettingResponse(BaseModel):
    """Model for merchant setting responses."""

    id: UUID
    merchant_id: UUID
    key: str
    value: Union[str, int, float, bool, Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Feature Flag Models
# =============================================================================


class FeatureFlagCreate(BaseModel):
    """Model for creating feature flags."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Feature flag name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Feature flag description"
    )
    enabled: bool = Field(False, description="Whether the feature is enabled")
    merchant_id: Optional[UUID] = Field(
        None, description="Merchant ID for merchant-specific overrides"
    )

    @validator("name")
    def validate_name_format(cls, v):
        """Ensure name follows snake_case convention."""
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "Feature flag name must contain only alphanumeric characters and underscores"
            )
        return v.lower()


class FeatureFlagUpdate(BaseModel):
    """Model for updating feature flags."""

    description: Optional[str] = Field(
        None, max_length=500, description="Updated description"
    )
    enabled: Optional[bool] = Field(None, description="Updated enabled state")


class FeatureFlagResponse(BaseModel):
    """Model for feature flag responses."""

    id: UUID
    name: str
    description: Optional[str]
    enabled: bool
    merchant_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Configuration Query & Bulk Models
# =============================================================================


class ConfigurationQuery(BaseModel):
    """Model for querying configurations with filters."""

    scope: Optional[ConfigScope] = Field(None, description="Configuration scope filter")
    key_prefix: Optional[str] = Field(
        None, min_length=1, description="Filter by key prefix"
    )
    merchant_id: Optional[UUID] = Field(None, description="Merchant ID filter")
    limit: int = Field(50, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")


class BulkConfigurationUpdate(BaseModel):
    """Model for bulk configuration updates."""

    system_settings: Optional[
        Dict[str, Union[str, int, float, bool, Dict[str, Any]]]
    ] = Field(None, description="System settings to update")
    merchant_settings: Optional[
        Dict[str, Union[str, int, float, bool, Dict[str, Any]]]
    ] = Field(None, description="Merchant settings to update")
    feature_flags: Optional[Dict[str, bool]] = Field(
        None, description="Feature flags to update"
    )


# =============================================================================
# Merged Configuration Models
# =============================================================================


class MergedConfigurationResponse(BaseModel):
    """Model for merged configuration responses with hierarchy."""

    system_settings: Dict[str, Union[str, int, float, bool, Dict[str, Any]]] = Field(
        default_factory=dict
    )
    merchant_settings: Dict[str, Union[str, int, float, bool, Dict[str, Any]]] = Field(
        default_factory=dict
    )
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    effective_config: Dict[str, Union[str, int, float, bool, Dict[str, Any]]] = Field(
        default_factory=dict
    )
    merchant_id: Optional[UUID] = None


class ConfigurationHierarchy(BaseModel):
    """Model representing configuration hierarchy and precedence."""

    key: str
    system_value: Optional[Union[str, int, float, bool, Dict[str, Any]]] = None
    merchant_value: Optional[Union[str, int, float, bool, Dict[str, Any]]] = None
    effective_value: Union[str, int, float, bool, Dict[str, Any]]
    source: str = Field(
        ..., description="Source of the effective value (system|merchant)"
    )


# =============================================================================
# Configuration Validation Models
# =============================================================================


class ConfigurationValidation(BaseModel):
    """Model for configuration validation results."""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ConfigurationSchema(BaseModel):
    """Model for configuration schema definitions."""

    key: str
    value_type: ConfigValueType
    required: bool = False
    default_value: Optional[Union[str, int, float, bool, Dict[str, Any]]] = None
    description: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None


# =============================================================================
# Configuration Export/Import Models
# =============================================================================


class ConfigurationExport(BaseModel):
    """Model for configuration export."""

    system_settings: List[SystemSettingResponse]
    merchant_settings: List[MerchantSettingResponse]
    feature_flags: List[FeatureFlagResponse]
    export_timestamp: datetime
    schema_version: str = "1.0"


class ConfigurationImport(BaseModel):
    """Model for configuration import."""

    system_settings: Optional[List[SystemSettingCreate]] = None
    merchant_settings: Optional[List[MerchantSettingCreate]] = None
    feature_flags: Optional[List[FeatureFlagCreate]] = None
    overwrite_existing: bool = False
    dry_run: bool = False


class ConfigurationImportResult(BaseModel):
    """Model for configuration import results."""

    success: bool
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
