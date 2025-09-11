"""
Database connection setup for Sayar WhatsApp Commerce Platform
Uses SQLAlchemy with async support for Supabase PostgreSQL
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in environment variables")

# Debug: Print the constructed URL (without password for security)
print(f"🔍 Using DATABASE_URL: {DATABASE_URL.split('@')[0]}@***")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    poolclass=NullPool,  # Use NullPool for serverless environments
    future=True,
    connect_args={
        "ssl": "prefer",             # TLS preferred, more permissive for development
        "statement_cache_size": 0,   # Disable statement caching to avoid pgbouncer issues
    },
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base class for all models
Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Use this in FastAPI dependencies for route handlers.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Initialize database by creating all tables.
    This should be called during application startup.
    """
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully")

async def close_db():
    """
    Close database connections.
    This should be called during application shutdown.
    """
    await engine.dispose()
    print("Database connections closed")

# Test database connection
async def test_connection():
    """Test database connection"""
    try:
        async with engine.connect() as conn:
            result = await conn.scalar("SELECT version()")
            print(f"Database connection successful: {result}")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False