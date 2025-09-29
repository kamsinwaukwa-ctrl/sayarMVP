
#!/usr/bin/env python3
"""
Test script to bootstrap WhatsApp webhook for a merchant
"""
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = "https://api.usesayar.com"
# API_BASE_URL = "http://localhost:8000"  # Use this if testing locally

def get_merchant_info(token):
    """Get current merchant info"""
    response = requests.get(
        f"{API_BASE_URL}/api/v1/merchants/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting merchant info: {response.status_code}")
        print(response.text)
        return None

def bootstrap_webhook(merchant_id, app_id, app_secret):
    """Bootstrap webhook for WhatsApp"""
    payload = {
        "merchant_id": merchant_id,
        "provider": "whatsapp",
        "app_id": app_id,
        "app_secret": app_secret,
        "base_url": "https://api.usesayar.com"
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/webhooks/bootstrap",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error bootstrapping webhook: {response.status_code}")
        print(response.text)
        return None

def main():
    print("=== WhatsApp Webhook Bootstrap Test ===\n")

    # Step 1: Get your JWT token (you'll need to provide this)
    print("Step 1: Get your JWT token")
    print("You can get this by:")
    print("1. Login to your frontend (http://localhost:5173)")
    print("2. Open browser DevTools > Application > Local Storage")
    print("3. Copy the 'authToken' value\n")

    token = input("Paste your JWT token here: ").strip()

    if not token:
        print("Error: Token is required")
        return

    # Get merchant info
    print("\nFetching merchant info...")
    merchant_info = get_merchant_info(token)
    if not merchant_info:
        return

    merchant_id = merchant_info.get("id")
    print(f"✓ Merchant ID: {merchant_id}")
    print(f"✓ Business Name: {merchant_info.get('business_name')}\n")

    # Step 2: Get WhatsApp credentials
    print("Step 2: Enter WhatsApp App credentials")
    print("Get these from: https://developers.facebook.com/apps/\n")

    app_id = input("WhatsApp App ID: ").strip()
    app_secret = input("WhatsApp App Secret: ").strip()

    if not app_id or not app_secret:
        print("Error: Both App ID and App Secret are required")
        return

    # Step 3: Bootstrap webhook
    print("\nBootstrapping webhook...")
    result = bootstrap_webhook(merchant_id, app_id, app_secret)

    if result:
        print("\n✅ SUCCESS! Webhook created:\n")
        print(f"Webhook ID: {result.get('id')}")
        print(f"Callback URL: {result.get('callback_url')}")
        print(f"Verify Token: {result.get('verify_token')}")
        print("\n📋 Next steps:")
        print("1. Go to https://developers.facebook.com/apps/")
        print("2. Select your app > WhatsApp > Configuration")
        print("3. Click 'Edit' on Webhook")
        print("4. Enter the Callback URL and Verify Token above")
        print("5. Subscribe to webhook fields: messages, message_status")
    else:
        print("\n❌ Failed to create webhook")

if __name__ == "__main__":
    main()