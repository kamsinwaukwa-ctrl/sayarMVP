#!/usr/bin/env python3
"""
Direct SQL script to bootstrap webhook without REST API
This bypasses the API and goes straight to the database
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def bootstrap_webhook():
    """Bootstrap webhook directly via SQL using asyncpg"""

    # Configuration
    merchant_id = "9c368836-4377-4dc5-a8ab-9f94e7951e9b"
    app_id = "768489492716576"
    app_secret = "8dd4bb55a6011a411893bd04c9035f15"
    base_url = "https://api.usesayar.com"

    encryption_key = os.getenv("DATABASE_ENCRYPTION_KEY")
    if not encryption_key:
        print("❌ ERROR: DATABASE_ENCRYPTION_KEY not set in .env")
        return

    # Get database connection string for Transaction Pooler (service role needed)
    # Note: Admin functions require service_role, so we need to connect as service
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_service_key:
        print("❌ ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    # Parse Supabase URL to get connection parameters
    # Format: https://project-ref.supabase.co
    project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")

    # Use Transaction Pooler (port 6543) with service role for admin functions
    db_host = f"aws-1-eu-west-3.pooler.supabase.com"
    db_user = f"postgres.{project_ref}"
    db_password = supabase_service_key.split(".")[-1]  # Extract password from JWT-like key
    # Actually, for service role we should use the direct connection string

    # Let's use the direct connection parameters you have in .env
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "postgres")

    print("=== Direct Webhook Bootstrap ===\n")
    print(f"Merchant ID: {merchant_id}")
    print(f"App ID: {app_id}")
    print(f"Base URL: {base_url}\n")
    print("⚠️  Note: Using connection pooler - admin function requires service_role\n")

    # Connect directly with asyncpg
    conn = await asyncpg.connect(
        user=db_user,
        password=db_password,
        database=db_name,
        host=db_host,
        port=db_port,
        ssl="prefer"
    )

    try:
        # Start transaction
        await conn.execute("BEGIN")

        # Set the role to service_role to bypass RLS
        await conn.execute("SET LOCAL role = 'service_role'")

        # Set encryption key
        await conn.execute(f"SET LOCAL app.encryption_key = '{encryption_key}'")

        # Set base URL
        await conn.execute(f"SET LOCAL app.base_url = '{base_url}'")

        print("Calling admin_create_or_rotate_webhook SQL function...")

        # Call the SQL admin function
        row = await conn.fetchrow("""
            SELECT * FROM admin_create_or_rotate_webhook(
                $1::uuid,
                'whatsapp',
                $2,
                $3,
                $4,
                NULL,
                NULL,
                NULL
            )
        """, merchant_id, app_id, app_secret, base_url)

        if not row:
            print("❌ Failed: No result returned from SQL function")
            await conn.execute("ROLLBACK")
            return

        # Commit transaction
        await conn.execute("COMMIT")

        # Display results
        print("\n✅ SUCCESS! Webhook created:\n")
        print("─" * 60)
        print(f"Webhook ID:    {row['id']}")
        print(f"Callback URL:  {row['callback_url']}")
        print(f"Verify Token:  {row['verify_token']}")
        print("─" * 60)

        print("\n📋 Next Steps:")
        print("1. Go to https://developers.facebook.com/apps/")
        print(f"2. Select App ID: {app_id}")
        print("3. Navigate to: WhatsApp > Configuration")
        print("4. Click 'Edit' on the Webhook section")
        print("5. Enter:")
        print(f"   - Callback URL: {row['callback_url']}")
        print(f"   - Verify Token: {row['verify_token']}")
        print("6. Click 'Verify and Save'")
        print("7. Subscribe to webhook fields:")
        print("   ✓ messages")
        print("   ✓ message_status")

        # Verify the record was created
        print("\n🔍 Verifying webhook_endpoints table...")
        verify_row = await conn.fetchrow("""
            SELECT id, merchant_id, provider, app_id, active, created_at
            FROM webhook_endpoints
            WHERE merchant_id = $1::uuid AND app_id = $2
        """, merchant_id, app_id)

        if verify_row:
            print(f"✓ Record found in database")
            print(f"  Active: {verify_row['active']}")
            print(f"  Created: {verify_row['created_at']}")
        else:
            print("⚠️  Warning: Could not verify record in database")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        await conn.execute("ROLLBACK")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(bootstrap_webhook())