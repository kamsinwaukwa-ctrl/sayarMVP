#!/usr/bin/env python3
"""
Simple test script to verify cloudinary library import and basic functionality
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_cloudinary_import():
    """Test if cloudinary library can be imported and configured"""
    try:
        import cloudinary
        import cloudinary.uploader

        print("✅ Cloudinary library imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import cloudinary library: {e}")
        return False


def test_cloudinary_config():
    """Test cloudinary configuration"""
    try:
        import cloudinary

        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        if not all([cloud_name, api_key, api_secret]):
            print("❌ Missing cloudinary environment variables")
            return False

        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)

        print("✅ Cloudinary configured successfully")
        print(f"   Cloud name: {cloud_name}")
        print(f"   API key: {api_key[:10]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to configure cloudinary: {e}")
        return False


def test_simple_upload():
    """Test a simple text upload to cloudinary"""
    try:
        import cloudinary
        import cloudinary.uploader

        # Configure
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)

        # Test upload with simple text content
        test_content = b"test cloudinary upload"

        response = cloudinary.uploader.upload(
            test_content,
            folder="sayar/test",
            public_id="test_upload",
            overwrite=True,
            resource_type="raw",  # Use raw for text content
        )

        print("✅ Cloudinary upload test successful")
        print(f"   Public ID: {response.get('public_id')}")
        print(f"   Secure URL: {response.get('secure_url')}")
        return True

    except Exception as e:
        print(f"❌ Cloudinary upload test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Testing Cloudinary Integration...")
    print()

    # Run tests
    import_ok = test_cloudinary_import()
    config_ok = test_cloudinary_config() if import_ok else False
    upload_ok = test_simple_upload() if config_ok else False

    print()
    print("📊 Test Results:")
    print(f"   Import: {'✅' if import_ok else '❌'}")
    print(f"   Config: {'✅' if config_ok else '❌'}")
    print(f"   Upload: {'✅' if upload_ok else '❌'}")

    if all([import_ok, config_ok, upload_ok]):
        print("\n🎉 All tests passed! Cloudinary is working correctly.")
    else:
        print("\n💥 Some tests failed. Check the errors above.")
