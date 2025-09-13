"""
Integration tests for delivery rates CRUD operations
Tests complete workflows with real database connections and business validation
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.utils.jwt import decode_jwt
from src.models.api import CreateDeliveryRateRequest, UpdateDeliveryRateRequest
from src.services.delivery_rates_service import DeliveryRatesService, DeliveryRateError

class TestDeliveryRatesIntegration:
    """Integration tests for delivery rates system"""
    
    @pytest.mark.asyncio
    async def test_create_delivery_rate_workflow(self, app_client: AsyncClient, admin_user_token: str, db_session: AsyncSession):
        """Test complete delivery rate creation workflow"""
        # Test data
        rate_data = {
            "name": "Lagos Island Express",
            "areas_text": "Victoria Island, Ikoyi, Lagos Island, Lekki Phase 1",
            "price_kobo": 2500,
            "description": "Same day delivery within Lagos Island"
        }
        
        # Create delivery rate
        response = await app_client.post(
            "/api/v1/delivery-rates",
            json=rate_data,
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert "data" in data
        
        # Verify response structure
        rate = data["data"]
        assert rate["name"] == rate_data["name"]
        assert rate["areas_text"] == rate_data["areas_text"]
        assert rate["price_kobo"] == rate_data["price_kobo"]
        assert rate["description"] == rate_data["description"]
        assert rate["active"] is True
        assert "id" in rate
        assert "merchant_id" in rate
        assert "created_at" in rate
        assert "updated_at" in rate
        
        # Verify database record
        rate_result = await db_session.execute(
            text("SELECT * FROM delivery_rates WHERE id = :id"),
            {"id": rate["id"]}
        )
        db_rate = rate_result.fetchone()
        assert db_rate is not None
        assert db_rate.name == rate_data["name"]
        assert db_rate.areas_text == rate_data["areas_text"]
        assert db_rate.price_kobo == rate_data["price_kobo"]
        assert db_rate.description == rate_data["description"]
        assert db_rate.active is True
    
    @pytest.mark.asyncio
    async def test_list_delivery_rates_workflow(self, app_client: AsyncClient, admin_user_token: str, delivery_rates_fixture):
        """Test listing delivery rates with filtering"""
        # List all rates
        response = await app_client.get(
            "/api/v1/delivery-rates",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        rates = data["data"]
        assert len(rates) >= 2  # From fixture
        
        # Verify rate structure
        for rate in rates:
            assert "id" in rate
            assert "name" in rate
            assert "areas_text" in rate
            assert "price_kobo" in rate
            assert "active" in rate
        
        # List only active rates
        response = await app_client.get(
            "/api/v1/delivery-rates?active=true",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        active_rates = data["data"]
        for rate in active_rates:
            assert rate["active"] is True
        
        # List only inactive rates
        response = await app_client.get(
            "/api/v1/delivery-rates?active=false",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        inactive_rates = data["data"]
        for rate in inactive_rates:
            assert rate["active"] is False
    
    @pytest.mark.asyncio
    async def test_update_delivery_rate_workflow(self, app_client: AsyncClient, admin_user_token: str, delivery_rates_fixture, db_session: AsyncSession):
        """Test delivery rate update with business validation"""
        active_rate_id = delivery_rates_fixture["active_rate_id"]
        
        # Test successful update
        update_data = {
            "name": "Lagos Island Premium",
            "price_kobo": 3000,
            "description": "Premium same-day delivery"
        }
        
        response = await app_client.put(
            f"/api/v1/delivery-rates/{active_rate_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        updated_rate = data["data"]
        assert updated_rate["name"] == update_data["name"]
        assert updated_rate["price_kobo"] == update_data["price_kobo"]
        assert updated_rate["description"] == update_data["description"]
        assert updated_rate["active"] is True  # Should remain active
        
        # Verify database was updated
        rate_result = await db_session.execute(
            text("SELECT * FROM delivery_rates WHERE id = :id"),
            {"id": active_rate_id}
        )
        db_rate = rate_result.fetchone()
        assert db_rate.name == update_data["name"]
        assert db_rate.price_kobo == update_data["price_kobo"]
    
    @pytest.mark.asyncio
    async def test_update_rate_business_validation(self, app_client: AsyncClient, admin_user_token: str, single_active_rate_fixture, db_session: AsyncSession):
        """Test 'at least one active rule' validation on update"""
        rate_id = single_active_rate_fixture["rate_id"]
        
        # Try to deactivate the only active rate - should fail
        update_data = {"active": False}
        
        response = await app_client.put(
            f"/api/v1/delivery-rates/{rate_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert data["ok"] is False
        assert "at least one active" in data["error"]["message"].lower()
        
        # Verify rate is still active in database
        rate_result = await db_session.execute(
            text("SELECT active FROM delivery_rates WHERE id = :id"),
            {"id": rate_id}
        )
        db_rate = rate_result.fetchone()
        assert db_rate.active is True
    
    @pytest.mark.asyncio
    async def test_delete_delivery_rate_workflow(self, app_client: AsyncClient, admin_user_token: str, delivery_rates_fixture, db_session: AsyncSession):
        """Test delivery rate deletion with business validation"""
        inactive_rate_id = delivery_rates_fixture["inactive_rate_id"]
        
        # Delete inactive rate (should succeed)
        response = await app_client.delete(
            f"/api/v1/delivery-rates/{inactive_rate_id}",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["deleted"] is True
        
        # Verify rate is deleted from database
        rate_result = await db_session.execute(
            text("SELECT * FROM delivery_rates WHERE id = :id"),
            {"id": inactive_rate_id}
        )
        db_rate = rate_result.fetchone()
        assert db_rate is None
    
    @pytest.mark.asyncio
    async def test_delete_rate_business_validation(self, app_client: AsyncClient, admin_user_token: str, single_active_rate_fixture, db_session: AsyncSession):
        """Test 'at least one active rule' validation on delete"""
        rate_id = single_active_rate_fixture["rate_id"]
        
        # Try to delete the only active rate - should fail
        response = await app_client.delete(
            f"/api/v1/delivery-rates/{rate_id}",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert data["ok"] is False
        assert "at least one active" in data["error"]["message"].lower()
        
        # Verify rate still exists in database
        rate_result = await db_session.execute(
            text("SELECT * FROM delivery_rates WHERE id = :id"),
            {"id": rate_id}
        )
        db_rate = rate_result.fetchone()
        assert db_rate is not None
        assert db_rate.active is True
    
    @pytest.mark.asyncio
    async def test_staff_user_access_control(self, app_client: AsyncClient, staff_user_token: str):
        """Test that staff users can read but not write delivery rates"""
        # Staff can list rates
        response = await app_client.get(
            "/api/v1/delivery-rates",
            headers={"Authorization": f"Bearer {staff_user_token}"}
        )
        assert response.status_code == 200
        
        # Staff cannot create rates
        rate_data = {
            "name": "Test Rate",
            "areas_text": "Test Area",
            "price_kobo": 1000
        }
        
        response = await app_client.post(
            "/api/v1/delivery-rates",
            json=rate_data,
            headers={"Authorization": f"Bearer {staff_user_token}"}
        )
        assert response.status_code == 403  # Forbidden
        
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, app_client: AsyncClient):
        """Test that unauthenticated requests are rejected"""
        # No token - should fail
        response = await app_client.get("/api/v1/delivery-rates")
        assert response.status_code == 401
        
        # Invalid token - should fail
        response = await app_client.get(
            "/api/v1/delivery-rates",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self, app_client: AsyncClient, admin_user_token: str, other_merchant_admin_token: str, delivery_rates_fixture):
        """Test that merchants cannot access other merchants' delivery rates"""
        rate_id = delivery_rates_fixture["active_rate_id"]
        
        # Try to access rate from different merchant - should not be found
        response = await app_client.get(
            "/api/v1/delivery-rates",
            headers={"Authorization": f"Bearer {other_merchant_admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        rates = data["data"]
        
        # Should not see the other merchant's rates
        rate_ids = [rate["id"] for rate in rates]
        assert rate_id not in rate_ids
        
        # Try to update other merchant's rate - should fail
        response = await app_client.put(
            f"/api/v1/delivery-rates/{rate_id}",
            json={"name": "Hacked Rate"},
            headers={"Authorization": f"Bearer {other_merchant_admin_token}"}
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_validation_errors(self, app_client: AsyncClient, admin_user_token: str):
        """Test input validation on create and update"""
        # Create with invalid data
        invalid_data = {
            "name": "",  # Empty name
            "areas_text": "",  # Empty areas
            "price_kobo": -100  # Negative price
        }
        
        response = await app_client.post(
            "/api/v1/delivery-rates",
            json=invalid_data,
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        assert response.status_code == 422  # Validation error
        
        # Create rate first for update test
        valid_data = {
            "name": "Test Rate",
            "areas_text": "Test Area",
            "price_kobo": 1000
        }
        
        response = await app_client.post(
            "/api/v1/delivery-rates",
            json=valid_data,
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        assert response.status_code == 201
        rate_id = response.json()["data"]["id"]
        
        # Update with invalid data
        invalid_update = {
            "price_kobo": -500  # Negative price
        }
        
        response = await app_client.put(
            f"/api/v1/delivery-rates/{rate_id}",
            json=invalid_update,
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_not_found_errors(self, app_client: AsyncClient, admin_user_token: str):
        """Test handling of non-existent delivery rates"""
        fake_uuid = str(uuid.uuid4())
        
        # Update non-existent rate
        response = await app_client.put(
            f"/api/v1/delivery-rates/{fake_uuid}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        assert response.status_code == 404
        
        # Delete non-existent rate
        response = await app_client.delete(
            f"/api/v1/delivery-rates/{fake_uuid}",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        assert response.status_code == 404


# Test Fixtures
@pytest.fixture
async def delivery_rates_fixture(db_session: AsyncSession, test_merchant_id: str):
    """Create test delivery rates for a merchant"""
    active_rate_id = str(uuid.uuid4())
    inactive_rate_id = str(uuid.uuid4())
    
    # Create active rate
    await db_session.execute(
        text("""
            INSERT INTO delivery_rates (id, merchant_id, name, areas_text, price_kobo, description, active)
            VALUES (:id, :merchant_id, :name, :areas_text, :price_kobo, :description, :active)
        """),
        {
            "id": active_rate_id,
            "merchant_id": test_merchant_id,
            "name": "Lagos Mainland",
            "areas_text": "Ikeja, Surulere, Yaba",
            "price_kobo": 1500,
            "description": "Next day delivery",
            "active": True
        }
    )
    
    # Create inactive rate
    await db_session.execute(
        text("""
            INSERT INTO delivery_rates (id, merchant_id, name, areas_text, price_kobo, description, active)
            VALUES (:id, :merchant_id, :name, :areas_text, :price_kobo, :description, :active)
        """),
        {
            "id": inactive_rate_id,
            "merchant_id": test_merchant_id,
            "name": "Lagos Island",
            "areas_text": "Victoria Island, Ikoyi",
            "price_kobo": 2000,
            "description": "Same day delivery",
            "active": False
        }
    )
    
    await db_session.commit()
    
    return {
        "active_rate_id": active_rate_id,
        "inactive_rate_id": inactive_rate_id
    }

@pytest.fixture
async def single_active_rate_fixture(db_session: AsyncSession, test_merchant_id: str):
    """Create a single active delivery rate (for testing business validation)"""
    rate_id = str(uuid.uuid4())
    
    await db_session.execute(
        text("""
            INSERT INTO delivery_rates (id, merchant_id, name, areas_text, price_kobo, active)
            VALUES (:id, :merchant_id, :name, :areas_text, :price_kobo, :active)
        """),
        {
            "id": rate_id,
            "merchant_id": test_merchant_id,
            "name": "Only Active Rate",
            "areas_text": "Test Area",
            "price_kobo": 1000,
            "active": True
        }
    )
    
    await db_session.commit()
    
    return {"rate_id": rate_id}