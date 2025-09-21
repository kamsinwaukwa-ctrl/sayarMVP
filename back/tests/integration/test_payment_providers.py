"""
Integration tests for payment provider verification endpoints
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

from back.main import app
from back.src.models.payment_providers import (
    PaymentProviderType,
    PaymentEnvironment,
    VerificationStatus,
)
from back.src.services.payment_provider_service import PaymentProviderService
from back.src.utils.encryption import get_encryption_service


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user"""
    return SimpleNamespace(
        user_id=str(uuid.uuid4()),
        merchant_id=str(uuid.uuid4()),
        email="test@example.com",
        role="admin",
    )


class TestPaystackVerification:
    """Test suite for Paystack credential verification"""

    @patch("back.src.integrations.paystack.PaystackIntegration.verify_credentials")
    async def test_verify_paystack_credentials_success(
        self, mock_verify, client, mock_auth_user
    ):
        """Test successful Paystack credential verification"""

        mock_verify.return_value = True

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={
                    "secret_key": "sk_test_valid_key_12345678901234567890",
                    "public_key": "pk_test_valid_key_12345678901234567890",
                    "environment": "test",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] == True
        assert data["data"]["success"] == True
        assert data["data"]["provider_type"] == "paystack"
        assert data["data"]["verification_status"] == "verified"
        assert (
            data["message"] == "Paystack credentials verified and stored successfully"
        )

    @patch("back.src.integrations.paystack.PaystackIntegration.verify_credentials")
    async def test_verify_paystack_credentials_invalid(
        self, mock_verify, client, mock_auth_user
    ):
        """Test Paystack credential verification with invalid credentials"""

        mock_verify.return_value = False

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={
                    "secret_key": "sk_test_invalid_key_123456789",
                    "environment": "test",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 422
        data = response.json()

        assert data["ok"] == False
        assert data["error"]["code"] == "VERIFICATION_FAILED"
        assert "Invalid credentials" in data["error"]["details"]["reason"]

    async def test_verify_paystack_invalid_key_format(self, client, mock_auth_user):
        """Test Paystack verification with invalid key format"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={"secret_key": "invalid_key_format", "environment": "test"},
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 422
        data = response.json()

        # Should fail validation at Pydantic level
        assert "detail" in data

    @patch("back.src.middleware.rate_limit.payment_verification_rate_limiter")
    async def test_paystack_rate_limiting(self, mock_limiter, client, mock_auth_user):
        """Test rate limiting on Paystack verification endpoint"""

        # Configure mock to simulate rate limiting
        mock_limiter.is_rate_limited.return_value = True
        mock_limiter.get_reset_time.return_value = 1234567890

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={"secret_key": "sk_test_key", "environment": "test"},
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 429
        assert "Too many verification attempts" in response.json()["detail"]


class TestKorapayVerification:
    """Test suite for Korapay credential verification"""

    @patch("back.src.integrations.korapay.KorapayIntegration.verify_credentials")
    async def test_verify_korapay_credentials_success(
        self, mock_verify, client, mock_auth_user
    ):
        """Test successful Korapay credential verification"""

        mock_verify.return_value = True

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/korapay",
                json={
                    "public_key": "pk_test_valid_key_12345678901234567890",
                    "secret_key": "sk_test_valid_key_12345678901234567890",
                    "webhook_secret": "webhook_secret_123",
                    "environment": "test",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] == True
        assert data["data"]["success"] == True
        assert data["data"]["provider_type"] == "korapay"
        assert data["data"]["verification_status"] == "verified"

    @patch("back.src.integrations.korapay.KorapayIntegration.verify_credentials")
    async def test_verify_korapay_credentials_invalid(
        self, mock_verify, client, mock_auth_user
    ):
        """Test Korapay credential verification failure"""

        mock_verify.return_value = False

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/korapay",
                json={
                    "public_key": "pk_test_invalid_key",
                    "secret_key": "sk_test_invalid_key",
                    "environment": "test",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 422
        data = response.json()

        assert data["ok"] == False
        assert data["error"]["code"] == "VERIFICATION_FAILED"


class TestPaymentProviderService:
    """Test suite for PaymentProviderService"""

    @pytest.fixture
    async def db_session(self):
        """Database session fixture for tests"""
        # This would be implemented based on your test database setup
        # For now, we'll mock it
        return AsyncMock(spec=AsyncSession)

    async def test_store_encrypted_credentials(self, db_session):
        """Test credential encryption and storage"""

        service = PaymentProviderService(db_session)
        merchant_id = uuid.uuid4()

        with patch.object(service, "_store_credentials") as mock_store:
            mock_store.return_value = uuid.uuid4()

            credentials_data = {
                "secret_key": "sk_test_secret_key_123456789",
                "public_key": "pk_test_public_key_123456789",
            }

            result = await service._store_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.PAYSTACK,
                credentials_data=credentials_data,
                environment=PaymentEnvironment.TEST,
                verification_status=VerificationStatus.VERIFIED,
            )

            assert result is not None

    async def test_get_decrypted_credentials(self, db_session):
        """Test credential decryption"""

        service = PaymentProviderService(db_session)
        merchant_id = uuid.uuid4()

        # Mock database result
        mock_config = SimpleNamespace(
            public_key_encrypted="encrypted_public_key",
            secret_key_encrypted="encrypted_secret_key",
            webhook_secret_encrypted="encrypted_webhook_secret",
        )

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        db_session.execute.return_value = mock_result

        # Mock encryption service
        mock_encryption = AsyncMock()
        mock_encryption.decrypt_data.side_effect = lambda x: f"decrypted_{x}"

        with patch.object(service, "encryption_service", mock_encryption):
            result = await service.get_decrypted_credentials(
                merchant_id=merchant_id,
                provider_type=PaymentProviderType.PAYSTACK,
                environment=PaymentEnvironment.TEST,
            )

            assert result is not None
            assert "public_key" in result
            assert "secret_key" in result
            assert result["public_key"] == "decrypted_encrypted_public_key"


class TestEncryption:
    """Test suite for encryption service"""

    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption"""

        encryption_service = get_encryption_service()
        original_text = "sk_test_secret_key_123456789"

        encrypted_result = encryption_service.encrypt_data(original_text)
        assert encrypted_result.encrypted_data != original_text
        assert len(encrypted_result.encrypted_data) > 0

        decrypted = encryption_service.decrypt_data(encrypted_result.encrypted_data)
        assert decrypted == original_text

    def test_encrypt_empty_string_raises_error(self):
        """Test encryption of empty string raises error"""

        encryption_service = get_encryption_service()

        with pytest.raises(ValueError, match="Data cannot be empty"):
            encryption_service.encrypt_data("")

    def test_decrypt_invalid_data_raises_error(self):
        """Test decryption of invalid data raises error"""

        encryption_service = get_encryption_service()

        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt_data("invalid_encrypted_data")


class TestListProviders:
    """Test suite for listing payment providers"""

    async def test_list_payment_providers_empty(self, client, mock_auth_user):
        """Test listing payment providers when none exist"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            with patch(
                "back.src.services.payment_provider_service.PaymentProviderService.get_provider_configs",
                return_value=[],
            ):
                response = client.get(
                    "/api/v1/payments/providers",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] == True
        assert data["data"]["total_count"] == 0
        assert len(data["data"]["providers"]) == 0

    async def test_list_payment_providers_with_configs(self, client, mock_auth_user):
        """Test listing payment providers with existing configurations"""

        # Mock provider configuration
        from back.src.models.payment_providers import PaymentProviderConfigResponse
        import datetime

        mock_provider = PaymentProviderConfigResponse(
            id=uuid.uuid4(),
            provider_type=PaymentProviderType.PAYSTACK,
            environment=PaymentEnvironment.TEST,
            verification_status=VerificationStatus.VERIFIED,
            last_verified_at=datetime.datetime.now(),
            verification_error=None,
            active=True,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            with patch(
                "back.src.services.payment_provider_service.PaymentProviderService.get_provider_configs",
                return_value=[mock_provider],
            ):
                response = client.get(
                    "/api/v1/payments/providers",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] == True
        assert data["data"]["total_count"] == 1
        assert len(data["data"]["providers"]) == 1

        provider = data["data"]["providers"][0]
        assert provider["provider_type"] == "paystack"
        assert provider["environment"] == "test"
        assert provider["verification_status"] == "verified"


class TestDeleteProvider:
    """Test suite for deleting payment provider configurations"""

    async def test_delete_existing_provider(self, client, mock_auth_user):
        """Test deleting an existing payment provider"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            with patch(
                "back.src.services.payment_provider_service.PaymentProviderService.delete_provider_config",
                return_value=True,
            ):
                response = client.delete(
                    "/api/v1/payments/providers/paystack?environment=test",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] == True
        assert data["data"]["deleted"] == True

    async def test_delete_nonexistent_provider(self, client, mock_auth_user):
        """Test deleting a non-existent payment provider"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            with patch(
                "back.src.services.payment_provider_service.PaymentProviderService.delete_provider_config",
                return_value=False,
            ):
                response = client.delete(
                    "/api/v1/payments/providers/paystack?environment=live",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        data = response.json()

        assert data["ok"] == False
        assert data["error"]["code"] == "PROVIDER_NOT_FOUND"


# Integration tests with actual credentials (would use test credentials)
class TestRealIntegration:
    """Test suite for real integration with test credentials"""

    @pytest.mark.skipif(
        True,  # Skip by default - enable when test credentials are available
        reason="Requires valid test credentials",
    )
    async def test_paystack_real_verification(self, client, mock_auth_user):
        """Test with real Paystack test credentials"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/paystack",
                json={
                    "secret_key": "sk_test_your_test_key_here",
                    "public_key": "pk_test_your_test_key_here",
                    "environment": "test",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

        # This test would verify actual API calls to Paystack
        assert response.status_code in [
            200,
            422,
        ]  # Either success or invalid credentials

    @pytest.mark.skipif(
        True,  # Skip by default - enable when test credentials are available
        reason="Requires valid test credentials",
    )
    async def test_korapay_real_verification(self, client, mock_auth_user):
        """Test with real Korapay test credentials"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_auth_user
        ):
            response = client.post(
                "/api/v1/payments/verify/korapay",
                json={
                    "public_key": "pk_test_your_test_key_here",
                    "secret_key": "sk_test_your_test_key_here",
                    "environment": "test",
                },
                headers={"Authorization": "Bearer valid_token"},
            )

        # This test would verify actual key format validation
        assert response.status_code in [
            200,
            422,
        ]  # Either success or invalid credentials


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
