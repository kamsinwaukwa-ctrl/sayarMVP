"""
Configuration management API endpoints.

This module provides REST endpoints for managing system settings,
merchant settings, and feature flags with proper role-based access control.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.dependencies.auth import get_current_user, require_admin, require_auth
from src.services.config_service import ConfigurationService
from src.models.config import (
    SystemSettingCreate, SystemSettingUpdate, SystemSettingResponse,
    MerchantSettingCreate, MerchantSettingUpdate, MerchantSettingResponse,
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    MergedConfigurationResponse, ConfigurationQuery, BulkConfigurationUpdate,
    ConfigurationExport, ConfigurationImport, ConfigurationImportResult
)
from src.models.api import APIResponse, ErrorResponse
from src.models.auth import User
from src.config.settings import invalidate_config_cache
from src.utils.logger import log
from src.models.errors import NotFoundError, ValidationError, AuthzError


router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])


# =============================================================================
# System Settings Endpoints (Admin Only)
# =============================================================================

@router.post(
    "/system",
    response_model=APIResponse[SystemSettingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create system setting",
    description="Create a new system-wide setting (admin only)"
)
async def create_system_setting(
    setting: SystemSettingCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[SystemSettingResponse]:
    """Create a new system setting."""
    
    service = ConfigurationService(db)
    
    try:
        result = await service.create_system_setting(setting, current_user.role)
        
        # Invalidate cache
        invalidate_config_cache()
        
        return APIResponse(
            data=result,
            message="System setting created successfully"
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/system",
    response_model=APIResponse[List[SystemSettingResponse]],
    summary="List system settings",
    description="Get list of system settings with optional filtering"
)
async def list_system_settings(
    key_prefix: Optional[str] = Query(None, description="Filter by key prefix"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[List[SystemSettingResponse]]:
    """List system settings."""
    
    service = ConfigurationService(db)
    query = ConfigurationQuery(key_prefix=key_prefix, limit=limit, offset=offset)
    
    settings = await service.list_system_settings(query)
    
    return APIResponse(
        data=settings,
        message=f"Retrieved {len(settings)} system settings"
    )


@router.get(
    "/system/{key}",
    response_model=APIResponse[SystemSettingResponse],
    summary="Get system setting",
    description="Get a specific system setting by key"
)
async def get_system_setting(
    key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[SystemSettingResponse]:
    """Get a system setting by key."""
    
    service = ConfigurationService(db)
    setting = await service.get_system_setting(key)
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System setting '{key}' not found"
        )
    
    return APIResponse(
        data=setting,
        message="System setting retrieved successfully"
    )


@router.put(
    "/system/{key}",
    response_model=APIResponse[SystemSettingResponse],
    summary="Update system setting",
    description="Update an existing system setting (admin only)"
)
async def update_system_setting(
    key: str,
    update_data: SystemSettingUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[SystemSettingResponse]:
    """Update a system setting."""
    
    service = ConfigurationService(db)
    
    try:
        result = await service.update_system_setting(key, update_data, current_user.role)
        
        # Invalidate cache
        invalidate_config_cache()
        
        return APIResponse(
            data=result,
            message="System setting updated successfully"
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/system/{key}",
    response_model=APIResponse[bool],
    summary="Delete system setting",
    description="Delete a system setting (admin only)"
)
async def delete_system_setting(
    key: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Delete a system setting."""
    
    service = ConfigurationService(db)
    
    try:
        await service.delete_system_setting(key, current_user.role)
        
        # Invalidate cache
        invalidate_config_cache()
        
        return APIResponse(
            data=True,
            message="System setting deleted successfully"
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# =============================================================================
# Merchant Settings Endpoints
# =============================================================================

@router.post(
    "/merchant",
    response_model=APIResponse[MerchantSettingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create merchant setting",
    description="Create a new merchant-specific setting"
)
async def create_merchant_setting(
    setting: MerchantSettingCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MerchantSettingResponse]:
    """Create a new merchant setting."""
    
    service = ConfigurationService(db)
    
    try:
        result = await service.create_merchant_setting(
            current_user.merchant_id, 
            setting, 
            current_user.role
        )
        
        # Invalidate cache for this merchant
        invalidate_config_cache(current_user.merchant_id)
        
        return APIResponse(
            data=result,
            message="Merchant setting created successfully"
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/merchant",
    response_model=APIResponse[List[MerchantSettingResponse]],
    summary="List merchant settings",
    description="Get list of merchant settings for current user's merchant"
)
async def list_merchant_settings(
    key_prefix: Optional[str] = Query(None, description="Filter by key prefix"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[List[MerchantSettingResponse]]:
    """List merchant settings."""
    
    service = ConfigurationService(db)
    query = ConfigurationQuery(key_prefix=key_prefix, limit=limit, offset=offset)
    
    settings = await service.list_merchant_settings(current_user.merchant_id, query)
    
    return APIResponse(
        data=settings,
        message=f"Retrieved {len(settings)} merchant settings"
    )


@router.get(
    "/merchant/{key}",
    response_model=APIResponse[MerchantSettingResponse],
    summary="Get merchant setting",
    description="Get a specific merchant setting by key"
)
async def get_merchant_setting(
    key: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MerchantSettingResponse]:
    """Get a merchant setting by key."""
    
    service = ConfigurationService(db)
    setting = await service.get_merchant_setting(current_user.merchant_id, key)
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant setting '{key}' not found"
        )
    
    return APIResponse(
        data=setting,
        message="Merchant setting retrieved successfully"
    )


@router.put(
    "/merchant/{key}",
    response_model=APIResponse[MerchantSettingResponse],
    summary="Update merchant setting",
    description="Update an existing merchant setting"
)
async def update_merchant_setting(
    key: str,
    update_data: MerchantSettingUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MerchantSettingResponse]:
    """Update a merchant setting."""
    
    service = ConfigurationService(db)
    
    try:
        result = await service.update_merchant_setting(
            current_user.merchant_id, 
            key, 
            update_data, 
            current_user.role
        )
        
        # Invalidate cache for this merchant
        invalidate_config_cache(current_user.merchant_id)
        
        return APIResponse(
            data=result,
            message="Merchant setting updated successfully"
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/merchant/{key}",
    response_model=APIResponse[bool],
    summary="Delete merchant setting",
    description="Delete a merchant setting"
)
async def delete_merchant_setting(
    key: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Delete a merchant setting."""
    
    service = ConfigurationService(db)
    
    try:
        await service.delete_merchant_setting(
            current_user.merchant_id, 
            key, 
            current_user.role
        )
        
        # Invalidate cache for this merchant
        invalidate_config_cache(current_user.merchant_id)
        
        return APIResponse(
            data=True,
            message="Merchant setting deleted successfully"
        )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# =============================================================================
# Feature Flag Endpoints
# =============================================================================

@router.post(
    "/feature-flags",
    response_model=APIResponse[FeatureFlagResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create feature flag",
    description="Create a new feature flag (global flags require admin role)"
)
async def create_feature_flag(
    flag: FeatureFlagCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[FeatureFlagResponse]:
    """Create a new feature flag."""
    
    # If creating merchant-specific flag, use current user's merchant_id
    if flag.merchant_id is None and current_user.role != "admin":
        flag.merchant_id = current_user.merchant_id
    
    service = ConfigurationService(db)
    
    try:
        result = await service.create_feature_flag(flag, current_user.role)
        
        # Invalidate cache
        if flag.merchant_id:
            invalidate_config_cache(flag.merchant_id)
        else:
            invalidate_config_cache()  # Global flag affects all
        
        return APIResponse(
            data=result,
            message="Feature flag created successfully"
        )
        
    except (ValidationError, AuthzError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/feature-flags",
    response_model=APIResponse[List[FeatureFlagResponse]],
    summary="List feature flags",
    description="Get list of feature flags (includes global and merchant-specific)"
)
async def list_feature_flags(
    include_global: bool = Query(True, description="Include global feature flags"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[List[FeatureFlagResponse]]:
    """List feature flags."""
    
    service = ConfigurationService(db)
    query = ConfigurationQuery(limit=limit, offset=offset)
    
    flags = await service.list_feature_flags(
        merchant_id=current_user.merchant_id,
        include_global=include_global,
        query=query
    )
    
    return APIResponse(
        data=flags,
        message=f"Retrieved {len(flags)} feature flags"
    )


@router.get(
    "/feature-flags/{name}",
    response_model=APIResponse[FeatureFlagResponse],
    summary="Get feature flag",
    description="Get a specific feature flag by name"
)
async def get_feature_flag(
    name: str,
    global_flag: bool = Query(False, description="Get global flag instead of merchant-specific"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[FeatureFlagResponse]:
    """Get a feature flag by name."""
    
    service = ConfigurationService(db)
    merchant_id = None if global_flag else current_user.merchant_id
    
    flag = await service.get_feature_flag(name, merchant_id)
    
    if not flag:
        scope = "global" if global_flag else "merchant-specific"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found ({scope})"
        )
    
    return APIResponse(
        data=flag,
        message="Feature flag retrieved successfully"
    )


@router.put(
    "/feature-flags/{name}",
    response_model=APIResponse[FeatureFlagResponse],
    summary="Update feature flag",
    description="Update an existing feature flag"
)
async def update_feature_flag(
    name: str,
    update_data: FeatureFlagUpdate,
    global_flag: bool = Query(False, description="Update global flag instead of merchant-specific"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[FeatureFlagResponse]:
    """Update a feature flag."""
    
    service = ConfigurationService(db)
    merchant_id = None if global_flag else current_user.merchant_id
    
    try:
        result = await service.update_feature_flag(
            name, 
            merchant_id, 
            update_data, 
            current_user.role
        )
        
        # Invalidate cache
        if merchant_id:
            invalidate_config_cache(merchant_id)
        else:
            invalidate_config_cache()  # Global flag affects all
        
        return APIResponse(
            data=result,
            message="Feature flag updated successfully"
        )
        
    except (NotFoundError, AuthzError) as e:
        if isinstance(e, AuthzError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )


@router.delete(
    "/feature-flags/{name}",
    response_model=APIResponse[bool],
    summary="Delete feature flag",
    description="Delete a feature flag"
)
async def delete_feature_flag(
    name: str,
    global_flag: bool = Query(False, description="Delete global flag instead of merchant-specific"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Delete a feature flag."""
    
    service = ConfigurationService(db)
    merchant_id = None if global_flag else current_user.merchant_id
    
    try:
        await service.delete_feature_flag(name, merchant_id, current_user.role)
        
        # Invalidate cache
        if merchant_id:
            invalidate_config_cache(merchant_id)
        else:
            invalidate_config_cache()  # Global flag affects all
        
        return APIResponse(
            data=True,
            message="Feature flag deleted successfully"
        )
        
    except (NotFoundError, AuthzError) as e:
        if isinstance(e, AuthzError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )


# =============================================================================
# Merged Configuration Endpoints
# =============================================================================

@router.get(
    "/merged",
    response_model=APIResponse[MergedConfigurationResponse],
    summary="Get merged configuration",
    description="Get merged configuration with proper hierarchy for current merchant"
)
async def get_merged_configuration(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MergedConfigurationResponse]:
    """Get merged configuration for current merchant."""
    
    service = ConfigurationService(db)
    merged_config = await service.get_merged_configuration(current_user.merchant_id)
    
    return APIResponse(
        data=merged_config,
        message="Merged configuration retrieved successfully"
    )


@router.post(
    "/bulk-update",
    response_model=APIResponse[MergedConfigurationResponse],
    summary="Bulk update configuration",
    description="Perform bulk updates to configuration settings and feature flags"
)
async def bulk_update_configuration(
    bulk_update: BulkConfigurationUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[MergedConfigurationResponse]:
    """Perform bulk configuration updates."""
    
    service = ConfigurationService(db)
    
    try:
        result = await service.bulk_update_configuration(
            current_user.merchant_id, 
            bulk_update, 
            current_user.role
        )
        
        # Invalidate cache
        invalidate_config_cache(current_user.merchant_id)
        if bulk_update.system_settings and current_user.role == "admin":
            invalidate_config_cache()  # System settings affect all merchants
        
        return APIResponse(
            data=result,
            message="Bulk configuration update completed successfully"
        )
        
    except (ValidationError, AuthzError) as e:
        if isinstance(e, AuthzError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# =============================================================================
# Administrative Endpoints
# =============================================================================

@router.post(
    "/cache/invalidate",
    response_model=APIResponse[bool],
    summary="Invalidate configuration cache",
    description="Manually invalidate configuration cache (admin only)"
)
async def invalidate_configuration_cache(
    merchant_id: Optional[UUID] = Query(None, description="Specific merchant ID to invalidate"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Manually invalidate configuration cache."""
    
    invalidate_config_cache(merchant_id)
    
    scope = f"merchant {merchant_id}" if merchant_id else "all merchants"
    
    log.info(
        "configuration_cache_invalidated_manually",
        extra={
            "merchant_id": str(merchant_id) if merchant_id else None,
            "admin_user": current_user.email
        }
    )
    
    return APIResponse(
        data=True,
        message=f"Configuration cache invalidated for {scope}"
    )