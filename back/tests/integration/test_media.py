"""
Integration tests for media upload functionality
Tests complete user workflows from API endpoint to database/storage state
"""

import os
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from fastapi import UploadFile
from uuid import uuid4

from ...main import app
from ...services.media_service import MediaService
from ...models.media import ALLOWED_LOGO_TYPES, DEFAULT_MAX_SIZE
from ..utils import (
    create_test_user, create_admin_jwt, create_staff_jwt,
    create_test_image, cleanup_test_files
)

class TestMediaUpload:
    """Test media upload functionality."""

    def test_upload_logo_success_admin(self, test_client: TestClient, test_merchant, admin_user):
        """Test successful logo upload by admin user."""
        # Create test image file
        image_data = create_test_image(format="PNG", size=(200, 200))
        
        # Create JWT token for admin user
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload logo
        response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert "data" in data
        
        upload_data = data["data"]
        assert "url" in upload_data
        assert "signed_url" in upload_data
        assert upload_data["filename"] == "logo.png"
        assert upload_data["content_type"] == "image/png"
        assert upload_data["size"] > 0
        assert "expires_at" in upload_data
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])

    def test_upload_logo_different_formats(self, test_client: TestClient, test_merchant, admin_user):
        """Test logo upload with different supported formats."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        formats = [
            ("PNG", "image/png", "logo.png"),
            ("JPEG", "image/jpeg", "logo.jpeg"),
            ("WEBP", "image/webp", "logo.webp")
        ]
        
        for format_name, mime_type, expected_filename in formats:
            # Create test image
            image_data = create_test_image(format=format_name, size=(150, 150))
            
            # Upload logo
            response = test_client.post(
                "/api/v1/media/logo",
                headers=headers,
                files={"file": (f"test.{format_name.lower()}", image_data, mime_type)}
            )
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["ok"] is True
            
            upload_data = data["data"]
            assert upload_data["filename"] == expected_filename
            assert upload_data["content_type"] == mime_type
            
        # Cleanup
        cleanup_test_files(test_merchant["id"])

    def test_upload_logo_staff_forbidden(self, test_client: TestClient, test_merchant, staff_user):
        """Test that staff users cannot upload logos."""
        # Create test image file
        image_data = create_test_image(format="PNG", size=(100, 100))
        
        # Create JWT token for staff user
        token = create_staff_jwt(staff_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Attempt to upload logo
        response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        
        # Verify forbidden response
        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data["detail"]

    def test_upload_logo_no_auth(self, test_client: TestClient):
        """Test logo upload without authentication."""
        # Create test image file
        image_data = create_test_image(format="PNG", size=(100, 100))
        
        # Attempt to upload without auth
        response = test_client.post(
            "/api/v1/media/logo",
            files={"file": ("logo.png", image_data, "image/png")}
        )
        
        # Verify unauthorized response
        assert response.status_code == 401

    def test_upload_logo_invalid_file_type(self, test_client: TestClient, test_merchant, admin_user):
        """Test logo upload with invalid file type."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create text file (unsupported)
        text_data = io.BytesIO(b"This is not an image")
        
        # Attempt to upload
        response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("document.txt", text_data, "text/plain")}
        )
        
        # Verify unsupported media type response
        assert response.status_code == 415
        data = response.json()
        assert "Unsupported file type" in data["detail"]

    def test_upload_logo_file_too_large(self, test_client: TestClient, test_merchant, admin_user):
        """Test logo upload with file too large."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create large file (> 5MB)
        large_data = io.BytesIO(b"x" * (6 * 1024 * 1024))  # 6MB
        
        # Attempt to upload
        response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("large.png", large_data, "image/png")}
        )
        
        # Verify payload too large response
        assert response.status_code == 413
        data = response.json()
        assert "File too large" in data["detail"]

    def test_upload_logo_no_file(self, test_client: TestClient, test_merchant, admin_user):
        """Test logo upload without file."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Attempt to upload without file
        response = test_client.post(
            "/api/v1/media/logo",
            headers=headers
        )
        
        # Verify bad request response
        assert response.status_code == 422  # FastAPI validation error

    def test_upload_logo_empty_file(self, test_client: TestClient, test_merchant, admin_user):
        """Test logo upload with empty file."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create empty file
        empty_data = io.BytesIO(b"")
        
        # Attempt to upload
        response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("empty.png", empty_data, "image/png")}
        )
        
        # Verify bad request response
        assert response.status_code == 400
        data = response.json()
        assert "Empty file not allowed" in data["detail"]

class TestSignedUrl:
    """Test signed URL generation functionality."""

    def test_get_signed_url_admin_success(self, test_client: TestClient, test_merchant, admin_user):
        """Test signed URL generation by admin user after logo upload."""
        # First upload a logo
        image_data = create_test_image(format="PNG", size=(100, 100))
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        upload_response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        assert upload_response.status_code == 201
        
        # Get signed URL
        response = test_client.get(
            "/api/v1/media/logo/signed-url",
            headers=headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        url_data = data["data"]
        assert "signed_url" in url_data
        assert "expires_at" in url_data
        assert url_data["signed_url"].startswith("http")
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])

    def test_get_signed_url_staff_success(self, test_client: TestClient, test_merchant, admin_user, staff_user):
        """Test signed URL generation by staff user."""
        # First upload a logo as admin
        image_data = create_test_image(format="PNG", size=(100, 100))
        admin_token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        upload_response = test_client.post(
            "/api/v1/media/logo",
            headers=admin_headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        assert upload_response.status_code == 201
        
        # Get signed URL as staff
        staff_token = create_staff_jwt(staff_user["id"], test_merchant["id"])
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        response = test_client.get(
            "/api/v1/media/logo/signed-url",
            headers=staff_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "signed_url" in data["data"]
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])

    def test_get_signed_url_no_logo(self, test_client: TestClient, test_merchant, admin_user):
        """Test signed URL generation when no logo exists."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get signed URL without uploading logo first
        response = test_client.get(
            "/api/v1/media/logo/signed-url",
            headers=headers
        )
        
        # Verify not found response
        assert response.status_code == 404
        data = response.json()
        assert "No logo found" in data["detail"]

    def test_get_signed_url_no_auth(self, test_client: TestClient):
        """Test signed URL generation without authentication."""
        response = test_client.get("/api/v1/media/logo/signed-url")
        
        # Verify unauthorized response
        assert response.status_code == 401

    def test_get_signed_url_custom_expiry(self, test_client: TestClient, test_merchant, admin_user):
        """Test signed URL generation with custom expiry."""
        # First upload a logo
        image_data = create_test_image(format="PNG", size=(100, 100))
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        upload_response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        assert upload_response.status_code == 201
        
        # Get signed URL with custom expiry
        response = test_client.get(
            "/api/v1/media/logo/signed-url?expiry_seconds=3600",  # 1 hour
            headers=headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "signed_url" in data["data"]
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])

class TestLogoDeletion:
    """Test logo deletion functionality."""

    def test_delete_logo_admin_success(self, test_client: TestClient, test_merchant, admin_user):
        """Test successful logo deletion by admin user."""
        # First upload a logo
        image_data = create_test_image(format="PNG", size=(100, 100))
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        upload_response = test_client.post(
            "/api/v1/media/logo",
            headers=headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        assert upload_response.status_code == 201
        
        # Delete logo
        response = test_client.delete(
            "/api/v1/media/logo",
            headers=headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "deleted successfully" in data["data"]["message"]

    def test_delete_logo_staff_forbidden(self, test_client: TestClient, test_merchant, admin_user, staff_user):
        """Test that staff users cannot delete logos."""
        # First upload a logo as admin
        image_data = create_test_image(format="PNG", size=(100, 100))
        admin_token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        upload_response = test_client.post(
            "/api/v1/media/logo",
            headers=admin_headers,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        assert upload_response.status_code == 201
        
        # Attempt to delete as staff
        staff_token = create_staff_jwt(staff_user["id"], test_merchant["id"])
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        response = test_client.delete(
            "/api/v1/media/logo",
            headers=staff_headers
        )
        
        # Verify forbidden response
        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data["detail"]
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])

    def test_delete_logo_no_logo(self, test_client: TestClient, test_merchant, admin_user):
        """Test logo deletion when no logo exists."""
        token = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Delete non-existent logo
        response = test_client.delete(
            "/api/v1/media/logo",
            headers=headers
        )
        
        # Verify not found response
        assert response.status_code == 404
        data = response.json()
        assert "No logo found to delete" in data["detail"]

    def test_delete_logo_no_auth(self, test_client: TestClient):
        """Test logo deletion without authentication."""
        response = test_client.delete("/api/v1/media/logo")
        
        # Verify unauthorized response
        assert response.status_code == 401

class TestMultiTenantIsolation:
    """Test multi-tenant isolation for media functionality."""

    def test_cross_tenant_upload_isolated(self, test_client: TestClient, test_merchant, other_merchant, admin_user, other_admin_user):
        """Test that merchants cannot access each other's media."""
        # Upload logo for first merchant
        image_data = create_test_image(format="PNG", size=(100, 100))
        token1 = create_admin_jwt(admin_user["id"], test_merchant["id"])
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        upload_response = test_client.post(
            "/api/v1/media/logo",
            headers=headers1,
            files={"file": ("logo.png", image_data, "image/png")}
        )
        assert upload_response.status_code == 201
        
        # Try to access signed URL with different merchant token
        token2 = create_admin_jwt(other_admin_user["id"], other_merchant["id"])
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response = test_client.get(
            "/api/v1/media/logo/signed-url",
            headers=headers2
        )
        
        # Verify isolation - should not find logo from other merchant
        assert response.status_code == 404
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])
        cleanup_test_files(other_merchant["id"])

class TestHealthCheck:
    """Test media service health check."""

    def test_health_check_success(self, test_client: TestClient):
        """Test media service health check."""
        response = test_client.get("/api/v1/media/health")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "data" in data
        
        health_data = data["data"]
        assert "service" in health_data
        assert "status" in health_data
        assert "checks" in health_data
        assert "timestamp" in health_data
        
        # Check individual components
        checks = health_data["checks"]
        assert "storage_bucket" in checks
        assert "database" in checks

class TestMediaService:
    """Test MediaService class directly."""

    @pytest.mark.asyncio
    async def test_upload_logo_service(self, test_db_session, test_merchant):
        """Test MediaService logo upload functionality."""
        media_service = MediaService(test_db_session)
        
        # Create mock UploadFile
        image_data = create_test_image(format="PNG", size=(100, 100))
        mock_file = UploadFile(
            filename="test.png",
            file=io.BytesIO(image_data.getvalue()),
            content_type="image/png"
        )
        
        # Upload logo
        result = await media_service.upload_logo(
            merchant_id=test_merchant["id"],
            file=mock_file,
            update_merchant_record=False  # Skip DB update for test
        )
        
        # Verify result
        assert result.filename == "logo.png"
        assert result.content_type == "image/png"
        assert result.size > 0
        assert result.url
        assert result.signed_url
        assert result.expires_at
        
        # Cleanup
        cleanup_test_files(test_merchant["id"])

    @pytest.mark.asyncio
    async def test_health_check_service(self, test_db_session):
        """Test MediaService health check."""
        media_service = MediaService(test_db_session)
        
        health_status = await media_service.health_check()
        
        # Verify health check structure
        assert "service" in health_status
        assert "status" in health_status
        assert "checks" in health_status
        assert "timestamp" in health_status
        
        assert health_status["service"] == "media_service"
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]

# Test fixtures and utilities would be imported from conftest.py or test utils