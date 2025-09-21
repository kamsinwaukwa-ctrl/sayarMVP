"""
Integration tests for discounts CRUD and validation endpoints
Tests cover complete discount lifecycle and business validation rules
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

from back.main import app
from back.src.models.sqlalchemy_models import Discount
from back.src.services.discounts_service import DiscountsService


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Mock admin user"""
    return SimpleNamespace(
        user_id=str(uuid.uuid4()),
        merchant_id=str(uuid.uuid4()),
        email="admin@example.com",
        role="admin",
    )


@pytest.fixture
def mock_staff_user():
    """Mock staff user"""
    return SimpleNamespace(
        user_id=str(uuid.uuid4()),
        merchant_id=str(uuid.uuid4()),
        email="staff@example.com",
        role="staff",
    )


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)


class TestDiscountCRUD:
    """Test suite for discount CRUD operations"""

    def test_create_percent_discount_success(self, client, mock_admin_user):
        """Test successful creation of percentage discount"""

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.create_discount"
            ) as mock_create:
                # Mock successful creation
                mock_discount = SimpleNamespace(
                    id=uuid.uuid4(),
                    code="SUMMER25",
                    type="percent",
                    value_bp=2500,
                    merchant_id=mock_admin_user.merchant_id,
                    status="active",
                )
                mock_create.return_value = mock_discount

                response = client.post(
                    "/api/v1/discounts",
                    json={
                        "code": "SUMMER25",
                        "type": "percent",
                        "value_bp": 2500,
                        "max_discount_kobo": 5000,
                        "min_subtotal_kobo": 10000,
                        "expires_at": "2025-12-31T23:59:59Z",
                        "usage_limit_total": 100,
                        "usage_limit_per_customer": 1,
                    },
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] == True
        assert "SUMMER25" in data["message"]

    def test_create_fixed_discount_success(self, client, mock_admin_user):
        """Test successful creation of fixed discount"""

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.create_discount"
            ) as mock_create:
                mock_discount = SimpleNamespace(
                    id=uuid.uuid4(),
                    code="SAVE20",
                    type="fixed",
                    amount_kobo=2000,
                    merchant_id=mock_admin_user.merchant_id,
                    status="active",
                )
                mock_create.return_value = mock_discount

                response = client.post(
                    "/api/v1/discounts",
                    json={
                        "code": "SAVE20",
                        "type": "fixed",
                        "amount_kobo": 2000,
                        "min_subtotal_kobo": 5000,
                        "usage_limit_total": 50,
                    },
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] == True

    def test_create_duplicate_code_conflict(self, client, mock_admin_user):
        """Test creation with duplicate code returns 409"""

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.create_discount"
            ) as mock_create:
                from back.src.services.discounts_service import DiscountError

                mock_create.side_effect = DiscountError(
                    "Discount code 'DUPLICATE' already exists"
                )

                response = client.post(
                    "/api/v1/discounts",
                    json={"code": "DUPLICATE", "type": "percent", "value_bp": 1000},
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_invalid_percentage_400(self, client, mock_admin_user):
        """Test creation with invalid percentage returns 400"""

        response = client.post(
            "/api/v1/discounts",
            json={
                "code": "INVALID",
                "type": "percent",
                "value_bp": 15000,  # > 10000 (100%)
            },
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_create_staff_forbidden(self, client, mock_staff_user):
        """Test staff user cannot create discounts"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_staff_user
        ):
            response = client.post(
                "/api/v1/discounts",
                json={"code": "STAFF", "type": "fixed", "amount_kobo": 1000},
                headers={"Authorization": "Bearer staff_token"},
            )

        # Should fail at auth dependency level (403 or 401 depending on implementation)
        assert response.status_code in [401, 403]

    def test_list_discounts_success(self, client, mock_admin_user):
        """Test listing discounts returns merchant's discounts"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.list_discounts"
            ) as mock_list:
                mock_discounts = [
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        code="DISCOUNT1",
                        type="percent",
                        status="active",
                    ),
                    SimpleNamespace(
                        id=uuid.uuid4(), code="DISCOUNT2", type="fixed", status="paused"
                    ),
                ]
                mock_list.return_value = mock_discounts

                response = client.get(
                    "/api/v1/discounts", headers={"Authorization": "Bearer admin_token"}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "Retrieved 2 discounts" in data["message"]

    def test_list_discounts_with_filters(self, client, mock_admin_user):
        """Test listing discounts with status filter"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.list_discounts"
            ) as mock_list:
                mock_list.return_value = []

                response = client.get(
                    "/api/v1/discounts?status=active&active=true",
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 200
        mock_list.assert_called_once_with(
            merchant_id=uuid.UUID(mock_admin_user.merchant_id),
            status="active",
            active_only=True,
        )

    def test_update_discount_success(self, client, mock_admin_user):
        """Test successful discount update"""

        discount_id = str(uuid.uuid4())

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.update_discount"
            ) as mock_update:
                mock_discount = SimpleNamespace(
                    id=discount_id, code="UPDATED", status="paused"
                )
                mock_update.return_value = mock_discount

                response = client.put(
                    f"/api/v1/discounts/{discount_id}",
                    json={"status": "paused"},
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "updated successfully" in data["message"]

    def test_update_nonexistent_discount_404(self, client, mock_admin_user):
        """Test updating nonexistent discount returns 404"""

        discount_id = str(uuid.uuid4())

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.update_discount"
            ) as mock_update:
                from back.src.services.discounts_service import DiscountError

                mock_update.side_effect = DiscountError(
                    f"Discount with ID {discount_id} not found"
                )

                response = client.put(
                    f"/api/v1/discounts/{discount_id}",
                    json={"status": "paused"},
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_delete_discount_success(self, client, mock_admin_user):
        """Test successful discount deletion"""

        discount_id = str(uuid.uuid4())

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.delete_discount"
            ) as mock_delete:
                mock_delete.return_value = True

                response = client.delete(
                    f"/api/v1/discounts/{discount_id}",
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 204

    def test_delete_nonexistent_discount_404(self, client, mock_admin_user):
        """Test deleting nonexistent discount returns 404"""

        discount_id = str(uuid.uuid4())

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.delete_discount"
            ) as mock_delete:
                mock_delete.return_value = False

                response = client.delete(
                    f"/api/v1/discounts/{discount_id}",
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 404


class TestDiscountValidation:
    """Test suite for discount validation logic"""

    def test_validate_active_discount_success(self, client, mock_admin_user):
        """Test validation of active, valid discount"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.validate_discount"
            ) as mock_validate:
                from back.src.models.api import DiscountValidationResponse

                mock_validate.return_value = DiscountValidationResponse(
                    valid=True, discount_kobo=2000
                )

                response = client.post(
                    "/api/v1/discounts/validate",
                    json={
                        "code": "SUMMER20",
                        "subtotal_kobo": 10000,
                        "customer_id": str(uuid.uuid4()),
                    },
                    headers={"Authorization": "Bearer token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["data"]["valid"] == True
        assert data["data"]["discount_kobo"] == 2000

    def test_validate_expired_discount_fails(self, client, mock_admin_user):
        """Test validation of expired discount fails"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.validate_discount"
            ) as mock_validate:
                from back.src.models.api import DiscountValidationResponse

                mock_validate.return_value = DiscountValidationResponse(
                    valid=False, reason="Discount has expired"
                )

                response = client.post(
                    "/api/v1/discounts/validate",
                    json={"code": "EXPIRED", "subtotal_kobo": 10000},
                    headers={"Authorization": "Bearer token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] == False
        assert "expired" in data["data"]["reason"]

    def test_validate_minimum_subtotal_not_met(self, client, mock_admin_user):
        """Test validation fails when minimum subtotal not met"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.validate_discount"
            ) as mock_validate:
                from back.src.models.api import DiscountValidationResponse

                mock_validate.return_value = DiscountValidationResponse(
                    valid=False,
                    reason="Minimum order amount not met (required: ₦100.00)",
                )

                response = client.post(
                    "/api/v1/discounts/validate",
                    json={"code": "HIGHMIN", "subtotal_kobo": 5000},  # Below minimum
                    headers={"Authorization": "Bearer token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] == False
        assert "Minimum order" in data["data"]["reason"]

    def test_validate_usage_limit_exceeded(self, client, mock_admin_user):
        """Test validation fails when usage limit exceeded"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.validate_discount"
            ) as mock_validate:
                from back.src.models.api import DiscountValidationResponse

                mock_validate.return_value = DiscountValidationResponse(
                    valid=False, reason="Discount usage limit exceeded"
                )

                response = client.post(
                    "/api/v1/discounts/validate",
                    json={"code": "MAXEDOUT", "subtotal_kobo": 10000},
                    headers={"Authorization": "Bearer token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] == False
        assert "usage limit exceeded" in data["data"]["reason"]

    def test_validate_nonexistent_code(self, client, mock_admin_user):
        """Test validation of nonexistent discount code"""

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.validate_discount"
            ) as mock_validate:
                from back.src.models.api import DiscountValidationResponse

                mock_validate.return_value = DiscountValidationResponse(
                    valid=False, reason="Discount code not found"
                )

                response = client.post(
                    "/api/v1/discounts/validate",
                    json={"code": "NOTFOUND", "subtotal_kobo": 10000},
                    headers={"Authorization": "Bearer token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] == False
        assert "not found" in data["data"]["reason"]


class TestDiscountServiceLogic:
    """Test suite for DiscountService business logic"""

    @pytest.fixture
    async def service(self, mock_db_session):
        """Service fixture"""
        return DiscountsService(mock_db_session)

    async def test_percentage_discount_calculation(self):
        """Test percentage discount amount calculation"""
        service = DiscountsService(AsyncMock())

        # Create mock discount
        discount = SimpleNamespace(
            type="percent",
            value_bp=2500,  # 25%
            max_discount_kobo=None,
            amount_kobo=None,
        )

        # Test calculation
        result = service._calculate_discount_amount(discount, 10000)
        assert result == 2500  # 25% of 10000 kobo

    async def test_percentage_discount_with_cap(self):
        """Test percentage discount with maximum cap"""
        service = DiscountsService(AsyncMock())

        discount = SimpleNamespace(
            type="percent",
            value_bp=5000,  # 50%
            max_discount_kobo=3000,  # Cap at 30 naira
            amount_kobo=None,
        )

        result = service._calculate_discount_amount(discount, 10000)
        assert result == 3000  # Capped at max_discount_kobo

    async def test_fixed_discount_calculation(self):
        """Test fixed discount amount calculation"""
        service = DiscountsService(AsyncMock())

        discount = SimpleNamespace(
            type="fixed", amount_kobo=2000, value_bp=None, max_discount_kobo=None
        )

        result = service._calculate_discount_amount(discount, 10000)
        assert result == 2000

    async def test_fixed_discount_cannot_exceed_subtotal(self):
        """Test fixed discount cannot exceed order subtotal"""
        service = DiscountsService(AsyncMock())

        discount = SimpleNamespace(
            type="fixed",
            amount_kobo=8000,  # More than subtotal
            value_bp=None,
            max_discount_kobo=None,
        )

        result = service._calculate_discount_amount(discount, 5000)
        assert result == 5000  # Limited to subtotal


class TestMultiTenantIsolation:
    """Test suite for multi-tenant isolation"""

    def test_list_discounts_merchant_isolation(self, client):
        """Test merchants can only see their own discounts"""

        merchant_a = SimpleNamespace(
            user_id=str(uuid.uuid4()),
            merchant_id=str(uuid.uuid4()),
            email="a@example.com",
            role="admin",
        )

        merchant_b = SimpleNamespace(
            user_id=str(uuid.uuid4()),
            merchant_id=str(uuid.uuid4()),
            email="b@example.com",
            role="admin",
        )

        # Test merchant A sees only their discounts
        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=merchant_a
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.list_discounts"
            ) as mock_list:
                mock_list.return_value = []

                response = client.get(
                    "/api/v1/discounts", headers={"Authorization": "Bearer token_a"}
                )

                # Verify service was called with merchant A's ID
                mock_list.assert_called_once()
                call_args = mock_list.call_args[1]
                assert str(call_args["merchant_id"]) == merchant_a.merchant_id

        # Test merchant B sees only their discounts
        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=merchant_b
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.list_discounts"
            ) as mock_list:
                mock_list.return_value = []

                response = client.get(
                    "/api/v1/discounts", headers={"Authorization": "Bearer token_b"}
                )

                # Verify service was called with merchant B's ID
                mock_list.assert_called_once()
                call_args = mock_list.call_args[1]
                assert str(call_args["merchant_id"]) == merchant_b.merchant_id

    def test_validate_discount_merchant_isolation(self, client):
        """Test discount validation is scoped to merchant"""

        merchant_a = SimpleNamespace(
            user_id=str(uuid.uuid4()),
            merchant_id=str(uuid.uuid4()),
            email="a@example.com",
            role="admin",
        )

        with patch(
            "back.src.dependencies.auth.get_current_user", return_value=merchant_a
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.validate_discount"
            ) as mock_validate:
                from back.src.models.api import DiscountValidationResponse

                mock_validate.return_value = DiscountValidationResponse(
                    valid=False, reason="Discount code not found"
                )

                response = client.post(
                    "/api/v1/discounts/validate",
                    json={"code": "MERCHANT_B_CODE", "subtotal_kobo": 10000},
                    headers={"Authorization": "Bearer token_a"},
                )

                # Verify service was called with merchant A's ID
                mock_validate.assert_called_once()
                call_args = mock_validate.call_args[1]
                assert str(call_args["merchant_id"]) == merchant_a.merchant_id


class TestEdgeCases:
    """Test suite for edge cases and error conditions"""

    def test_create_discount_invalid_date_range(self, client, mock_admin_user):
        """Test creation with starts_at after expires_at fails"""

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.create_discount"
            ) as mock_create:
                from back.src.services.discounts_service import DiscountError

                mock_create.side_effect = DiscountError(
                    "starts_at must be before expires_at"
                )

                response = client.post(
                    "/api/v1/discounts",
                    json={
                        "code": "BADDATE",
                        "type": "percent",
                        "value_bp": 1000,
                        "starts_at": "2025-12-31T23:59:59Z",
                        "expires_at": "2025-01-01T00:00:00Z",
                    },
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 400

    def test_update_expired_discount_reactivation_fails(self, client, mock_admin_user):
        """Test cannot reactivate expired discount"""

        discount_id = str(uuid.uuid4())

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.update_discount"
            ) as mock_update:
                from back.src.services.discounts_service import DiscountError

                mock_update.side_effect = DiscountError(
                    "Cannot reactivate expired discount"
                )

                response = client.put(
                    f"/api/v1/discounts/{discount_id}",
                    json={"status": "active"},
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 400

    def test_reduce_usage_limit_below_current_usage_fails(
        self, client, mock_admin_user
    ):
        """Test cannot reduce usage limit below current redemptions"""

        discount_id = str(uuid.uuid4())

        with patch(
            "back.src.dependencies.auth.get_current_admin", return_value=mock_admin_user
        ):
            with patch(
                "back.src.services.discounts_service.DiscountsService.update_discount"
            ) as mock_update:
                from back.src.services.discounts_service import DiscountError

                mock_update.side_effect = DiscountError(
                    "usage_limit_total cannot be less than current redemptions (50)"
                )

                response = client.put(
                    f"/api/v1/discounts/{discount_id}",
                    json={"usage_limit_total": 25},
                    headers={"Authorization": "Bearer admin_token"},
                )

        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
