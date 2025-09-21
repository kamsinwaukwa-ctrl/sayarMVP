"""
Integration tests for WhatsApp credentials CRUD and verification endpoints
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.main import app
from src.models.errors import ErrorCode
from tests.conftest import TestUser, get_test_db_session


class TestWhatsAppCredentials:
    """Test cases for WhatsApp credentials management"""

    @pytest_asyncio.fixture
    async def valid_credentials(self):
        """Valid WhatsApp credentials for testing"""
        return {
            "waba_id": "123456789012345",
            "phone_number_id": "987654321098765",
            "app_id": "456789123456789",
            "system_user_token": "EAAtest_token_12345678901234567890",
            "environment": "test",
        }

    @pytest_asyncio.fixture
    async def mock_graph_api_success(self):
        """Mock successful Graph API response"""
        return {
            "id": "987654321098765",
            "display_phone_number": "+234 812 345 6789",
            "verified_name": "Beauty Store Lagos",
        }

    def test_save_whatsapp_credentials_success(
        self, client: TestClient, admin_user: TestUser, valid_credentials: dict
    ):
        """Test successful saving of WhatsApp credentials"""
        response = client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "WhatsApp credentials saved successfully"
        assert data["data"]["connection_status"] == "not_connected"
        assert data["data"]["environment"] == "test"
        assert data["data"]["phone_number_id"] == "***********8765"
        assert data["data"]["verified_at"] is None

    def test_update_whatsapp_credentials_success(
        self, client: TestClient, admin_user: TestUser, valid_credentials: dict
    ):
        """Test updating existing WhatsApp credentials"""
        # First save credentials
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Update with new values
        updated_credentials = valid_credentials.copy()
        updated_credentials["environment"] = "prod"

        response = client.put(
            "/api/v1/integrations/whatsapp/credentials",
            json=updated_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "WhatsApp credentials updated successfully"
        assert data["data"]["environment"] == "prod"

    def test_get_whatsapp_status_not_configured(
        self, client: TestClient, admin_user: TestUser
    ):
        """Test getting status when no credentials configured"""
        response = client.get(
            "/api/v1/integrations/whatsapp/status",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["data"]["connection_status"] == "not_connected"
        assert data["data"]["environment"] == "test"
        assert data["data"]["phone_number_id"] is None

    def test_get_whatsapp_status_configured(
        self, client: TestClient, admin_user: TestUser, valid_credentials: dict
    ):
        """Test getting status after credentials are saved"""
        # Save credentials first
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        response = client.get(
            "/api/v1/integrations/whatsapp/status",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["data"]["connection_status"] == "not_connected"
        assert data["data"]["environment"] == "test"
        assert data["data"]["phone_number_id"] == "***********8765"

    @patch("httpx.AsyncClient.get")
    def test_verify_whatsapp_connection_success(
        self,
        mock_get,
        client: TestClient,
        admin_user: TestUser,
        valid_credentials: dict,
        mock_graph_api_success: dict,
    ):
        """Test successful WhatsApp connection verification"""
        # Mock successful Graph API response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_graph_api_success
        mock_get.return_value = mock_response

        # Save credentials first
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Verify connection
        response = client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "WhatsApp connection verified successfully"
        assert data["data"]["connection_status"] == "verified_test"
        assert data["data"]["phone_number_display"] == "+234 812 345 6789"
        assert data["data"]["business_name"] == "Beauty Store Lagos"
        assert data["data"]["verified_at"] is not None

    @patch("httpx.AsyncClient.get")
    def test_verify_whatsapp_connection_prod_environment(
        self,
        mock_get,
        client: TestClient,
        admin_user: TestUser,
        valid_credentials: dict,
        mock_graph_api_success: dict,
    ):
        """Test verification sets correct status for prod environment"""
        # Mock successful Graph API response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_graph_api_success
        mock_get.return_value = mock_response

        # Save credentials with prod environment
        prod_credentials = valid_credentials.copy()
        prod_credentials["environment"] = "prod"

        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=prod_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Verify connection
        response = client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["connection_status"] == "verified_prod"

    @patch("httpx.AsyncClient.get")
    def test_verify_whatsapp_connection_invalid_credentials(
        self,
        mock_get,
        client: TestClient,
        admin_user: TestUser,
        valid_credentials: dict,
    ):
        """Test verification with invalid credentials"""
        # Mock Graph API error response
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid access token",
                "code": 190,
                "error_subcode": 463,
            }
        }
        mock_response.content = json.dumps(mock_response.json.return_value).encode()
        mock_get.return_value = mock_response

        # Save credentials first
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Verify connection
        response = client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 422

        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "WHATSAPP_VERIFICATION_FAILED"
        assert "Invalid access token" in data["error"]["details"]["graph_error"]
        assert data["error"]["details"]["error_code"] == 190
        assert data["error"]["details"]["error_subcode"] == 463

    def test_verify_whatsapp_connection_no_credentials(
        self, client: TestClient, admin_user: TestUser
    ):
        """Test verification when no credentials are saved"""
        response = client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 404

        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "WHATSAPP_CREDENTIALS_NOT_FOUND"

    def test_save_credentials_invalid_data(
        self, client: TestClient, admin_user: TestUser
    ):
        """Test saving credentials with invalid data"""
        invalid_credentials = {
            "waba_id": "123",  # Too short
            "phone_number_id": "",  # Empty
            "app_id": "456789123456789",
            "system_user_token": "short",  # Too short
            "environment": "invalid",  # Invalid enum value
        }

        response = client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=invalid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 422  # Validation error

    def test_endpoints_require_authentication(
        self, client: TestClient, valid_credentials: dict
    ):
        """Test that all endpoints require authentication"""
        endpoints = [
            ("POST", "/api/v1/integrations/whatsapp/credentials", valid_credentials),
            ("PUT", "/api/v1/integrations/whatsapp/credentials", valid_credentials),
            ("POST", "/api/v1/integrations/whatsapp/verify", {}),
            ("GET", "/api/v1/integrations/whatsapp/status", None),
        ]

        for method, url, data in endpoints:
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                response = client.post(url, json=data)
            elif method == "PUT":
                response = client.put(url, json=data)

            assert response.status_code == 401

    def test_staff_user_access_denied(
        self, client: TestClient, staff_user: TestUser, valid_credentials: dict
    ):
        """Test that staff users cannot access admin-only endpoints"""
        endpoints = [
            ("POST", "/api/v1/integrations/whatsapp/credentials", valid_credentials),
            ("PUT", "/api/v1/integrations/whatsapp/credentials", valid_credentials),
            ("POST", "/api/v1/integrations/whatsapp/verify", {}),
            ("GET", "/api/v1/integrations/whatsapp/status", None),
        ]

        for method, url, data in endpoints:
            if method == "GET":
                response = client.get(
                    url, headers={"Authorization": f"Bearer {staff_user.token}"}
                )
            elif method == "POST":
                response = client.post(
                    url,
                    json=data,
                    headers={"Authorization": f"Bearer {staff_user.token}"},
                )
            elif method == "PUT":
                response = client.put(
                    url,
                    json=data,
                    headers={"Authorization": f"Bearer {staff_user.token}"},
                )

            assert response.status_code == 403  # Forbidden for staff

    def test_merchant_isolation(
        self,
        client: TestClient,
        admin_user: TestUser,
        admin_user_2: TestUser,
        valid_credentials: dict,
    ):
        """Test that merchants can only see their own credentials"""
        # Merchant 1 saves credentials
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Merchant 2 should not see merchant 1's credentials
        response = client.get(
            "/api/v1/integrations/whatsapp/status",
            headers={"Authorization": f"Bearer {admin_user_2.token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should have default status (no credentials configured)
        assert data["data"]["phone_number_id"] is None

    @patch("httpx.AsyncClient.get")
    def test_graph_api_timeout_handling(
        self,
        mock_get,
        client: TestClient,
        admin_user: TestUser,
        valid_credentials: dict,
    ):
        """Test handling of Graph API timeout"""
        import httpx

        # Mock timeout exception
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        # Save credentials first
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Verify connection
        response = client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "WHATSAPP_VERIFICATION_FAILED"
        assert "timeout" in data["error"]["message"].lower()

    def test_phone_number_id_masking(
        self, client: TestClient, admin_user: TestUser, valid_credentials: dict
    ):
        """Test that phone number IDs are properly masked in responses"""
        # Save credentials
        response = client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        data = response.json()
        phone_id = data["data"]["phone_number_id"]

        # Should show last 4 digits with asterisks
        assert phone_id == "***********8765"
        assert len(phone_id) == len(valid_credentials["phone_number_id"])

    def test_credentials_encryption_in_database(
        self, client: TestClient, admin_user: TestUser, valid_credentials: dict
    ):
        """Test that credentials are encrypted when stored in database"""
        # Save credentials
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Check database directly
        async def check_encryption():
            async with get_test_db_session() as db:
                from src.models.sqlalchemy_models import Merchant
                from sqlalchemy import select

                result = await db.execute(
                    select(Merchant).where(Merchant.id == admin_user.merchant_id)
                )
                merchant = result.scalar_one()

                # Encrypted values should not match plaintext
                assert merchant.waba_id_enc != valid_credentials["waba_id"]
                assert (
                    merchant.phone_number_id_enc != valid_credentials["phone_number_id"]
                )
                assert merchant.app_id_enc != valid_credentials["app_id"]
                assert (
                    merchant.system_user_token_enc
                    != valid_credentials["system_user_token"]
                )

                # Encrypted values should be base64-encoded (contain only base64 chars)
                import base64
                import binascii

                for encrypted_field in [
                    merchant.waba_id_enc,
                    merchant.phone_number_id_enc,
                    merchant.app_id_enc,
                    merchant.system_user_token_enc,
                ]:
                    try:
                        base64.b64decode(encrypted_field)
                    except binascii.Error:
                        pytest.fail(
                            f"Encrypted field is not valid base64: {encrypted_field}"
                        )

        import asyncio

        asyncio.run(check_encryption())

    @patch("httpx.AsyncClient.get")
    def test_verification_status_persistence(
        self,
        mock_get,
        client: TestClient,
        admin_user: TestUser,
        valid_credentials: dict,
        mock_graph_api_success: dict,
    ):
        """Test that verification status is properly persisted"""
        # Mock successful Graph API response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_graph_api_success
        mock_get.return_value = mock_response

        # Save credentials
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Verify connection
        client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Check that status persisted
        response = client.get(
            "/api/v1/integrations/whatsapp/status",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        data = response.json()
        assert data["data"]["connection_status"] == "verified_test"
        assert data["data"]["verified_at"] is not None
        assert data["data"]["last_error"] is None

    @patch("httpx.AsyncClient.get")
    def test_verification_failure_status_persistence(
        self,
        mock_get,
        client: TestClient,
        admin_user: TestUser,
        valid_credentials: dict,
    ):
        """Test that verification failure status is properly persisted"""
        # Mock Graph API error response
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid access token", "code": 190}
        }
        mock_response.content = json.dumps(mock_response.json.return_value).encode()
        mock_get.return_value = mock_response

        # Save credentials
        client.post(
            "/api/v1/integrations/whatsapp/credentials",
            json=valid_credentials,
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Attempt verification (should fail)
        client.post(
            "/api/v1/integrations/whatsapp/verify",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        # Check that error status persisted
        response = client.get(
            "/api/v1/integrations/whatsapp/status",
            headers={"Authorization": f"Bearer {admin_user.token}"},
        )

        data = response.json()
        assert data["data"]["connection_status"] == "not_connected"
        assert data["data"]["last_error"] is not None
        assert "failed" in data["data"]["last_error"].lower()
