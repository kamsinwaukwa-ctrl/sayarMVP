#!/usr/bin/env python3
"""
Test script to verify the bootstrap function works correctly
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from argon2 import PasswordHasher

# Load environment first
load_dotenv()

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Create a clean engine for testing
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    sys.exit(1)

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    connect_args={
        "ssl": "prefer",
        "statement_cache_size": 0,
    },
)

ph = PasswordHasher()


async def test_bootstrap_function():
    """Test the register_merchant_and_admin function directly"""

    print("Testing bootstrap function...")

    try:
        # Test data
        test_email = "bootstrap_test@example.com"
        test_password = "testpass123"
        password_hash = ph.hash(test_password)

        print(f"Testing with email: {test_email}")

        async with engine.begin() as conn:
            # First, clean up any existing test data
            await conn.execute(
                text("DELETE FROM users WHERE email = :email"), {"email": test_email}
            )

            # Test the bootstrap function
            result = await conn.execute(
                text(
                    """
                    SELECT out_merchant_id, out_user_id
                    FROM public.register_merchant_and_admin(
                        :p_name,
                        :p_email,
                        :p_password_hash,
                        :p_business_name,
                        :p_whatsapp
                    )
                """
                ),
                {
                    "p_name": "Test User",
                    "p_email": test_email,
                    "p_password_hash": password_hash,
                    "p_business_name": "Test Business",
                    "p_whatsapp": None,
                },
            )

            row = result.fetchone()
            if row:
                merchant_id = str(row.out_merchant_id)
                user_id = str(row.out_user_id)
                print(f"✅ Success! Created merchant {merchant_id} and user {user_id}")

                # Verify the data was inserted
                merchant_check = await conn.execute(
                    text("SELECT name FROM merchants WHERE id = :id"),
                    {"id": merchant_id},
                )
                merchant_row = merchant_check.fetchone()

                user_check = await conn.execute(
                    text("SELECT name, email, role FROM users WHERE id = :id"),
                    {"id": user_id},
                )
                user_row = user_check.fetchone()

                print(f"Merchant: {merchant_row.name if merchant_row else 'Not found'}")
                print(
                    f"User: {user_row.name if user_row else 'Not found'} ({user_row.email if user_row else 'N/A'}) - {user_row.role if user_row else 'N/A'}"
                )

                return True
            else:
                print("❌ Function returned no results")
                return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return False


async def test_function_exists():
    """Check if the bootstrap function exists in the database"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT proname, pronamespace::regnamespace
                    FROM pg_proc 
                    WHERE proname = 'register_merchant_and_admin'
                """
                )
            )
            functions = result.fetchall()

            if functions:
                print("✅ Bootstrap function found:")
                for func in functions:
                    print(f"  - {func.pronamespace}.{func.proname}")
                return True
            else:
                print("❌ Bootstrap function not found in database")
                return False

    except Exception as e:
        print(f"❌ Error checking function: {e}")
        return False


async def main():
    print("🔍 Database Bootstrap Function Test")
    print("=" * 50)

    # Test database connection
    try:
        async with engine.connect() as conn:
            version = await conn.scalar(text("SELECT version()"))
            print(f"✅ Connected to database")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # Check if function exists
    print("\n1. Checking if bootstrap function exists...")
    if not await test_function_exists():
        return False

    # Test the function
    print("\n2. Testing bootstrap function...")
    success = await test_bootstrap_function()

    if success:
        print("\n✅ All tests passed! Bootstrap function is working correctly.")
    else:
        print("\n❌ Bootstrap function test failed.")

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
