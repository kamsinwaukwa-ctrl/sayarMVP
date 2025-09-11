"""
Pytest configuration for Sayar backend tests
"""

import pytest
import pytest_asyncio
import jwt
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.database.connection import get_db
from src.models.database import Base
from src.utils.jwt import create_access_token

# Reusable ASGI transport for the app (no deprecation warnings)
_transport = ASGITransport(app=app)

# Test database URL - Use PostgreSQL for testing
import os

# Set testing environment variable
os.environ["TESTING"] = "true"

# Use PostgreSQL for testing
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/sayar_test"

@pytest.fixture(scope="function")
async def test_db():
    """Create a test database session"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def test_client() -> AsyncClient:
    """Create async test client with independent database"""
    # Create separate database engine for this test
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Setup database dependency override
        async def override_get_db():
            yield session
            
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            async with AsyncClient(transport=_transport, base_url="http://testserver") as ac:
                yield ac
        finally:
            app.dependency_overrides.clear()
            
    # Clean up database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(test_client: AsyncClient) -> AsyncClient:
    """Alias for test_client fixture for backward compatibility"""
    yield test_client

@pytest.fixture
def merchant_token():
    """Create a test merchant JWT token"""
    return create_access_token(
        data={
            "sub": "test-merchant",
            "role": "merchant",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
    )

@pytest.fixture
def admin_token():
    """Create a test admin JWT token"""
    return create_access_token(
        data={
            "sub": "test-admin",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
    )

# app_client fixture removed in favor of test_client and client fixtures

@pytest.fixture(scope="function")
async def db_session():
    """Provides database session for direct database operations"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        
    # Clean up database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for unit tests"""
    class MockSupabase:
        async def rpc(self, *args, **kwargs):
            return {"data": None, "error": None}
            
    return MockSupabase()