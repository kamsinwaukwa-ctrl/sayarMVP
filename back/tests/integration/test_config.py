"""
Integration tests for configuration management system.

Tests system settings, merchant settings, feature flags, and configuration
hierarchy with proper RLS enforcement and caching.
"""

import pytest
import asyncio
from uuid import uuid4
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.config import (
    SystemSettingCreate, SystemSettingUpdate, 
    MerchantSettingCreate, MerchantSettingUpdate,
    FeatureFlagCreate, FeatureFlagUpdate,
    BulkConfigurationUpdate
)
from src.services.config_service import ConfigurationService
from src.config.settings import get_merchant_config, settings_loader
from src.utils.feature_flags import is_feature_enabled, feature_flags
from src.models.errors import NotFoundError, ValidationError, AuthzError

pytestmark = pytest.mark.asyncio


class TestSystemSettings:
    """Test system settings management."""
    
    async def test_create_system_setting_admin(self, test_client: AsyncClient, admin_token: str):
        """Test creating system setting as admin."""
        setting_data = {
            "key": "test.system.setting",
            "value": "test_value",
            "description": "Test system setting"
        }
        
        response = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["key"] == "test.system.setting"
        assert data["data"]["value"] == "test_value"
        assert data["data"]["description"] == "Test system setting"
    
    async def test_create_system_setting_non_admin_forbidden(self, test_client: AsyncClient, merchant_token: str):
        """Test creating system setting as non-admin is forbidden."""
        setting_data = {
            "key": "test.forbidden.setting",
            "value": "forbidden_value"
        }
        
        response = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 403
    
    async def test_get_system_setting(self, test_client: AsyncClient, admin_token: str, merchant_token: str):
        """Test retrieving system setting."""
        # Create setting as admin
        setting_data = {
            "key": "test.get.setting",
            "value": {"nested": "value"},
            "description": "Test get setting"
        }
        
        create_response = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 201
        
        # Retrieve as merchant (should work)
        response = await test_client.get(
            "/api/v1/config/system/test.get.setting",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["key"] == "test.get.setting"
        assert data["data"]["value"] == {"nested": "value"}
    
    async def test_update_system_setting(self, test_client: AsyncClient, admin_token: str):
        """Test updating system setting."""
        # Create setting
        setting_data = {
            "key": "test.update.setting",
            "value": "original_value"
        }
        
        create_response = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 201
        
        # Update setting
        update_data = {
            "value": "updated_value",
            "description": "Updated description"
        }
        
        response = await test_client.put(
            "/api/v1/config/system/test.update.setting",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["value"] == "updated_value"
        assert data["data"]["description"] == "Updated description"
    
    async def test_list_system_settings(self, test_client: AsyncClient, admin_token: str):
        """Test listing system settings with filtering."""
        # Create multiple settings
        settings = [
            {"key": "prefix.test.one", "value": "value1"},
            {"key": "prefix.test.two", "value": "value2"},
            {"key": "other.setting", "value": "value3"}
        ]
        
        for setting in settings:
            await test_client.post(
                "/api/v1/config/system",
                json=setting,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        # List with prefix filter
        response = await test_client.get(
            "/api/v1/config/system?key_prefix=prefix.test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert all(item["key"].startswith("prefix.test") for item in data["data"])
    
    async def test_delete_system_setting(self, test_client: AsyncClient, admin_token: str):
        """Test deleting system setting."""
        # Create setting
        setting_data = {
            "key": "test.delete.setting",
            "value": "to_be_deleted"
        }
        
        await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Delete setting
        response = await test_client.delete(
            "/api/v1/config/system/test.delete.setting",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify deletion
        get_response = await test_client.get(
            "/api/v1/config/system/test.delete.setting",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 404


class TestMerchantSettings:
    """Test merchant settings management."""
    
    async def test_create_merchant_setting(self, test_client: AsyncClient, merchant_token: str):
        """Test creating merchant setting."""
        setting_data = {
            "key": "merchant.test.setting",
            "value": {"config": "value"}
        }
        
        response = await test_client.post(
            "/api/v1/config/merchant",
            json=setting_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["key"] == "merchant.test.setting"
        assert data["data"]["value"] == {"config": "value"}
    
    async def test_merchant_setting_isolation(
        self, 
        test_client: AsyncClient, 
        merchant_token: str,
        db_session: AsyncSession
    ):
        """Test that merchant settings are properly isolated by RLS."""
        # Create setting for merchant 1
        setting_data = {
            "key": "isolation.test",
            "value": "merchant1_value"
        }
        
        response = await test_client.post(
            "/api/v1/config/merchant",
            json=setting_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        assert response.status_code == 201
        
        # Try to access from different merchant context would require different token
        # For now, verify via service layer
        service = ConfigurationService(db_session)
        different_merchant_id = uuid4()
        
        # This should return None due to RLS
        setting = await service.get_merchant_setting(different_merchant_id, "isolation.test")
        assert setting is None
    
    async def test_update_merchant_setting(self, test_client: AsyncClient, merchant_token: str):
        """Test updating merchant setting."""
        # Create setting
        setting_data = {
            "key": "merchant.update.test",
            "value": "original"
        }
        
        create_response = await test_client.post(
            "/api/v1/config/merchant",
            json=setting_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        assert create_response.status_code == 201
        
        # Update setting
        update_data = {"value": "updated"}
        
        response = await test_client.put(
            "/api/v1/config/merchant/merchant.update.test",
            json=update_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["value"] == "updated"


class TestFeatureFlags:
    """Test feature flags management."""
    
    async def test_create_merchant_feature_flag(self, test_client: AsyncClient, merchant_token: str):
        """Test creating merchant-specific feature flag."""
        flag_data = {
            "name": "test_merchant_feature",
            "description": "Test merchant feature flag",
            "enabled": True
        }
        
        response = await test_client.post(
            "/api/v1/config/feature-flags",
            json=flag_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["name"] == "test_merchant_feature"
        assert data["data"]["enabled"] is True
        assert data["data"]["merchant_id"] is not None
    
    async def test_create_global_feature_flag_admin_only(
        self, 
        test_client: AsyncClient, 
        admin_token: str,
        merchant_token: str
    ):
        """Test creating global feature flag requires admin."""
        global_flag_data = {
            "name": "test_global_feature",
            "description": "Global feature flag",
            "enabled": False,
            "merchant_id": None
        }
        
        # Should succeed as admin
        admin_response = await test_client.post(
            "/api/v1/config/feature-flags",
            json=global_flag_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 201
        
        # Should fail as merchant
        merchant_response = await test_client.post(
            "/api/v1/config/feature-flags",
            json=global_flag_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        assert merchant_response.status_code == 400
    
    async def test_feature_flag_hierarchy(
        self, 
        test_client: AsyncClient, 
        admin_token: str,
        merchant_token: str
    ):
        """Test feature flag hierarchy (global vs merchant override)."""
        # Create global flag (disabled)
        global_flag = {
            "name": "hierarchy_test_flag",
            "enabled": False,
            "merchant_id": None
        }
        
        await test_client.post(
            "/api/v1/config/feature-flags",
            json=global_flag,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Create merchant override (enabled)
        merchant_flag = {
            "name": "hierarchy_test_flag",
            "enabled": True
        }
        
        await test_client.post(
            "/api/v1/config/feature-flags",
            json=merchant_flag,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        # List flags - should see both
        response = await test_client.get(
            "/api/v1/config/feature-flags",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        hierarchy_flags = [f for f in data["data"] if f["name"] == "hierarchy_test_flag"]
        assert len(hierarchy_flags) == 2  # Global + merchant override
        
        # Merchant-specific flag should be enabled, global should be disabled
        merchant_flag_result = next(f for f in hierarchy_flags if f["merchant_id"] is not None)
        global_flag_result = next(f for f in hierarchy_flags if f["merchant_id"] is None)
        
        assert merchant_flag_result["enabled"] is True
        assert global_flag_result["enabled"] is False


class TestConfigurationHierarchy:
    """Test configuration hierarchy and merging."""
    
    async def test_merged_configuration_hierarchy(
        self, 
        test_client: AsyncClient, 
        admin_token: str,
        merchant_token: str
    ):
        """Test that merged configuration respects hierarchy."""
        # Create system setting
        system_setting = {
            "key": "hierarchy.test.setting",
            "value": "system_value"
        }
        
        await test_client.post(
            "/api/v1/config/system",
            json=system_setting,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Create merchant override
        merchant_setting = {
            "key": "hierarchy.test.setting",
            "value": "merchant_value"
        }
        
        await test_client.post(
            "/api/v1/config/merchant",
            json=merchant_setting,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        # Get merged configuration
        response = await test_client.get(
            "/api/v1/config/merged",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # System setting should be present
        assert "hierarchy.test.setting" in data["data"]["system_settings"]
        assert data["data"]["system_settings"]["hierarchy.test.setting"] == "system_value"
        
        # Merchant setting should be present
        assert "hierarchy.test.setting" in data["data"]["merchant_settings"]
        assert data["data"]["merchant_settings"]["hierarchy.test.setting"] == "merchant_value"
        
        # Effective config should use merchant value (higher priority)
        assert "hierarchy.test.setting" in data["data"]["effective_config"]
        assert data["data"]["effective_config"]["hierarchy.test.setting"] == "merchant_value"
    
    async def test_bulk_configuration_update(
        self, 
        test_client: AsyncClient, 
        admin_token: str
    ):
        """Test bulk configuration updates."""
        bulk_update = {
            "system_settings": {
                "bulk.system.setting1": "sys_value1",
                "bulk.system.setting2": 42
            },
            "merchant_settings": {
                "bulk.merchant.setting1": "merchant_value1",
                "bulk.merchant.setting2": {"nested": "value"}
            },
            "feature_flags": {
                "bulk_test_feature": True,
                "bulk_test_feature2": False
            }
        }
        
        response = await test_client.post(
            "/api/v1/config/bulk-update",
            json=bulk_update,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all settings were created/updated
        assert "bulk.system.setting1" in data["data"]["system_settings"]
        assert "bulk.merchant.setting1" in data["data"]["merchant_settings"]
        assert "bulk_test_feature" in data["data"]["feature_flags"]
        assert data["data"]["feature_flags"]["bulk_test_feature"] is True


class TestConfigurationCaching:
    """Test configuration caching behavior."""
    
    async def test_configuration_caching(self, db_session: AsyncSession):
        """Test that configuration caching works correctly."""
        merchant_id = uuid4()
        
        # Clear cache first
        settings_loader.invalidate_cache(merchant_id)
        
        # First load should hit database
        config1 = await get_merchant_config(db_session, merchant_id, use_cache=True)
        
        # Second load should use cache
        config2 = await get_merchant_config(db_session, merchant_id, use_cache=True)
        
        # Both should be identical
        assert config1.merchant_id == config2.merchant_id
        assert config1.system_settings == config2.system_settings
    
    async def test_cache_invalidation(
        self, 
        test_client: AsyncClient, 
        admin_token: str
    ):
        """Test cache invalidation after updates."""
        # Create initial setting
        setting_data = {
            "key": "cache.test.setting",
            "value": "original"
        }
        
        await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Update setting (should invalidate cache)
        update_data = {"value": "updated"}
        
        response = await test_client.put(
            "/api/v1/config/system/cache.test.setting",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify the updated value is returned (not cached)
        get_response = await test_client.get(
            "/api/v1/config/system/cache.test.setting",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert get_response.status_code == 200
        assert get_response.json()["data"]["value"] == "updated"
    
    async def test_manual_cache_invalidation(
        self, 
        test_client: AsyncClient, 
        admin_token: str
    ):
        """Test manual cache invalidation endpoint."""
        response = await test_client.post(
            "/api/v1/config/cache/invalidate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] is True
        assert "all merchants" in data["message"]


class TestFeatureFlagsEvaluation:
    """Test feature flags evaluation and strategies."""
    
    async def test_feature_flag_evaluation_service_layer(self, db_session: AsyncSession):
        """Test feature flag evaluation through service layer."""
        merchant_id = uuid4()
        
        # Create configuration service
        service = ConfigurationService(db_session)
        
        # Create a global feature flag
        global_flag = FeatureFlagCreate(
            name="service_test_flag",
            enabled=True,
            description="Test flag for service evaluation"
        )
        
        await service.create_feature_flag(global_flag, "admin")
        
        # Test evaluation
        is_enabled = await is_feature_enabled("service_test_flag", merchant_id, db=db_session)
        assert is_enabled is True
        
        # Create merchant override (disabled)
        merchant_flag = FeatureFlagCreate(
            name="service_test_flag",
            enabled=False,
            merchant_id=merchant_id
        )
        
        await service.create_feature_flag(merchant_flag, "admin")
        
        # Re-evaluate - merchant override should take precedence
        is_enabled_override = await is_feature_enabled("service_test_flag", merchant_id, db=db_session)
        assert is_enabled_override is False
    
    async def test_feature_flag_builtin_registration(self):
        """Test that built-in feature flags are properly registered."""
        builtin_flags = feature_flags.list_registered_flags()
        
        expected_flags = [
            "enhanced_analytics", "bulk_import", "advanced_inventory",
            "custom_webhooks", "multi_currency", "subscription_billing",
            "ai_recommendations", "social_media_integration", 
            "loyalty_program", "advanced_reporting"
        ]
        
        registered_names = [flag.name for flag in builtin_flags]
        
        for expected in expected_flags:
            assert expected in registered_names


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    async def test_duplicate_system_setting_error(self, test_client: AsyncClient, admin_token: str):
        """Test error when creating duplicate system setting."""
        setting_data = {
            "key": "duplicate.test.key",
            "value": "first_value"
        }
        
        # Create first setting
        response1 = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 400
    
    async def test_invalid_setting_key_format(self, test_client: AsyncClient, admin_token: str):
        """Test validation of setting key format."""
        invalid_setting = {
            "key": "invalid key with spaces!",
            "value": "test"
        }
        
        response = await test_client.post(
            "/api/v1/config/system",
            json=invalid_setting,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_nonexistent_setting_retrieval(self, test_client: AsyncClient, merchant_token: str):
        """Test retrieving non-existent settings returns 404."""
        response = await test_client.get(
            "/api/v1/config/system/nonexistent.setting",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        
        assert response.status_code == 404
    
    async def test_unauthorized_system_setting_operations(
        self, 
        test_client: AsyncClient, 
        merchant_token: str
    ):
        """Test that non-admin users cannot perform system setting operations."""
        setting_data = {
            "key": "unauthorized.test",
            "value": "test"
        }
        
        # Create should fail
        create_response = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        assert create_response.status_code == 403
        
        # Update should fail
        update_response = await test_client.put(
            "/api/v1/config/system/any.setting",
            json={"value": "new"},
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        assert update_response.status_code == 403
        
        # Delete should fail
        delete_response = await test_client.delete(
            "/api/v1/config/system/any.setting",
            headers={"Authorization": f"Bearer {merchant_token}"}
        )
        assert delete_response.status_code == 403


class TestConfigurationValidation:
    """Test configuration validation and type handling."""
    
    async def test_json_value_handling(self, test_client: AsyncClient, admin_token: str):
        """Test that JSON values are properly handled."""
        complex_setting = {
            "key": "json.complex.setting",
            "value": {
                "nested_object": {
                    "string_field": "text",
                    "number_field": 42,
                    "boolean_field": True,
                    "array_field": [1, 2, 3],
                    "null_field": None
                }
            }
        }
        
        response = await test_client.post(
            "/api/v1/config/system",
            json=complex_setting,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["value"] == complex_setting["value"]
    
    async def test_setting_key_normalization(self, test_client: AsyncClient, admin_token: str):
        """Test that setting keys are normalized to lowercase."""
        setting_data = {
            "key": "Test.Mixed.Case.Key",
            "value": "normalized"
        }
        
        response = await test_client.post(
            "/api/v1/config/system",
            json=setting_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["key"] == "test.mixed.case.key"