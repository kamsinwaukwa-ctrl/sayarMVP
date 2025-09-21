"""
Integration tests for Meta Commerce Catalog integration credentials management
"""

import pytest
import json
from typing import Dict, Any
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.meta_integrations import (
    MetaIntegration,
    MetaCredentialsRequest,
    MetaCredentialsResponse,
    MetaIntegrationStatusResponse,
    MetaTokenRotateRequest,
    MetaIntegrationStatus,
    MetaCredentialsForWorker,
)
from src.services.meta_integration_service import (
    MetaIntegrationService,
    MetaIntegrationError,
)
from src.utils.encryption import encrypt_key, decrypt_key
from tests.fixtures.auth import admin_jwt, staff_jwt, other_merchant_jwt
from tests.fixtures.database import db_session


class TestMetaIntegrationService:
    """Test Meta integration service layer"""

    @pytest.mark.asyncio
    async def test_store_valid_credentials(self, db_session: AsyncSession):
        """Test storing valid Meta credentials"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        request = MetaCredentialsRequest(
            catalog_id="1234567890",
            system_user_token="EAAtest_valid_token",
            app_id="987654321",
            waba_id="123456789012345",
        )

        # Mock Meta API verification
        with patch.object(service, "_verify_credentials") as mock_verify:
            mock_verify.return_value = {
                "status": MetaIntegrationStatus.VERIFIED,
                "catalog_name": "Test Catalog",
                "verified_at": datetime.utcnow(),
            }

            result = await service.store_credentials(merchant_id, request)

            assert result.success is True
            assert result.status == MetaIntegrationStatus.VERIFIED
            assert result.catalog_name == "Test Catalog"
            assert result.verification_timestamp is not None

        # Verify database record
        stmt = select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        db_result = await db_session.execute(stmt)
        integration = db_result.scalar_one()

        assert integration.catalog_id == request.catalog_id
        assert integration.app_id == request.app_id
        assert integration.waba_id == request.waba_id
        assert integration.status == MetaIntegrationStatus.VERIFIED.value
        assert integration.catalog_name == "Test Catalog"

        # Verify token is encrypted
        decrypted_token = decrypt_key(integration.system_user_token_encrypted)
        assert decrypted_token == request.system_user_token

    @pytest.mark.asyncio
    async def test_store_invalid_credentials(self, db_session: AsyncSession):
        """Test storing invalid Meta credentials"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        request = MetaCredentialsRequest(
            catalog_id="invalid_catalog",
            system_user_token="EAAinvalid_token",
            app_id="invalid_app",
            waba_id=None,
        )

        # Mock Meta API verification failure
        with patch.object(service, "_verify_credentials") as mock_verify:
            mock_verify.return_value = {
                "status": MetaIntegrationStatus.INVALID,
                "error": "Invalid access token",
                "error_code": "META_AUTH_FAILED",
            }

            result = await service.store_credentials(merchant_id, request)

            assert result.success is True  # API call succeeds even with invalid creds
            assert result.status == MetaIntegrationStatus.INVALID

        # Verify database record shows invalid status
        stmt = select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        db_result = await db_session.execute(stmt)
        integration = db_result.scalar_one()

        assert integration.status == MetaIntegrationStatus.INVALID.value
        assert integration.last_error == "Invalid access token"
        assert integration.error_code == "META_AUTH_FAILED"

    @pytest.mark.asyncio
    async def test_credentials_idempotency(self, db_session: AsyncSession):
        """Test credential storage idempotency"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        request = MetaCredentialsRequest(
            catalog_id="1234567890",
            system_user_token="EAAtest_token",
            app_id="987654321",
        )

        # Mock verification
        with patch.object(service, "_verify_credentials") as mock_verify:
            mock_verify.return_value = {
                "status": MetaIntegrationStatus.VERIFIED,
                "catalog_name": "Test Catalog",
                "verified_at": datetime.utcnow(),
            }

            # First call
            result1 = await service.store_credentials(merchant_id, request)
            assert mock_verify.call_count == 1

            # Second call with same credentials should be idempotent
            result2 = await service.store_credentials(merchant_id, request)
            assert mock_verify.call_count == 1  # Not called again
            assert result2.message == "Meta credentials already configured"

    @pytest.mark.asyncio
    async def test_get_integration_status_verified(self, db_session: AsyncSession):
        """Test getting status for verified integration"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        # Create verified integration
        integration_data = {
            "merchant_id": merchant_id,
            "catalog_id": "1234567890",
            "system_user_token_encrypted": encrypt_key("EAAtest_token").encrypted_data,
            "app_id": "987654321",
            "waba_id": "123456789012345",
            "status": MetaIntegrationStatus.VERIFIED.value,
            "catalog_name": "Test Catalog",
            "last_verified_at": datetime.utcnow(),
        }

        integration = MetaIntegration(**integration_data)
        db_session.add(integration)
        await db_session.commit()

        result = await service.get_integration_status(merchant_id)

        assert result.status == MetaIntegrationStatus.VERIFIED
        assert result.catalog_id == "1234567890"
        assert result.catalog_name == "Test Catalog"
        assert result.app_id == "987654321"
        assert result.waba_id == "123456789012345"
        assert result.verification_details is not None
        assert result.verification_details.token_valid is True

    @pytest.mark.asyncio
    async def test_get_integration_status_not_configured(
        self, db_session: AsyncSession
    ):
        """Test getting status when no integration exists"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        result = await service.get_integration_status(merchant_id)

        assert result.status == MetaIntegrationStatus.PENDING
        assert result.message == "Meta credentials not set up for this merchant"

    @pytest.mark.asyncio
    async def test_delete_integration(self, db_session: AsyncSession):
        """Test deleting Meta integration"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        # Create integration
        integration = MetaIntegration(
            merchant_id=merchant_id,
            catalog_id="1234567890",
            system_user_token_encrypted=encrypt_key("EAAtest_token").encrypted_data,
            app_id="987654321",
            status=MetaIntegrationStatus.VERIFIED.value,
        )
        db_session.add(integration)
        await db_session.commit()

        # Delete integration
        success = await service.delete_integration(merchant_id)
        assert success is True

        # Verify deletion
        stmt = select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        db_result = await db_session.execute(stmt)
        assert db_result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_rotate_token(self, db_session: AsyncSession):
        """Test token rotation"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        # Create existing integration
        integration = MetaIntegration(
            merchant_id=merchant_id,
            catalog_id="1234567890",
            system_user_token_encrypted=encrypt_key("EAAold_token").encrypted_data,
            app_id="987654321",
            status=MetaIntegrationStatus.VERIFIED.value,
        )
        db_session.add(integration)
        await db_session.commit()

        rotate_request = MetaTokenRotateRequest(system_user_token="EAAnew_token")

        # Mock verification for new token
        with patch.object(service, "_verify_credentials") as mock_verify:
            mock_verify.return_value = {
                "status": MetaIntegrationStatus.VERIFIED,
                "catalog_name": "Test Catalog",
                "verified_at": datetime.utcnow(),
            }

            result = await service.rotate_token(merchant_id, rotate_request)

            assert result.success is True
            assert result.status == MetaIntegrationStatus.VERIFIED

        # Verify token was updated
        stmt = select(MetaIntegration).where(MetaIntegration.merchant_id == merchant_id)
        db_result = await db_session.execute(stmt)
        updated_integration = db_result.scalar_one()

        decrypted_token = decrypt_key(updated_integration.system_user_token_encrypted)
        assert decrypted_token == "EAAnew_token"

    @pytest.mark.asyncio
    async def test_load_credentials_for_worker(self, db_session: AsyncSession):
        """Test loading credentials for sync worker"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        # Create verified integration
        integration = MetaIntegration(
            merchant_id=merchant_id,
            catalog_id="1234567890",
            system_user_token_encrypted=encrypt_key("EAAworker_token").encrypted_data,
            app_id="987654321",
            waba_id="123456789012345",
            status=MetaIntegrationStatus.VERIFIED.value,
            last_verified_at=datetime.utcnow(),
        )
        db_session.add(integration)
        await db_session.commit()

        credentials = await service.load_credentials_for_worker(merchant_id)

        assert credentials is not None
        assert isinstance(credentials, MetaCredentialsForWorker)
        assert credentials.catalog_id == "1234567890"
        assert credentials.system_user_token == "EAAworker_token"
        assert credentials.app_id == "987654321"
        assert credentials.waba_id == "123456789012345"
        assert credentials.status == MetaIntegrationStatus.VERIFIED
        assert credentials.is_usable() is True

    @pytest.mark.asyncio
    async def test_load_credentials_for_worker_not_verified(
        self, db_session: AsyncSession
    ):
        """Test loading credentials when integration is not verified"""
        service = MetaIntegrationService(db_session)
        merchant_id = uuid4()

        # Create invalid integration
        integration = MetaIntegration(
            merchant_id=merchant_id,
            catalog_id="1234567890",
            system_user_token_encrypted=encrypt_key("EAAinvalid_token").encrypted_data,
            app_id="987654321",
            status=MetaIntegrationStatus.INVALID.value,
        )
        db_session.add(integration)
        await db_session.commit()

        credentials = await service.load_credentials_for_worker(merchant_id)

        assert credentials is None

    @pytest.mark.asyncio
    async def test_meta_api_verification_success(self, db_session: AsyncSession):
        """Test successful Meta API verification"""
        service = MetaIntegrationService(db_session)

        request = MetaCredentialsRequest(
            catalog_id="1234567890",
            system_user_token="EAAvalid_token",
            app_id="987654321",
        )

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Test Catalog"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await service._verify_credentials(request)

            assert result["status"] == MetaIntegrationStatus.VERIFIED
            assert result["catalog_name"] == "Test Catalog"
            assert "verified_at" in result

    @pytest.mark.asyncio
    async def test_meta_api_verification_auth_failed(self, db_session: AsyncSession):
        """Test Meta API verification with auth failure"""
        service = MetaIntegrationService(db_session)

        request = MetaCredentialsRequest(
            catalog_id="1234567890",
            system_user_token="EAAinvalid_token",
            app_id="987654321",
        )

        # Mock auth failure response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"code": 190, "message": "Invalid access token"}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await service._verify_credentials(request)

            assert result["status"] == MetaIntegrationStatus.INVALID
            assert result["error"] == "Invalid access token"
            assert result["error_code"] == "META_190"

    @pytest.mark.asyncio
    async def test_meta_api_verification_catalog_not_found(
        self, db_session: AsyncSession
    ):
        """Test Meta API verification with catalog not found"""
        service = MetaIntegrationService(db_session)

        request = MetaCredentialsRequest(
            catalog_id="9999999999",
            system_user_token="EAAvalid_token",
            app_id="987654321",
        )

        # Mock not found response
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await service._verify_credentials(request)

            assert result["status"] == MetaIntegrationStatus.INVALID
            assert result["error"] == "Catalog not found or inaccessible"
            assert result["error_code"] == "META_CATALOG_NOT_FOUND"


class TestMetaIntegrationAPI:
    """Test Meta integration API endpoints"""

    def test_store_credentials_success(self, client: TestClient, admin_jwt: str):
        """Test successful credential storage via API"""
        payload = {
            "catalog_id": "1234567890",
            "system_user_token": "EAAtest_token",
            "app_id": "987654321",
            "waba_id": "123456789012345",
        }

        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.store_credentials"
        ) as mock_store:
            mock_store.return_value = MetaCredentialsResponse(
                success=True,
                message="Meta credentials saved successfully",
                status=MetaIntegrationStatus.VERIFIED,
                catalog_name="Test Catalog",
                verification_timestamp=datetime.utcnow(),
            )

            response = client.put(
                "/api/v1/integrations/meta/credentials",
                json=payload,
                headers={"Authorization": f"Bearer {admin_jwt}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "verified"
            assert data["catalog_name"] == "Test Catalog"

    def test_store_credentials_staff_forbidden(
        self, client: TestClient, staff_jwt: str
    ):
        """Test that staff users cannot store credentials"""
        payload = {
            "catalog_id": "1234567890",
            "system_user_token": "EAAtest_token",
            "app_id": "987654321",
        }

        response = client.put(
            "/api/v1/integrations/meta/credentials",
            json=payload,
            headers={"Authorization": f"Bearer {staff_jwt}"},
        )

        assert response.status_code == 403

    def test_store_credentials_validation_error(
        self, client: TestClient, admin_jwt: str
    ):
        """Test credential validation error"""
        payload = {
            "catalog_id": "invalid_catalog",  # Should be numeric
            "system_user_token": "invalid_token",  # Should start with EAA
            "app_id": "invalid_app",  # Should be numeric
        }

        response = client.put(
            "/api/v1/integrations/meta/credentials",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )

        assert response.status_code == 422

    def test_get_status_verified(self, client: TestClient, admin_jwt: str):
        """Test getting verified integration status"""
        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.get_integration_status"
        ) as mock_status:
            mock_status.return_value = MetaIntegrationStatusResponse(
                status=MetaIntegrationStatus.VERIFIED,
                catalog_id="1234567890",
                catalog_name="Test Catalog",
                app_id="987654321",
                waba_id="123456789012345",
                last_verified_at=datetime.utcnow(),
                verification_details={
                    "token_valid": True,
                    "catalog_accessible": True,
                    "permissions_valid": True,
                },
            )

            response = client.get(
                "/api/v1/integrations/meta/status",
                headers={"Authorization": f"Bearer {admin_jwt}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "verified"
            assert data["catalog_id"] == "1234567890"
            assert data["catalog_name"] == "Test Catalog"

    def test_get_status_not_configured(self, client: TestClient, admin_jwt: str):
        """Test getting status when not configured"""
        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.get_integration_status"
        ) as mock_status:
            mock_status.return_value = MetaIntegrationStatusResponse.not_configured()

            response = client.get(
                "/api/v1/integrations/meta/status",
                headers={"Authorization": f"Bearer {admin_jwt}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"
            assert "message" in data

    def test_get_status_staff_access(self, client: TestClient, staff_jwt: str):
        """Test that staff can view status"""
        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.get_integration_status"
        ) as mock_status:
            mock_status.return_value = MetaIntegrationStatusResponse.not_configured()

            response = client.get(
                "/api/v1/integrations/meta/status",
                headers={"Authorization": f"Bearer {staff_jwt}"},
            )

            assert response.status_code == 200

    def test_delete_integration_success(self, client: TestClient, admin_jwt: str):
        """Test successful integration deletion"""
        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.delete_integration"
        ) as mock_delete:
            mock_delete.return_value = True

            response = client.delete(
                "/api/v1/integrations/meta/credentials",
                headers={"Authorization": f"Bearer {admin_jwt}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Meta integration removed successfully"

    def test_delete_integration_staff_forbidden(
        self, client: TestClient, staff_jwt: str
    ):
        """Test that staff cannot delete integration"""
        response = client.delete(
            "/api/v1/integrations/meta/credentials",
            headers={"Authorization": f"Bearer {staff_jwt}"},
        )

        assert response.status_code == 403

    def test_rotate_credentials_success(self, client: TestClient, admin_jwt: str):
        """Test successful token rotation"""
        payload = {"system_user_token": "EAAnew_token"}

        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.rotate_token"
        ) as mock_rotate:
            mock_rotate.return_value = MetaCredentialsResponse(
                success=True,
                message="Meta credentials rotated successfully",
                status=MetaIntegrationStatus.VERIFIED,
                catalog_name="Test Catalog",
                verification_timestamp=datetime.utcnow(),
            )

            response = client.post(
                "/api/v1/integrations/meta/rotate",
                json=payload,
                headers={"Authorization": f"Bearer {admin_jwt}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "verified"

    def test_rotate_credentials_no_existing_integration(
        self, client: TestClient, admin_jwt: str
    ):
        """Test token rotation when no existing integration"""
        payload = {"system_user_token": "EAAnew_token"}

        with patch(
            "src.services.meta_integration_service.MetaIntegrationService.rotate_token"
        ) as mock_rotate:
            mock_rotate.side_effect = MetaIntegrationError(
                "No existing Meta integration found"
            )

            response = client.post(
                "/api/v1/integrations/meta/rotate",
                json=payload,
                headers={"Authorization": f"Bearer {admin_jwt}"},
            )

            assert response.status_code == 404

    def test_cross_tenant_isolation(self, client: TestClient, other_merchant_jwt: str):
        """Test that merchants can't access other merchants' integrations"""
        response = client.get(
            "/api/v1/integrations/meta/status",
            headers={"Authorization": f"Bearer {other_merchant_jwt}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should return not_configured for different merchant
        assert data["status"] == "pending"


class TestSyncWorkerIntegration:
    """Test integration with sync worker"""

    @pytest.mark.asyncio
    async def test_worker_loads_valid_credentials(self, db_session: AsyncSession):
        """Test that sync worker loads valid credentials"""
        from src.services.product_service import ProductService

        merchant_id = uuid4()
        product_service = ProductService(db_session)

        # Create verified integration
        integration = MetaIntegration(
            merchant_id=merchant_id,
            catalog_id="1234567890",
            system_user_token_encrypted=encrypt_key("EAAworker_token").encrypted_data,
            app_id="987654321",
            status=MetaIntegrationStatus.VERIFIED.value,
            last_verified_at=datetime.utcnow(),
        )
        db_session.add(integration)
        await db_session.commit()

        credentials = await product_service.load_meta_credentials_for_worker(
            merchant_id
        )

        assert credentials is not None
        assert credentials.is_usable() is True
        assert credentials.catalog_id == "1234567890"
        assert credentials.system_user_token == "EAAworker_token"

    @pytest.mark.asyncio
    async def test_worker_handles_missing_credentials(self, db_session: AsyncSession):
        """Test that sync worker handles missing credentials gracefully"""
        from src.services.product_service import ProductService

        merchant_id = uuid4()
        product_service = ProductService(db_session)

        # No integration exists
        credentials = await product_service.load_meta_credentials_for_worker(
            merchant_id
        )

        assert credentials is None

    @pytest.mark.asyncio
    async def test_worker_handles_invalid_credentials(self, db_session: AsyncSession):
        """Test that sync worker handles invalid credentials gracefully"""
        from src.services.product_service import ProductService

        merchant_id = uuid4()
        product_service = ProductService(db_session)

        # Create invalid integration
        integration = MetaIntegration(
            merchant_id=merchant_id,
            catalog_id="1234567890",
            system_user_token_encrypted=encrypt_key("EAAinvalid_token").encrypted_data,
            app_id="987654321",
            status=MetaIntegrationStatus.INVALID.value,
        )
        db_session.add(integration)
        await db_session.commit()

        credentials = await product_service.load_meta_credentials_for_worker(
            merchant_id
        )

        assert credentials is None  # Service returns None for invalid credentials
