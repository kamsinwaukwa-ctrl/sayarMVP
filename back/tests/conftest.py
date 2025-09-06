"""
Pytest configuration for Sayar backend tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(scope="session")
def test_db():
    """
    Create a test database session
    TODO: Configure with Supabase test database connection
    """
    # This will be implemented when Supabase configuration is added
    pass


@pytest.fixture
def mock_supabase():
    """
    Mock Supabase client for unit tests
    TODO: Implement mock Supabase client
    """
    pass