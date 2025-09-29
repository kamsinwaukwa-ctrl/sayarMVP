#!/usr/bin/env python3
"""
Simple SQL script to bootstrap webhook by directly inserting into the table
This bypasses the admin function and RLS
"""
import asyncio
import os
import asyncpg
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def bootstrap_webhook():
    """Bootstrap webhook directly via SQL INSERT"""

    # Configuration
    merchant_id = "9c368836-4377-4dc5-a8ab-9f94e7951e9b"
    app_id = "768489492716576"
    app_secret = "8dd4bb55a6011a411893bd04c9035f15"
    base_url = "https://api.usesayar.com"

    encryption_key = os.getenv("DATABASE_ENCRYPTION_KEY")
    if not encryption_key:
        print("❌ ERROR: DATABASE_ENCRYPTION_KEY not set in .env")
        return

    # Database connection parameters
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "postgres")

    print("=== Simple Webhook Bootstrap (Direct INSERT) ===\n")
    print(f"Merchant ID: {merchant_id}")
    print(f"App ID: {app_id}")
    print(f"Base URL: {base_url}\n")

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

        # Temporarily disable RLS for this session (as postgres user)
        await conn.execute("SET LOCAL session_replication_role = replica")

        # Set encryption key
        await conn.execute(f"SET LOCAL app.encryption_key = '{encryption_key}'")

        # Generate verify token (32 bytes = ~43 base64 chars)
        verify_token_raw = secrets.token_urlsafe(32)

        # Build callback path and URL
        callback_path = f"/api/webhooks/whatsapp/app/{app_id}"
        callback_url = f"{base_url.rstrip('/')}{callback_path}"

        print(f"Generated verify token: {verify_token_raw}")
        print(f"Callback URL: {callback_url}\n")

        # Check if record already exists
        existing = await conn.fetchrow("""
            SELECT id FROM webhook_endpoints
            WHERE merchant_id = $1::uuid AND app_id = $2
        """, merchant_id, app_id)

        if existing:
            print(f"⚠️  Webhook already exists (ID: {existing['id']}). Updating...")

            # Update existing record
            await conn.execute("""
                UPDATE webhook_endpoints
                SET app_secret_encrypted = pgp_sym_encrypt($1, current_setting('app.encryption_key')),
                    verify_token_hash = crypt($2, gen_salt('bf')),
                    callback_path = $3,
                    active = TRUE,
                    updated_at = NOW()
                WHERE merchant_id = $4::uuid AND app_id = $5
            """, app_secret, verify_token_raw, callback_path, merchant_id, app_id)

            webhook_id = existing['id']
        else:
            print("Creating new webhook record...")

            # Insert new record
            result = await conn.fetchrow("""
                INSERT INTO webhook_endpoints (
                    merchant_id, provider, app_id,
                    app_secret_encrypted, verify_token_hash,
                    callback_path, active
                )
                VALUES (
                    $1::uuid, 'whatsapp', $2,
                    pgp_sym_encrypt($3, current_setting('app.encryption_key')),
                    crypt($4, gen_salt('bf')),
                    $5, TRUE
                )
                RETURNING id
            """, merchant_id, app_id, app_secret, verify_token_raw, callback_path)

            webhook_id = result['id']

        # Commit transaction
        await conn.execute("COMMIT")

        # Display results
        print("\n✅ SUCCESS! Webhook created:\n")
        print("─" * 70)
        print(f"Webhook ID:    {webhook_id}")
        print(f"Callback URL:  {callback_url}")
        print(f"Verify Token:  {verify_token_raw}")
        print("─" * 70)

        print("\n📋 Next Steps:")
        print("1. Go to https://developers.facebook.com/apps/")
        print(f"2. Select App ID: {app_id}")
        print("3. Navigate to: WhatsApp > Configuration")
        print("4. Click 'Edit' on the Webhook section")
        print("5. Enter:")
        print(f"   - Callback URL: {callback_url}")
        print(f"   - Verify Token: {verify_token_raw}")
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
        try:
            await conn.execute("ROLLBACK")
        except:
            pass
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(bootstrap_webhook())