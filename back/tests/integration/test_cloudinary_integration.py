"""
Integration tests for Cloudinary image management
Tests platform credentials, upload/delete operations, webhook processing, and catalog sync
"""

import pytest
import uuid
import json
import os
import hashlib
import hmac
import time
from datetime import datetime
from io import BytesIO
from PIL import Image
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.models.sqlalchemy_models import ProductImage, Product, Merchant
from src.services.cloudinary_service import CloudinaryService
from src.integrations.cloudinary_client import CloudinaryClient, CloudinaryConfig
from src.models.errors import APIError, ErrorCode


class TestCloudinaryConfig:
    """Test Cloudinary configuration and environment variable handling"""

    def test_config_with_all_env_vars(self, monkeypatch):
        """Test config when all required environment variables are set"""
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")

        config = CloudinaryConfig()
        assert config.is_configured() is True
        assert config.cloud_name == "test-cloud"
        assert config.api_key == "test-key"
        assert config.api_secret == "test-secret"

    def test_config_missing_env_vars(self, monkeypatch):
        """Test config when required environment variables are missing"""
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)

        config = CloudinaryConfig()
        assert config.is_configured() is False

    def test_config_optional_env_vars(self, monkeypatch):
        """Test config with optional environment variables"""
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")
        monkeypatch.setenv("CLOUDINARY_UPLOAD_TIMEOUT", "60")
        monkeypatch.setenv("MAX_IMAGE_SIZE_MB", "10")
        monkeypatch.setenv("SUPPORTED_IMAGE_FORMATS", "png,jpg,webp")

        config = CloudinaryConfig()
        assert config.upload_timeout == 60
        assert config.max_image_size_mb == 10
        assert config.supported_formats == ["png", "jpg", "webp"]


class TestCloudinaryClient:
    """Test Cloudinary client operations"""

    @pytest.fixture
    def configured_client(self, monkeypatch):
        """Create a configured Cloudinary client for testing"""
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")
        return CloudinaryClient()

    def test_client_initialization_fails_without_config(self, monkeypatch):
        """Test that client initialization fails when environment is not configured"""
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)

        with pytest.raises(APIError) as exc_info:
            CloudinaryClient()

        assert exc_info.value.code == ErrorCode.CLOUDINARY_NOT_CONFIGURED

    @patch('requests.get')
    def test_health_check_success(self, mock_get, configured_client):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"credits": 1000}
        mock_get.return_value = mock_response

        result = configured_client.verify_health()

        assert result["configured"] is True
        assert result["cloud_name"] == "test-cloud"
        assert "verified_at" in result
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_health_check_failure(self, mock_get, configured_client):
        """Test health check failure"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            configured_client.verify_health()

        assert exc_info.value.code == ErrorCode.CLOUDINARY_HEALTHCHECK_FAILED

    def test_validate_image_file_success(self, configured_client):
        """Test successful image file validation"""
        # Create a test image
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_content = img_bytes.getvalue()

        width, height, format_name = configured_client.validate_image_file(
            img_content, "test.jpg"
        )

        assert width == 800
        assert height == 600
        assert format_name == "jpeg"

    def test_validate_image_file_too_large(self, configured_client, monkeypatch):
        """Test image file validation with oversized file"""
        monkeypatch.setenv("MAX_IMAGE_SIZE_MB", "1")
        # Reinitialize client to pick up new config
        configured_client.config = CloudinaryConfig()

        # Create a large image (simulate by creating large content)
        large_content = b'fake_image_data' * 100000  # ~1.4MB

        with pytest.raises(APIError) as exc_info:
            configured_client.validate_image_file(large_content, "large.jpg")

        assert exc_info.value.code == ErrorCode.IMAGE_TOO_LARGE

    def test_validate_image_file_too_small(self, configured_client):
        """Test image file validation with undersized image"""
        # Create a small image (below 500px minimum)
        img = Image.new('RGB', (400, 300), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_content = img_bytes.getvalue()

        with pytest.raises(APIError) as exc_info:
            configured_client.validate_image_file(img_content, "small.jpg")

        assert exc_info.value.code == ErrorCode.IMAGE_DIMENSIONS_TOO_SMALL

    def test_validate_image_file_unsupported_format(self, configured_client):
        """Test image file validation with unsupported format"""
        # Create invalid image content
        invalid_content = b"not_an_image"

        with pytest.raises(APIError) as exc_info:
            configured_client.validate_image_file(invalid_content, "test.txt")

        assert exc_info.value.code == ErrorCode.UNSUPPORTED_IMAGE_TYPE

    @patch('requests.post')
    def test_upload_image_success(self, mock_post, configured_client):
        """Test successful image upload"""
        # Mock Cloudinary upload response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "public_id": "sayar/products/merchant_id/image_123",
            "secure_url": "https://res.cloudinary.com/cloud/image/upload/v123/test.jpg",
            "width": 800,
            "height": 600,
            "format": "jpg",
            "bytes": 50000,
            "version": 1234567890,
            "eager": [
                {
                    "transformation": "c_limit,w_1600,h_1600,f_auto,q_auto:good",
                    "secure_url": "https://res.cloudinary.com/cloud/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v123/test.jpg"
                },
                {
                    "transformation": "c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco",
                    "secure_url": "https://res.cloudinary.com/cloud/image/upload/c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco/v123/test.jpg"
                }
            ]
        }
        mock_post.return_value = mock_response

        # Create test image content
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_content = img_bytes.getvalue()

        result = configured_client.upload_image(
            file_content=img_content,
            merchant_id="merchant_123",
            product_id="product_456",
            filename="test.jpg"
        )

        assert result["public_id"].startswith("sayar/products/merchant_123/")
        assert "secure_url" in result
        assert "thumbnail_url" in result
        assert result["width"] == 800
        assert result["height"] == 600
        mock_post.assert_called_once()

    def test_webhook_signature_verification(self, configured_client):
        """Test webhook signature verification"""
        payload = b'{"test": "data"}'
        timestamp = str(int(time.time()))

        # Create valid signature
        signature_data = payload + b"test-secret"
        valid_signature = hashlib.sha1(signature_data).hexdigest()

        # Test valid signature
        assert configured_client.verify_webhook_signature(
            payload, valid_signature, timestamp
        ) is True

        # Test invalid signature
        assert configured_client.verify_webhook_signature(
            payload, "invalid_signature", timestamp
        ) is False

        # Test expired timestamp
        old_timestamp = str(int(time.time()) - 400)  # 6+ minutes ago
        assert configured_client.verify_webhook_signature(
            payload, valid_signature, old_timestamp
        ) is False


class TestCloudinaryService:
    """Test CloudinaryService business logic"""

    @pytest.fixture
    def service(self, db_session):
        """Create CloudinaryService instance for testing"""
        return CloudinaryService(db_session)

    @pytest.fixture
    def test_merchant(self, db_session):
        """Create test merchant"""
        merchant = Merchant(
            id=uuid.uuid4(),
            name="Test Merchant",
            currency="NGN"
        )
        db_session.add(merchant)
        db_session.commit()
        return merchant

    @pytest.fixture
    def test_product(self, db_session, test_merchant):
        """Create test product"""
        product = Product(
            id=uuid.uuid4(),
            merchant_id=test_merchant.id,
            title="Test Product",
            price_kobo=10000,
            stock=100,
            retailer_id=f"test_merchant_{uuid.uuid4().hex[:8]}_prod_{uuid.uuid4().hex[:8]}"
        )
        db_session.add(product)
        db_session.commit()
        return product

    @patch.object(CloudinaryClient, 'verify_health')
    def test_health_check_configured(self, mock_health, service):
        """Test health check when Cloudinary is configured"""
        mock_health.return_value = {
            "configured": True,
            "cloud_name": "test-cloud",
            "verified_at": time.time()
        }

        result = service.health_check()

        assert result["configured"] is True
        assert result["cloud_name"] == "test-cloud"
        assert isinstance(result["verified_at"], datetime)

    @patch.object(CloudinaryClient, 'verify_health')
    def test_health_check_not_configured(self, mock_health, service):
        """Test health check when Cloudinary is not configured"""
        mock_health.side_effect = APIError(
            code=ErrorCode.CLOUDINARY_NOT_CONFIGURED,
            message="Not configured"
        )

        result = service.health_check()

        assert result["configured"] is False
        assert result["cloud_name"] is None
        assert result["verified_at"] is None

    @patch.object(CloudinaryClient, 'upload_image')
    def test_upload_product_image_success(self, mock_upload, service, test_product):
        """Test successful product image upload"""
        mock_upload.return_value = {
            "public_id": "sayar/products/merchant_id/image_123",
            "secure_url": "https://example.com/main.jpg",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "width": 800,
            "height": 600,
            "format": "jpg",
            "bytes": 50000,
            "version": 1234567890
        }

        # Create test image content
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_content = img_bytes.getvalue()

        result = service.upload_product_image(
            product_id=test_product.id,
            merchant_id=test_product.merchant_id,
            file_content=img_content,
            filename="test.jpg",
            is_primary=True,
            alt_text="Test image"
        )

        assert isinstance(result.id, uuid.UUID)
        assert result.product_id == test_product.id
        assert result.is_primary is True
        assert result.alt_text == "Test image"
        assert result.upload_status == "uploading"

        # Check database record was created
        image = service.db.query(ProductImage).filter(
            ProductImage.id == result.id
        ).first()
        assert image is not None
        assert image.is_primary is True

    def test_upload_product_image_product_not_found(self, service, test_merchant):
        """Test upload with non-existent product"""
        fake_product_id = uuid.uuid4()
        img_content = b"fake_image_content"

        with pytest.raises(Exception):  # Should raise NotFoundError
            service.upload_product_image(
                product_id=fake_product_id,
                merchant_id=test_merchant.id,
                file_content=img_content,
                filename="test.jpg"
            )

    @patch.object(CloudinaryClient, 'delete_image')
    def test_delete_product_image_success(self, mock_delete, service, test_product):
        """Test successful product image deletion"""
        # Create a product image first
        image = ProductImage(
            id=uuid.uuid4(),
            product_id=test_product.id,
            merchant_id=test_product.merchant_id,
            cloudinary_public_id="test_public_id",
            secure_url="https://example.com/test.jpg",
            is_primary=True,
            upload_status="completed"
        )
        service.db.add(image)
        service.db.commit()

        mock_delete.return_value = True

        result = service.delete_product_image(
            image_id=image.id,
            merchant_id=test_product.merchant_id
        )

        assert result is True

        # Check image was deleted from database
        deleted_image = service.db.query(ProductImage).filter(
            ProductImage.id == image.id
        ).first()
        assert deleted_image is None

    def test_process_webhook_upload_notification(self, service, test_product):
        """Test processing of upload webhook notification"""
        # Create a product image in uploading state
        image = ProductImage(
            id=uuid.uuid4(),
            product_id=test_product.id,
            merchant_id=test_product.merchant_id,
            cloudinary_public_id="test_public_id",
            secure_url="https://example.com/temp.jpg",
            upload_status="uploading"
        )
        service.db.add(image)
        service.db.commit()

        # Mock webhook payload
        from src.models.api import CloudinaryWebhookPayload
        payload = CloudinaryWebhookPayload(
            notification_type="upload",
            timestamp=int(time.time()),
            public_id="test_public_id",
            version=1234567890,
            width=800,
            height=600,
            format="jpg",
            resource_type="image",
            bytes=50000,
            url="http://example.com/test.jpg",
            secure_url="https://example.com/test.jpg",
            eager=[
                {
                    "transformation": "c_limit,w_1600,h_1600,f_auto,q_auto:good",
                    "secure_url": "https://example.com/main.jpg"
                },
                {
                    "transformation": "c_fill,w_600,h_600,g_auto,f_auto:eco",
                    "secure_url": "https://example.com/thumb.jpg"
                }
            ]
        )

        # Create valid webhook signature
        body = json.dumps(payload.dict()).encode()
        timestamp = str(int(time.time()))
        signature_data = body + b"test-secret"
        signature = hashlib.sha1(signature_data).hexdigest()

        with patch.object(service.cloudinary_client, 'verify_webhook_signature', return_value=True):
            result = service.process_webhook(
                payload=payload,
                signature=signature,
                timestamp=timestamp,
                raw_body=body
            )

        assert result["success"] is True

        # Check that image was updated
        updated_image = service.db.query(ProductImage).filter(
            ProductImage.id == image.id
        ).first()
        assert updated_image.upload_status == "completed"
        assert updated_image.width == 800
        assert updated_image.height == 600
        assert updated_image.secure_url == "https://example.com/main.jpg"
        assert updated_image.thumbnail_url == "https://example.com/thumb.jpg"


class TestCloudinaryAPI:
    """Test API endpoints for Cloudinary operations"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Create authorization headers for testing"""
        # This would need to be implemented based on your auth system
        return {"Authorization": "Bearer test_token"}

    def test_health_check_endpoint_success(self, client, auth_headers):
        """Test successful health check endpoint"""
        with patch('src.services.cloudinary_service.CloudinaryService.health_check') as mock_health:
            mock_health.return_value = {
                "configured": True,
                "cloud_name": "test-cloud",
                "verified_at": datetime.now()
            }

            response = client.get(
                "/api/v1/integrations/cloudinary/health",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["configured"] is True

    def test_health_check_endpoint_not_configured(self, client, auth_headers):
        """Test health check endpoint when not configured"""
        with patch('src.services.cloudinary_service.CloudinaryService.health_check') as mock_health:
            mock_health.return_value = {
                "configured": False,
                "cloud_name": None,
                "verified_at": None
            }

            response = client.get(
                "/api/v1/integrations/cloudinary/health",
                headers=auth_headers
            )

            assert response.status_code == 503

    def test_upload_image_endpoint_success(self, client, auth_headers):
        """Test successful image upload endpoint"""
        # Create test image file
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_content = img_bytes.getvalue()

        with patch('src.services.cloudinary_service.CloudinaryService.upload_product_image') as mock_upload:
            from src.models.api import ProductImageResponse
            mock_upload.return_value = ProductImageResponse(
                id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                cloudinary_public_id="test_public_id",
                secure_url="https://example.com/test.jpg",
                thumbnail_url="https://example.com/thumb.jpg",
                width=800,
                height=600,
                format="jpg",
                bytes=50000,
                is_primary=True,
                alt_text="Test image",
                upload_status="uploading",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            product_id = str(uuid.uuid4())
            response = client.post(
                f"/api/v1/products/{product_id}/images",
                headers=auth_headers,
                files={"image": ("test.jpg", img_content, "image/jpeg")},
                data={"is_primary": "true", "alt_text": "Test image"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["is_primary"] is True

    def test_webhook_endpoint_success(self, client):
        """Test successful webhook endpoint"""
        payload = {
            "notification_type": "upload",
            "timestamp": int(time.time()),
            "public_id": "test_public_id",
            "version": 1234567890,
            "width": 800,
            "height": 600,
            "format": "jpg",
            "resource_type": "image",
            "bytes": 50000,
            "url": "http://example.com/test.jpg",
            "secure_url": "https://example.com/test.jpg",
            "eager": []
        }

        body = json.dumps(payload).encode()
        timestamp = str(int(time.time()))
        signature_data = body + b"test-secret"
        signature = hashlib.sha1(signature_data).hexdigest()

        with patch('src.services.cloudinary_service.CloudinaryService.process_webhook') as mock_webhook:
            mock_webhook.return_value = {"success": True, "message": "Processed"}

            response = client.post(
                "/api/v1/webhooks/cloudinary",
                headers={
                    "X-Cld-Signature": signature,
                    "X-Cld-Timestamp": timestamp,
                    "Content-Type": "application/json"
                },
                content=body
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_webhook_endpoint_invalid_signature(self, client):
        """Test webhook endpoint with invalid signature"""
        payload = {"test": "data"}
        body = json.dumps(payload).encode()
        timestamp = str(int(time.time()))

        response = client.post(
            "/api/v1/webhooks/cloudinary",
            headers={
                "X-Cld-Signature": "invalid_signature",
                "X-Cld-Timestamp": timestamp,
                "Content-Type": "application/json"
            },
            content=body
        )

        assert response.status_code == 422


class TestCloudinaryIntegrationFlow:
    """Test complete integration flows"""

    @pytest.fixture
    def setup_test_environment(self, db_session, monkeypatch):
        """Set up complete test environment"""
        # Configure environment
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")

        # Create test merchant and product
        merchant = Merchant(
            id=uuid.uuid4(),
            name="Test Merchant",
            currency="NGN"
        )
        db_session.add(merchant)

        product = Product(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            title="Test Product",
            price_kobo=10000,
            stock=100,
            retailer_id=f"test_merchant_{uuid.uuid4().hex[:8]}_prod_{uuid.uuid4().hex[:8]}"
        )
        db_session.add(product)
        db_session.commit()

        return {
            "merchant": merchant,
            "product": product,
            "service": CloudinaryService(db_session)
        }

    def test_complete_image_upload_flow(self, setup_test_environment):
        """Test complete image upload and processing flow"""
        env = setup_test_environment
        service = env["service"]
        product = env["product"]
        merchant = env["merchant"]

        # Create test image
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_content = img_bytes.getvalue()

        # Mock Cloudinary operations
        with patch.object(service.cloudinary_client, 'upload_image') as mock_upload, \
             patch.object(service.cloudinary_client, 'verify_webhook_signature', return_value=True):

            mock_upload.return_value = {
                "public_id": "sayar/products/merchant_id/image_123",
                "secure_url": "https://example.com/main.jpg",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "width": 800,
                "height": 600,
                "format": "jpg",
                "bytes": 50000,
                "version": 1234567890
            }

            # 1. Upload image
            upload_result = service.upload_product_image(
                product_id=product.id,
                merchant_id=merchant.id,
                file_content=img_content,
                filename="test.jpg",
                is_primary=True,
                alt_text="Test image"
            )

            assert upload_result.upload_status == "uploading"
            assert upload_result.is_primary is True

            # 2. Process webhook to complete upload
            from src.models.api import CloudinaryWebhookPayload
            webhook_payload = CloudinaryWebhookPayload(
                notification_type="upload",
                timestamp=int(time.time()),
                public_id="sayar/products/merchant_id/image_123",
                version=1234567890,
                width=800,
                height=600,
                format="jpg",
                resource_type="image",
                bytes=50000,
                url="http://example.com/test.jpg",
                secure_url="https://example.com/test.jpg",
                eager=[
                    {
                        "transformation": "c_limit,w_1600,h_1600,f_auto,q_auto:good",
                        "secure_url": "https://example.com/main.jpg"
                    },
                    {
                        "transformation": "c_fill,w_600,h_600,g_auto,f_auto:eco",
                        "secure_url": "https://example.com/thumb.jpg"
                    }
                ]
            )

            webhook_result = service.process_webhook(
                payload=webhook_payload,
                signature="valid_signature",
                timestamp=str(int(time.time())),
                raw_body=b"test_body"
            )

            assert webhook_result["success"] is True

            # 3. Verify final state
            final_image = service.db.query(ProductImage).filter(
                ProductImage.id == upload_result.id
            ).first()

            assert final_image.upload_status == "completed"
            assert final_image.width == 800
            assert final_image.height == 600
            assert final_image.secure_url == "https://example.com/main.jpg"
            assert final_image.thumbnail_url == "https://example.com/thumb.jpg"

    def test_primary_image_switching_flow(self, setup_test_environment):
        """Test switching primary images and catalog sync triggers"""
        env = setup_test_environment
        service = env["service"]
        product = env["product"]
        merchant = env["merchant"]

        # Create two images
        image1 = ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            merchant_id=merchant.id,
            cloudinary_public_id="image_1",
            secure_url="https://example.com/image1.jpg",
            is_primary=True,
            upload_status="completed"
        )

        image2 = ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            merchant_id=merchant.id,
            cloudinary_public_id="image_2",
            secure_url="https://example.com/image2.jpg",
            is_primary=False,
            upload_status="completed"
        )

        service.db.add_all([image1, image2])
        service.db.commit()

        # Switch primary image
        result = service.set_primary_image(
            image_id=image2.id,
            product_id=product.id,
            merchant_id=merchant.id
        )

        assert result.is_primary is True
        assert result.catalog_sync_triggered is True

        # Verify database state
        updated_image1 = service.db.query(ProductImage).filter(
            ProductImage.id == image1.id
        ).first()
        updated_image2 = service.db.query(ProductImage).filter(
            ProductImage.id == image2.id
        ).first()

        assert updated_image1.is_primary is False
        assert updated_image2.is_primary is True

        # Verify product primary_image_id was updated
        updated_product = service.db.query(Product).filter(
            Product.id == product.id
        ).first()
        assert updated_product.primary_image_id == image2.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])