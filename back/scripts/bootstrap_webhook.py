#!/usr/bin/env python3
"""
Bootstrap script to set up WhatsApp webhook endpoints for merchants
This is an admin-only tool to configure webhook URLs and generate verify tokens
"""

import asyncio
import os
import sys
import secrets
import string
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import required modules
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker
from src.models.sqlalchemy_models import WebhookEndpoint
from src.utils.encryption import get_encryption_service


def generate_verify_token(prefix: Optional[str] = None) -> str:
    """Generate a strong random verify token"""
    # Generate 32 character random token
    alphabet = string.ascii_letters + string.digits + "-_"
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))

    if prefix:
        # Clean the prefix to be URL-safe
        clean_prefix = ''.join(c for c in prefix if c.isalnum() or c in '-_')[:10]
        return f"{clean_prefix}_{random_part}"
    return random_part


def hash_verify_token(token: str) -> str:
    """Hash the verify token using bcrypt"""
    return bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def construct_callback_path(app_id: str) -> str:
    """Construct the webhook callback path"""
    return f"/api/webhooks/whatsapp/app/{app_id}"


async def setup_webhook(
    merchant_id: str,
    app_id: str,
    app_secret: str,
    phone_number_id: Optional[str] = None,
    waba_id: Optional[str] = None,
    whatsapp_phone: Optional[str] = None,
    merchant_slug: Optional[str] = None,
) -> tuple[str, str]:
    """
    Set up webhook endpoint for a merchant
    Returns (webhook_url, verify_token)
    """
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if webhook already exists for this app_id
        result = await session.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.app_id == app_id)
        )
        existing_webhook = result.scalar_one_or_none()

        if existing_webhook:
            print(f"\n⚠️  Webhook already exists for app_id: {app_id}")
            print(f"   Merchant ID: {existing_webhook.merchant_id}")
            print(f"   Created at: {existing_webhook.created_at}")

            response = input("\nDo you want to regenerate the verify token? (y/N): ")
            if response.lower() != 'y':
                print("❌ Operation cancelled")
                return None, None

        # Generate verify token
        verify_token = generate_verify_token(prefix=merchant_slug)
        verify_token_hash = hash_verify_token(verify_token)

        # Encrypt app secret
        encryption_service = get_encryption_service()
        encrypted_secret = encryption_service.encrypt_data(app_secret)

        # Construct callback path
        callback_path = construct_callback_path(app_id)

        if existing_webhook:
            # Update existing webhook
            await session.execute(
                update(WebhookEndpoint)
                .where(WebhookEndpoint.app_id == app_id)
                .values(
                    app_secret_encrypted=encrypted_secret.encrypted_data,
                    verify_token_hash=verify_token_hash,
                    phone_number_id=phone_number_id,
                    waba_id=waba_id,
                    whatsapp_phone_e164=whatsapp_phone,
                    callback_path=callback_path,
                    updated_at=datetime.now(timezone.utc),
                    active=True,
                )
            )
        else:
            # Create new webhook endpoint
            webhook = WebhookEndpoint(
                merchant_id=merchant_id,
                provider="whatsapp",
                app_id=app_id,
                app_secret_encrypted=encrypted_secret.encrypted_data,
                verify_token_hash=verify_token_hash,
                phone_number_id=phone_number_id,
                waba_id=waba_id,
                whatsapp_phone_e164=whatsapp_phone,
                callback_path=callback_path,
                active=True,
            )
            session.add(webhook)

        await session.commit()

    # Get Railway URL or fallback to localhost
    railway_url = os.getenv("RAILWAY_STATIC_URL", "http://localhost:8000")
    if not railway_url.startswith("http"):
        railway_url = f"https://{railway_url}"

    webhook_url = f"{railway_url}{callback_path}"

    return webhook_url, verify_token


async def main():
    """Main entry point for the bootstrap script"""
    parser = argparse.ArgumentParser(
        description="Bootstrap WhatsApp webhook endpoint for a merchant"
    )
    parser.add_argument("merchant_id", help="Merchant ID (UUID)")
    parser.add_argument("app_id", help="Meta App ID")
    parser.add_argument("app_secret", help="Meta App Secret")
    parser.add_argument("--phone-number-id", help="WhatsApp Phone Number ID (optional)")
    parser.add_argument("--waba-id", help="WhatsApp Business Account ID (optional)")
    parser.add_argument("--phone", help="WhatsApp phone number in E.164 format (optional)")
    parser.add_argument("--slug", help="Merchant slug for verify token prefix (optional)")

    args = parser.parse_args()

    print("\n🚀 WhatsApp Webhook Bootstrap Script")
    print("=" * 50)
    print(f"Merchant ID: {args.merchant_id}")
    print(f"App ID: {args.app_id}")
    print(f"Phone Number ID: {args.phone_number_id or 'Not provided'}")
    print(f"WABA ID: {args.waba_id or 'Not provided'}")
    print(f"Phone: {args.phone or 'Not provided'}")
    print("=" * 50)

    try:
        webhook_url, verify_token = await setup_webhook(
            merchant_id=args.merchant_id,
            app_id=args.app_id,
            app_secret=args.app_secret,
            phone_number_id=args.phone_number_id,
            waba_id=args.waba_id,
            whatsapp_phone=args.phone,
            merchant_slug=args.slug,
        )

        if webhook_url and verify_token:
            print("\n✅ Webhook endpoint created successfully!")
            print("\n" + "=" * 70)
            print("📋 COPY THESE VALUES TO META DEVELOPER CONSOLE")
            print("=" * 70)
            print(f"\n🔗 Callback URL:")
            print(f"   {webhook_url}")
            print(f"\n🔑 Verify Token (SAVE THIS - YOU WON'T SEE IT AGAIN):")
            print(f"   {verify_token}")
            print("\n" + "=" * 70)
            print("\n📝 Instructions:")
            print("1. Go to Meta Developer Console → Your App → WhatsApp → Configuration")
            print("2. Click 'Edit' on Webhook")
            print("3. Paste the Callback URL above")
            print("4. Paste the Verify Token above")
            print("5. Subscribe to: messages, message_status, message_template_status_update")
            print("6. Click 'Verify and Save'")
            print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())