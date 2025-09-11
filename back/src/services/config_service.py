"""
Configuration service for managing system settings, merchant settings, and feature flags.

This service provides business logic for CRUD operations with proper RLS enforcement
and multi-tenant isolation.
"""

from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime

from src.models.config import (
    SystemSettingCreate, SystemSettingUpdate, SystemSettingResponse,
    MerchantSettingCreate, MerchantSettingUpdate, MerchantSettingResponse,
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    MergedConfigurationResponse, ConfigurationQuery, BulkConfigurationUpdate,
    ConfigurationValidation, ConfigurationExport, ConfigurationImport,
    ConfigurationImportResult
)
from src.models.database import SystemSetting, MerchantSetting, FeatureFlag
from src.models.errors import NotFoundError, ValidationError, AuthzError
from src.utils.logger import log


class ConfigurationService:
    """Service for managing configuration settings and feature flags."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # System Settings Management
    # =========================================================================
    
    async def create_system_setting(
        self, 
        setting: SystemSettingCreate,
        current_user_role: str
    ) -> SystemSettingResponse:
        """Create a new system setting (admin only)."""
        if current_user_role != "admin":
            raise AuthzError("Only admins can create system settings")
        
        # Check if setting already exists
        existing = await self._get_system_setting_by_key(setting.key)
        if existing:
            raise ValidationError(f"System setting with key '{setting.key}' already exists")
        
        # Create new setting
        db_setting = SystemSetting(
            key=setting.key,
            value=setting.value,
            description=setting.description
        )
        
        self.db.add(db_setting)
        await self.db.commit()
        await self.db.refresh(db_setting)
        
        log.info(
            "system_setting_created",
            extra={
                "setting_key": setting.key,
                "user_role": current_user_role
            }
        )
        
        return SystemSettingResponse.from_orm(db_setting)
    
    async def get_system_setting(self, key: str) -> Optional[SystemSettingResponse]:
        """Get a system setting by key."""
        db_setting = await self._get_system_setting_by_key(key)
        return SystemSettingResponse.from_orm(db_setting) if db_setting else None
    
    async def list_system_settings(
        self, 
        query: ConfigurationQuery
    ) -> List[SystemSettingResponse]:
        """List system settings with optional filtering."""
        stmt = select(SystemSetting)
        
        if query.key_prefix:
            stmt = stmt.where(SystemSetting.key.like(f"{query.key_prefix}%"))
        
        stmt = stmt.offset(query.offset).limit(query.limit)
        result = await self.db.execute(stmt)
        settings = result.scalars().all()
        
        return [SystemSettingResponse.from_orm(setting) for setting in settings]
    
    async def update_system_setting(
        self, 
        key: str, 
        update_data: SystemSettingUpdate,
        current_user_role: str
    ) -> SystemSettingResponse:
        """Update a system setting (admin only)."""
        if current_user_role != "admin":
            raise AuthzError("Only admins can update system settings")
        
        db_setting = await self._get_system_setting_by_key(key)
        if not db_setting:
            raise NotFoundError(f"System setting with key '{key}' not found")
        
        # Update fields
        if update_data.value is not None:
            db_setting.value = update_data.value
        if update_data.description is not None:
            db_setting.description = update_data.description
        
        db_setting.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_setting)
        
        log.info(
            "system_setting_updated",
            extra={
                "setting_key": key,
                "user_role": current_user_role
            }
        )
        
        return SystemSettingResponse.from_orm(db_setting)
    
    async def delete_system_setting(
        self, 
        key: str,
        current_user_role: str
    ) -> bool:
        """Delete a system setting (admin only)."""
        if current_user_role != "admin":
            raise AuthzError("Only admins can delete system settings")
        
        db_setting = await self._get_system_setting_by_key(key)
        if not db_setting:
            raise NotFoundError(f"System setting with key '{key}' not found")
        
        await self.db.delete(db_setting)
        await self.db.commit()
        
        log.info(
            "system_setting_deleted",
            extra={
                "setting_key": key,
                "user_role": current_user_role
            }
        )
        
        return True
    
    # =========================================================================
    # Merchant Settings Management
    # =========================================================================
    
    async def create_merchant_setting(
        self, 
        merchant_id: UUID, 
        setting: MerchantSettingCreate,
        current_user_role: str
    ) -> MerchantSettingResponse:
        """Create a new merchant setting (admin/staff for their merchant)."""
        # Check if setting already exists for this merchant
        existing = await self._get_merchant_setting_by_key(merchant_id, setting.key)
        if existing:
            raise ValidationError(f"Merchant setting with key '{setting.key}' already exists for this merchant")
        
        # Create new setting
        db_setting = MerchantSetting(
            merchant_id=merchant_id,
            key=setting.key,
            value=setting.value
        )
        
        self.db.add(db_setting)
        await self.db.commit()
        await self.db.refresh(db_setting)
        
        log.info(
            "merchant_setting_created",
            extra={
                "merchant_id": str(merchant_id),
                "setting_key": setting.key,
                "user_role": current_user_role
            }
        )
        
        return MerchantSettingResponse.from_orm(db_setting)
    
    async def get_merchant_setting(
        self, 
        merchant_id: UUID, 
        key: str
    ) -> Optional[MerchantSettingResponse]:
        """Get a merchant setting by key."""
        db_setting = await self._get_merchant_setting_by_key(merchant_id, key)
        return MerchantSettingResponse.from_orm(db_setting) if db_setting else None
    
    async def list_merchant_settings(
        self, 
        merchant_id: UUID,
        query: ConfigurationQuery
    ) -> List[MerchantSettingResponse]:
        """List merchant settings with optional filtering."""
        stmt = select(MerchantSetting).where(MerchantSetting.merchant_id == merchant_id)
        
        if query.key_prefix:
            stmt = stmt.where(MerchantSetting.key.like(f"{query.key_prefix}%"))
        
        stmt = stmt.offset(query.offset).limit(query.limit)
        result = await self.db.execute(stmt)
        settings = result.scalars().all()
        
        return [MerchantSettingResponse.from_orm(setting) for setting in settings]
    
    async def update_merchant_setting(
        self, 
        merchant_id: UUID, 
        key: str, 
        update_data: MerchantSettingUpdate,
        current_user_role: str
    ) -> MerchantSettingResponse:
        """Update a merchant setting."""
        db_setting = await self._get_merchant_setting_by_key(merchant_id, key)
        if not db_setting:
            raise NotFoundError(f"Merchant setting with key '{key}' not found for this merchant")
        
        # Update value
        db_setting.value = update_data.value
        db_setting.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_setting)
        
        log.info(
            "merchant_setting_updated",
            extra={
                "merchant_id": str(merchant_id),
                "setting_key": key,
                "user_role": current_user_role
            }
        )
        
        return MerchantSettingResponse.from_orm(db_setting)
    
    async def delete_merchant_setting(
        self, 
        merchant_id: UUID, 
        key: str,
        current_user_role: str
    ) -> bool:
        """Delete a merchant setting."""
        db_setting = await self._get_merchant_setting_by_key(merchant_id, key)
        if not db_setting:
            raise NotFoundError(f"Merchant setting with key '{key}' not found for this merchant")
        
        await self.db.delete(db_setting)
        await self.db.commit()
        
        log.info(
            "merchant_setting_deleted",
            extra={
                "merchant_id": str(merchant_id),
                "setting_key": key,
                "user_role": current_user_role
            }
        )
        
        return True
    
    # =========================================================================
    # Feature Flag Management
    # =========================================================================
    
    async def create_feature_flag(
        self, 
        flag: FeatureFlagCreate,
        current_user_role: str
    ) -> FeatureFlagResponse:
        """Create a new feature flag."""
        if current_user_role != "admin" and flag.merchant_id is None:
            raise AuthzError("Only admins can create global feature flags")
        
        # Check if flag already exists (same name and merchant_id)
        existing = await self._get_feature_flag_by_name(flag.name, flag.merchant_id)
        if existing:
            scope = "global" if flag.merchant_id is None else f"merchant {flag.merchant_id}"
            raise ValidationError(f"Feature flag '{flag.name}' already exists for {scope}")
        
        # Create new flag
        db_flag = FeatureFlag(
            name=flag.name,
            description=flag.description,
            enabled=flag.enabled,
            merchant_id=flag.merchant_id
        )
        
        self.db.add(db_flag)
        await self.db.commit()
        await self.db.refresh(db_flag)
        
        log.info(
            "feature_flag_created",
            extra={
                "flag_name": flag.name,
                "merchant_id": str(flag.merchant_id) if flag.merchant_id else None,
                "enabled": flag.enabled,
                "user_role": current_user_role
            }
        )
        
        return FeatureFlagResponse.from_orm(db_flag)
    
    async def get_feature_flag(
        self, 
        name: str, 
        merchant_id: Optional[UUID] = None
    ) -> Optional[FeatureFlagResponse]:
        """Get a feature flag by name and optional merchant."""
        db_flag = await self._get_feature_flag_by_name(name, merchant_id)
        return FeatureFlagResponse.from_orm(db_flag) if db_flag else None
    
    async def list_feature_flags(
        self, 
        merchant_id: Optional[UUID] = None,
        include_global: bool = True,
        query: Optional[ConfigurationQuery] = None
    ) -> List[FeatureFlagResponse]:
        """List feature flags with optional filtering."""
        stmt = select(FeatureFlag)
        
        # Build where conditions based on parameters
        conditions = []
        
        if merchant_id and include_global:
            # Include both global flags and merchant-specific flags
            conditions.append(
                or_(
                    FeatureFlag.merchant_id.is_(None),
                    FeatureFlag.merchant_id == merchant_id
                )
            )
        elif merchant_id:
            # Only merchant-specific flags
            conditions.append(FeatureFlag.merchant_id == merchant_id)
        elif include_global:
            # Only global flags
            conditions.append(FeatureFlag.merchant_id.is_(None))
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        if query and query.offset:
            stmt = stmt.offset(query.offset)
        if query and query.limit:
            stmt = stmt.limit(query.limit)
        
        result = await self.db.execute(stmt)
        flags = result.scalars().all()
        
        return [FeatureFlagResponse.from_orm(flag) for flag in flags]
    
    async def update_feature_flag(
        self, 
        name: str, 
        merchant_id: Optional[UUID], 
        update_data: FeatureFlagUpdate,
        current_user_role: str
    ) -> FeatureFlagResponse:
        """Update a feature flag."""
        if current_user_role != "admin" and merchant_id is None:
            raise AuthzError("Only admins can update global feature flags")
        
        db_flag = await self._get_feature_flag_by_name(name, merchant_id)
        if not db_flag:
            scope = "global" if merchant_id is None else f"merchant {merchant_id}"
            raise NotFoundError(f"Feature flag '{name}' not found for {scope}")
        
        # Update fields
        if update_data.description is not None:
            db_flag.description = update_data.description
        if update_data.enabled is not None:
            db_flag.enabled = update_data.enabled
        
        db_flag.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_flag)
        
        log.info(
            "feature_flag_updated",
            extra={
                "flag_name": name,
                "merchant_id": str(merchant_id) if merchant_id else None,
                "enabled": db_flag.enabled,
                "user_role": current_user_role
            }
        )
        
        return FeatureFlagResponse.from_orm(db_flag)
    
    async def delete_feature_flag(
        self, 
        name: str, 
        merchant_id: Optional[UUID],
        current_user_role: str
    ) -> bool:
        """Delete a feature flag."""
        if current_user_role != "admin" and merchant_id is None:
            raise AuthzError("Only admins can delete global feature flags")
        
        db_flag = await self._get_feature_flag_by_name(name, merchant_id)
        if not db_flag:
            scope = "global" if merchant_id is None else f"merchant {merchant_id}"
            raise NotFoundError(f"Feature flag '{name}' not found for {scope}")
        
        await self.db.delete(db_flag)
        await self.db.commit()
        
        log.info(
            "feature_flag_deleted",
            extra={
                "flag_name": name,
                "merchant_id": str(merchant_id) if merchant_id else None,
                "user_role": current_user_role
            }
        )
        
        return True
    
    # =========================================================================
    # Configuration Hierarchy & Merging
    # =========================================================================
    
    async def get_merged_configuration(
        self, 
        merchant_id: UUID
    ) -> MergedConfigurationResponse:
        """Get merged configuration with proper hierarchy (system < merchant)."""
        
        # Get all system settings
        system_settings_stmt = select(SystemSetting)
        system_result = await self.db.execute(system_settings_stmt)
        system_settings = {s.key: s.value for s in system_result.scalars().all()}
        
        # Get merchant settings
        merchant_settings_stmt = select(MerchantSetting).where(
            MerchantSetting.merchant_id == merchant_id
        )
        merchant_result = await self.db.execute(merchant_settings_stmt)
        merchant_settings = {s.key: s.value for s in merchant_result.scalars().all()}
        
        # Get feature flags (global + merchant overrides)
        flags_stmt = select(FeatureFlag).where(
            or_(
                FeatureFlag.merchant_id.is_(None),
                FeatureFlag.merchant_id == merchant_id
            )
        )
        flags_result = await self.db.execute(flags_stmt)
        all_flags = flags_result.scalars().all()
        
        # Process feature flags with merchant override priority
        feature_flags = {}
        for flag in all_flags:
            # Merchant-specific flags override global flags
            if flag.name not in feature_flags or flag.merchant_id is not None:
                feature_flags[flag.name] = flag.enabled
        
        # Create effective configuration (merchant settings override system settings)
        effective_config = {**system_settings, **merchant_settings}
        
        return MergedConfigurationResponse(
            system_settings=system_settings,
            merchant_settings=merchant_settings,
            feature_flags=feature_flags,
            effective_config=effective_config,
            merchant_id=merchant_id
        )
    
    # =========================================================================
    # Bulk Operations
    # =========================================================================
    
    async def bulk_update_configuration(
        self, 
        merchant_id: UUID, 
        bulk_update: BulkConfigurationUpdate,
        current_user_role: str
    ) -> MergedConfigurationResponse:
        """Perform bulk configuration updates."""
        
        # Update system settings (admin only)
        if bulk_update.system_settings and current_user_role == "admin":
            for key, value in bulk_update.system_settings.items():
                try:
                    await self.update_system_setting(
                        key, 
                        SystemSettingUpdate(value=value),
                        current_user_role
                    )
                except NotFoundError:
                    # Create if doesn't exist
                    await self.create_system_setting(
                        SystemSettingCreate(key=key, value=value),
                        current_user_role
                    )
        
        # Update merchant settings
        if bulk_update.merchant_settings:
            for key, value in bulk_update.merchant_settings.items():
                try:
                    await self.update_merchant_setting(
                        merchant_id, 
                        key, 
                        MerchantSettingUpdate(value=value),
                        current_user_role
                    )
                except NotFoundError:
                    # Create if doesn't exist
                    await self.create_merchant_setting(
                        merchant_id,
                        MerchantSettingCreate(key=key, value=value),
                        current_user_role
                    )
        
        # Update feature flags
        if bulk_update.feature_flags:
            for name, enabled in bulk_update.feature_flags.items():
                try:
                    await self.update_feature_flag(
                        name, 
                        merchant_id,
                        FeatureFlagUpdate(enabled=enabled),
                        current_user_role
                    )
                except NotFoundError:
                    # Create merchant-specific override
                    await self.create_feature_flag(
                        FeatureFlagCreate(name=name, enabled=enabled, merchant_id=merchant_id),
                        current_user_role
                    )
        
        log.info(
            "bulk_configuration_updated",
            extra={
                "merchant_id": str(merchant_id),
                "user_role": current_user_role,
                "system_settings_count": len(bulk_update.system_settings or {}),
                "merchant_settings_count": len(bulk_update.merchant_settings or {}),
                "feature_flags_count": len(bulk_update.feature_flags or {})
            }
        )
        
        # Return merged configuration
        return await self.get_merged_configuration(merchant_id)
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    async def _get_system_setting_by_key(self, key: str) -> Optional[SystemSetting]:
        """Get system setting by key."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_merchant_setting_by_key(
        self, 
        merchant_id: UUID, 
        key: str
    ) -> Optional[MerchantSetting]:
        """Get merchant setting by merchant_id and key."""
        stmt = select(MerchantSetting).where(
            and_(
                MerchantSetting.merchant_id == merchant_id,
                MerchantSetting.key == key
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_feature_flag_by_name(
        self, 
        name: str, 
        merchant_id: Optional[UUID] = None
    ) -> Optional[FeatureFlag]:
        """Get feature flag by name and optional merchant."""
        conditions = [FeatureFlag.name == name]
        
        if merchant_id is None:
            conditions.append(FeatureFlag.merchant_id.is_(None))
        else:
            conditions.append(FeatureFlag.merchant_id == merchant_id)
        
        stmt = select(FeatureFlag).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()