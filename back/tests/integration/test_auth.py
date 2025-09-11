"""
Integration tests for authentication system
Tests complete auth workflows with real database connections
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.utils.jwt import decode_jwt, JWTError
from src.services.auth_service import AuthService, AuthError
from src.models.auth import RegisterRequest, LoginRequest, UserRole

class TestAuthIntegration:
    """Integration tests for authentication system"""
    
    @pytest.mark.asyncio
    async def test_register_workflow(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test complete user registration workflow"""
        # Test data
        register_data = {
            "name": "John Doe",
            "email": f"john_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecureP@ssw0rd123",
            "business_name": "John's Beauty Store",
            "whatsapp_phone_e164": f"+234801234567{uuid.uuid4().hex[:2]}"
        }
        
        # Register user
        response = await app_client.post("/api/v1/auth/register", json=register_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "data" in data
        
        # Verify response structure
        auth_data = data["data"]
        assert "token" in auth_data
        assert "user" in auth_data
        assert "merchant" in auth_data
        
        # Verify user data
        user = auth_data["user"]
        assert user["name"] == register_data["name"]
        assert user["email"] == register_data["email"]
        assert user["role"] == "admin"
        assert "id" in user
        assert "merchant_id" in user
        
        # Verify merchant data
        merchant = auth_data["merchant"]
        assert merchant["name"] == register_data["business_name"]
        assert merchant["whatsapp_phone_e164"] == register_data["whatsapp_phone_e164"]
        assert "id" in merchant
        
        # Verify JWT token
        token = auth_data["token"]
        payload = decode_jwt(token)
        assert payload["email"] == register_data["email"]
        assert payload["role"] == "admin"
        assert payload["merchant_id"] == str(merchant["id"])
        assert payload["sub"] == str(user["id"])
        
        # Verify database records
        user_result = await db_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": register_data["email"]}
        )
        db_user = user_result.fetchone()
        assert db_user is not None
        assert db_user.name == register_data["name"]
        assert db_user.role == "admin"
        
        merchant_result = await db_session.execute(
            text("SELECT * FROM merchants WHERE id = :id"),
            {"id": merchant["id"]}
        )
        db_merchant = merchant_result.fetchone()
        assert db_merchant is not None
        assert db_merchant.name == register_data["business_name"]
        
        return auth_data  # Return for use in other tests
    
    @pytest.mark.asyncio
    async def test_duplicate_email_registration(self, app_client: AsyncClient):
        """Test that duplicate email registration fails"""
        register_data = {
            "name": "John Doe",
            "email": f"duplicate_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecureP@ssw0rd123",
            "business_name": "John's Beauty Store",
            "whatsapp_phone_e164": f"+234801234567{uuid.uuid4().hex[:2]}"
        }
        
        # First registration should succeed
        response1 = await app_client.post("/api/v1/auth/register", json=register_data)
        assert response1.status_code == 200
        
        # Second registration with same email should fail
        response2 = await app_client.post("/api/v1/auth/register", json=register_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_workflow(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test complete user login workflow"""
        # First register a user
        auth_data = await self.test_register_workflow(app_client, db_session)
        
        # Login with correct credentials
        login_data = {
            "email": auth_data["user"]["email"],
            "password": "SecureP@ssw0rd123"
        }
        
        response = await app_client.post("/api/v1/auth/login", json=login_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "data" in data
        
        # Verify login response structure
        login_result = data["data"]
        assert "token" in login_result
        assert "user" in login_result
        
        # Verify JWT token
        token = login_result["token"]
        payload = decode_jwt(token)
        assert payload["email"] == login_data["email"]
        assert payload["role"] == "admin"
        
        # Verify last_login_at was updated
        user_result = await db_session.execute(
            text("SELECT last_login_at FROM users WHERE email = :email"),
            {"email": login_data["email"]}
        )
        db_user = user_result.fetchone()
        assert db_user.last_login_at is not None
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, app_client: AsyncClient):
        """Test login with invalid credentials"""
        # Try to login with non-existent user
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = await app_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test login with wrong password"""
        # First register a user
        auth_data = await self.test_register_workflow(app_client, db_session)
        
        # Try login with wrong password
        login_data = {
            "email": auth_data["user"]["email"],
            "password": "WrongPassword123"
        }
        
        response = await app_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test /me endpoint with valid token"""
        # First register and get token
        auth_data = await self.test_register_workflow(app_client, db_session)
        token = auth_data["token"]
        
        # Call /me endpoint
        response = await app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify user data
        user_data = data["data"]
        assert user_data["id"] == auth_data["user"]["id"]
        assert user_data["email"] == auth_data["user"]["email"]
        assert user_data["role"] == "admin"
        assert user_data["merchant_id"] == auth_data["user"]["merchant_id"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, app_client: AsyncClient):
        """Test /me endpoint with invalid token"""
        response = await app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, app_client: AsyncClient):
        """Test /me endpoint without token"""
        response = await app_client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # FastAPI HTTPBearer returns 403 for missing auth
    
    @pytest.mark.asyncio
    async def test_rls_isolation_after_auth(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test that RLS policies work after authentication"""
        # Register two different merchants/users
        auth_data_1 = await self.test_register_workflow(app_client, db_session)
        
        # Register second user with different email and phone
        register_data_2 = {
            "name": "Jane Smith",
            "email": f"jane_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecureP@ssw0rd456",
            "business_name": "Jane's Beauty Store",
            "whatsapp_phone_e164": f"+234801234567{uuid.uuid4().hex[:2]}"
        }
        
        response_2 = await app_client.post("/api/v1/auth/register", json=register_data_2)
        auth_data_2 = response_2.json()["data"]
        
        # Use first user's token to create a product
        token_1 = auth_data_1["token"]
        product_data = {
            "title": "Test Product",
            "description": "A test product",
            "price_kobo": 10000,
            "stock": 100,
            "sku": f"TEST-{uuid.uuid4().hex[:8]}"
        }
        
        # We would test product creation here, but since we don't have that endpoint yet,
        # we'll verify RLS by checking merchants table access
        
        # Create a new session with user 1's JWT claims
        claims_json = {
            "sub": str(auth_data_1["user"]["id"]),
            "merchant_id": str(auth_data_1["merchant"]["id"]),
            "email": auth_data_1["user"]["email"],
            "role": "admin"
        }
        
        # Set RLS claims for user 1
        await db_session.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": str(claims_json).replace("'", '"')}
        )
        
        # User 1 should only see their own merchant
        result_1 = await db_session.execute(text("SELECT id, name FROM merchants"))
        merchants_1 = result_1.fetchall()
        merchant_ids_1 = [str(m.id) for m in merchants_1]
        
        # Should only see own merchant (plus any test merchants from setup)
        assert str(auth_data_1["merchant"]["id"]) in merchant_ids_1
        # Should not see the other user's merchant
        assert str(auth_data_2["merchant"]["id"]) not in merchant_ids_1
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, app_client: AsyncClient):
        """Test rate limiting on login endpoint"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        # Make several failed login attempts
        for i in range(6):  # Rate limit is 5 attempts
            response = await app_client.post("/api/v1/auth/login", json=login_data)
            if i < 5:
                # First 5 should return 401 (invalid credentials)
                assert response.status_code == 401
            else:
                # 6th should be rate limited
                assert response.status_code == 429
                assert "Too many" in response.json()["detail"]
                break
    
    @pytest.mark.asyncio
    async def test_password_validation(self, app_client: AsyncClient):
        """Test password validation during registration"""
        # Test with weak password
        register_data = {
            "name": "John Doe",
            "email": f"weak_{uuid.uuid4().hex[:8]}@example.com",
            "password": "weak",  # Too short
            "business_name": "John's Store",
            "whatsapp_phone_e164": f"+234801234567{uuid.uuid4().hex[:2]}"
        }
        
        response = await app_client.post("/api/v1/auth/register", json=register_data)
        # Should fail validation due to password length
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_email_validation(self, app_client: AsyncClient):
        """Test email validation during registration"""
        register_data = {
            "name": "John Doe",
            "email": "invalid-email",  # Invalid email format
            "password": "SecureP@ssw0rd123",
            "business_name": "John's Store",
            "whatsapp_phone_e164": f"+234801234567{uuid.uuid4().hex[:2]}"
        }
        
        response = await app_client.post("/api/v1/auth/register", json=register_data)
        # Should fail validation due to email format
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_without_whatsapp(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test registration workflow without WhatsApp phone (minimal registration)"""
        # Test data without WhatsApp phone
        register_data = {
            "name": "Alice Johnson",
            "email": f"alice_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecureP@ssw0rd789",
            "business_name": "Alice's Boutique"
            # Note: whatsapp_phone_e164 is intentionally omitted
        }
        
        # Register user
        response = await app_client.post("/api/v1/auth/register", json=register_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "data" in data
        
        # Verify response structure
        auth_data = data["data"]
        assert "token" in auth_data
        assert "user" in auth_data
        assert "merchant" in auth_data
        
        # Verify user data
        user = auth_data["user"]
        assert user["name"] == register_data["name"]
        assert user["email"] == register_data["email"]
        assert user["role"] == "admin"
        
        # Verify merchant data - WhatsApp should be None/null
        merchant = auth_data["merchant"]
        assert merchant["name"] == register_data["business_name"]
        # WhatsApp phone should be None (null in JSON) when not provided
        assert merchant.get("whatsapp_phone_e164") is None
        
        # Verify database records
        merchant_result = await db_session.execute(
            text("SELECT * FROM merchants WHERE id = :id"),
            {"id": merchant["id"]}
        )
        db_merchant = merchant_result.fetchone()
        assert db_merchant is not None
        assert db_merchant.name == register_data["business_name"]
        # Database should have NULL for whatsapp_phone_e164
        assert db_merchant.whatsapp_phone_e164 is None
    
    @pytest.mark.asyncio
    async def test_register_with_whatsapp(self, app_client: AsyncClient, db_session: AsyncSession):
        """Test registration workflow with WhatsApp phone (complete registration)"""
        # Test data with WhatsApp phone
        register_data = {
            "name": "Bob Smith",
            "email": f"bob_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecureP@ssw0rd456",
            "business_name": "Bob's Electronics",
            "whatsapp_phone_e164": f"+234801234567{uuid.uuid4().hex[:2]}"
        }
        
        # Register user
        response = await app_client.post("/api/v1/auth/register", json=register_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify merchant data includes WhatsApp
        auth_data = data["data"]
        merchant = auth_data["merchant"]
        assert merchant["name"] == register_data["business_name"]
        assert merchant["whatsapp_phone_e164"] == register_data["whatsapp_phone_e164"]
        
        # Verify database records
        merchant_result = await db_session.execute(
            text("SELECT * FROM merchants WHERE id = :id"),
            {"id": merchant["id"]}
        )
        db_merchant = merchant_result.fetchone()
        assert db_merchant is not None
        assert db_merchant.whatsapp_phone_e164 == register_data["whatsapp_phone_e164"]


class TestAuthService:
    """Unit tests for AuthService class"""
    
    @pytest.mark.asyncio
    async def test_auth_service_register(self, db_session: AsyncSession):
        """Test AuthService register method directly"""
        auth_service = AuthService(db_session)
        
        request = RegisterRequest(
            name="Test User",
            email=f"service_{uuid.uuid4().hex[:8]}@example.com",
            password="TestPassword123",
            business_name="Test Business",
            whatsapp_phone_e164=f"+234801234567{uuid.uuid4().hex[:2]}"
        )
        
        result = await auth_service.register(request)
        
        # Verify result structure
        assert result.token is not None
        assert result.user.name == request.name
        assert result.user.email == request.email
        assert result.user.role == UserRole.ADMIN
        assert result.merchant.name == request.business_name
        
        # Verify JWT token
        payload = decode_jwt(result.token)
        assert payload["email"] == request.email
        assert payload["role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_auth_service_login(self, db_session: AsyncSession):
        """Test AuthService login method directly"""
        auth_service = AuthService(db_session)
        
        # First register a user
        register_request = RegisterRequest(
            name="Test User",
            email=f"login_{uuid.uuid4().hex[:8]}@example.com",
            password="TestPassword123",
            business_name="Test Business",
            whatsapp_phone_e164=f"+234801234567{uuid.uuid4().hex[:2]}"
        )
        
        await auth_service.register(register_request)
        
        # Then try to login
        login_request = LoginRequest(
            email=register_request.email,
            password="TestPassword123"
        )
        
        result = await auth_service.login(login_request)
        
        # Verify result
        assert result.token is not None
        assert result.user.email == login_request.email
        assert result.user.role == UserRole.ADMIN
        
        # Verify JWT token
        payload = decode_jwt(result.token)
        assert payload["email"] == login_request.email
    
    @pytest.mark.asyncio
    async def test_auth_service_login_invalid_credentials(self, db_session: AsyncSession):
        """Test AuthService login with invalid credentials"""
        auth_service = AuthService(db_session)
        
        login_request = LoginRequest(
            email="nonexistent@example.com",
            password="WrongPassword"
        )
        
        with pytest.raises(AuthError, match="Invalid credentials"):
            await auth_service.login(login_request)