"""
Integration tests for Cloudinary preset transformations and management
Tests preset configurations, variant generation, statistics tracking, and admin API endpoints
"""

import pytest
import uuid
import json
import time
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.models.sqlalchemy_models import ProductImage, Product, Merchant
from src.services.cloudinary_service import CloudinaryService
from src.integrations.cloudinary_client import CloudinaryClient
from src.models.cloudinary import (
    PresetProfile,
    PresetTestRequest,
    UploadWithPresetsRequest,
    ImageVariant,
    ImageDimensions,
)
from src.config.cloudinary_presets import (
    STANDARD_PRESETS,
    PRESET_PROFILES,
    get_preset_by_id,
    get_profile_by_id,
    get_eager_presets_for_profile,
    get_all_presets_for_profile,
    validate_preset_configuration,
)
from src.models.errors import APIError, ErrorCode


class TestPresetConfiguration:
    """Test preset configuration and validation"""

    def test_all_presets_exist(self):
        """Test that all expected presets are defined"""
        expected_presets = [
            "main_catalog",
            "dashboard_thumb",
            "mobile_optimized",
            "product_list",
            "detailed_view",
        ]

        for preset_id in expected_presets:
            assert preset_id in STANDARD_PRESETS
            preset = STANDARD_PRESETS[preset_id]
            assert preset.id == preset_id
            assert len(preset.name) > 0
            assert len(preset.transformation) > 0

    def test_all_profiles_exist(self):
        """Test that all expected profiles are defined"""
        expected_profiles = [
            PresetProfile.STANDARD,
            PresetProfile.PREMIUM,
            PresetProfile.MOBILE_FIRST,
            PresetProfile.CATALOG_FOCUS,
        ]

        for profile_id in expected_profiles:
            assert profile_id in PRESET_PROFILES
            profile = PRESET_PROFILES[profile_id]
            assert profile.profile_id == profile_id
            assert len(profile.name) > 0
            assert len(profile.presets) > 0

    def test_preset_transformation_syntax(self):
        """Test that all preset transformations have valid syntax"""
        for preset_id, preset in STANDARD_PRESETS.items():
            transformation = preset.transformation

            # Check required components
            assert "c_" in transformation  # Crop mode
            assert "f_auto" in transformation  # Format auto
            assert "q_auto" in transformation  # Quality auto
            assert ("w_" in transformation) or (
                "h_" in transformation
            )  # Width or height

    def test_preset_configuration_validation(self):
        """Test preset configuration validation function"""
        assert validate_preset_configuration() is True

    def test_profile_preset_references(self):
        """Test that all profile preset references are valid"""
        for profile_id, profile in PRESET_PROFILES.items():
            for variant_name, preset_id in profile.presets.items():
                assert (
                    preset_id in STANDARD_PRESETS
                ), f"Profile {profile_id} references unknown preset {preset_id}"

            for variant_name in profile.default_eager_variants:
                assert (
                    variant_name in profile.presets
                ), f"Profile {profile_id} has invalid eager variant {variant_name}"

    def test_get_preset_functions(self):
        """Test preset helper functions"""
        # Test get_preset_by_id
        preset = get_preset_by_id("main_catalog")
        assert preset.id == "main_catalog"

        with pytest.raises(ValueError):
            get_preset_by_id("nonexistent_preset")

        # Test get_profile_by_id
        profile = get_profile_by_id(PresetProfile.STANDARD)
        assert profile.profile_id == PresetProfile.STANDARD

        # Test get_eager_presets_for_profile
        eager_presets = get_eager_presets_for_profile(PresetProfile.STANDARD)
        assert "main" in eager_presets
        assert "thumb" in eager_presets

        # Test get_all_presets_for_profile
        all_presets = get_all_presets_for_profile(PresetProfile.STANDARD)
        assert len(all_presets) >= 4  # main, thumb, mobile, list


class TestCloudinaryClientWithPresets:
    """Test CloudinaryClient preset functionality"""

    @pytest.fixture
    def configured_client(self, monkeypatch):
        """Create a configured Cloudinary client for testing"""
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")
        return CloudinaryClient()

    @patch("requests.post")
    def test_upload_image_with_presets_standard(self, mock_post, configured_client):
        """Test upload with standard preset profile"""
        # Mock Cloudinary upload response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "public_id": "sayar/products/merchant_id/image_123",
            "secure_url": "https://res.cloudinary.com/cloud/image/upload/v123/test.jpg",
            "width": 1200,
            "height": 800,
            "format": "jpg",
            "bytes": 80000,
            "version": 1234567890,
            "eager": [
                {
                    "transformation": "c_limit,w_1600,h_1600,f_auto,q_auto:good",
                    "secure_url": "https://res.cloudinary.com/cloud/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v123/test.jpg",
                    "width": 1200,
                    "height": 800,
                    "bytes": 75000,
                },
                {
                    "transformation": "c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco",
                    "secure_url": "https://res.cloudinary.com/cloud/image/upload/c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco/v123/test.jpg",
                    "width": 600,
                    "height": 600,
                    "bytes": 45000,
                },
            ],
        }
        mock_post.return_value = mock_response

        # Create test image content
        img = Image.new("RGB", (1200, 800), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        img_content = img_bytes.getvalue()

        result = configured_client.upload_image_with_presets(
            file_content=img_content,
            merchant_id="merchant_123",
            product_id="product_456",
            filename="test.jpg",
            preset_profile=PresetProfile.STANDARD,
        )

        assert result["public_id"].startswith("sayar/products/merchant_123/")
        assert "variants" in result

        variants = result["variants"]
        assert "main" in variants
        assert "thumb" in variants
        assert "mobile" in variants
        assert "list" in variants

        # Check eager variants have full data
        main_variant = variants["main"]
        assert main_variant.url is not None
        assert main_variant.preset_id == "main_catalog"
        assert main_variant.file_size_kb == 73  # 75000 bytes / 1024
        assert main_variant.dimensions.width == 1200
        assert main_variant.dimensions.height == 800

        thumb_variant = variants["thumb"]
        assert thumb_variant.url is not None
        assert thumb_variant.preset_id == "dashboard_thumb"
        assert thumb_variant.file_size_kb == 43  # 45000 bytes / 1024
        assert thumb_variant.dimensions.width == 600
        assert thumb_variant.dimensions.height == 600

        # Check on-demand variants have URLs but no size data
        mobile_variant = variants["mobile"]
        assert mobile_variant.url is not None
        assert mobile_variant.preset_id == "mobile_optimized"
        assert mobile_variant.file_size_kb is None

    def test_generate_variant_url(self, configured_client):
        """Test variant URL generation"""
        url = configured_client.generate_variant_url(
            public_id="sayar/products/merchant_id/image_123",
            transformation="c_limit,w_800,h_800,f_auto,q_auto:auto",
            version=1234567890,
        )

        expected = "https://res.cloudinary.com/test-cloud/image/upload/c_limit,w_800,h_800,f_auto,q_auto:auto/v1234567890/sayar/products/merchant_id/image_123"
        assert url == expected

    def test_test_preset_transformation(self, configured_client):
        """Test preset transformation testing"""
        result = configured_client.test_preset_transformation(
            preset_id="main_catalog",
            test_image_url="https://res.cloudinary.com/demo/image/upload/sample.jpg",
        )

        assert result.success is True
        assert result.transformed_url is not None
        assert "c_limit,w_1600,h_1600,f_auto,q_auto:good" in result.transformed_url
        assert result.estimated_file_size_kb is not None
        assert result.dimensions.width <= 1600
        assert result.dimensions.height <= 1600

    def test_verify_variant_url_exists(self, configured_client):
        """Test variant URL existence verification"""
        with patch("requests.head") as mock_head:
            mock_head.return_value.status_code = 200

            result = configured_client.verify_variant_url_exists(
                "https://res.cloudinary.com/test/image/upload/c_limit,w_800,h_800/test.jpg"
            )

            assert result is True

        with patch("requests.head") as mock_head:
            mock_head.return_value.status_code = 404

            result = configured_client.verify_variant_url_exists(
                "https://res.cloudinary.com/test/image/upload/nonexistent.jpg"
            )

            assert result is False

    def test_batch_generate_variants(self, configured_client):
        """Test batch variant generation"""
        preset_ids = ["main_catalog", "dashboard_thumb", "mobile_optimized"]
        public_id = "sayar/products/merchant_id/image_123"
        version = 1234567890

        variants = configured_client.batch_generate_variants(
            public_id=public_id, preset_ids=preset_ids, version=version
        )

        assert len(variants) == 3
        for preset_id in preset_ids:
            assert preset_id in variants
            assert variants[preset_id] is not None
            assert public_id in variants[preset_id]


class TestCloudinaryServiceWithPresets:
    """Test CloudinaryService preset functionality"""

    @pytest.fixture
    def service(self, db_session):
        """Create CloudinaryService instance for testing"""
        return CloudinaryService(db_session)

    @pytest.fixture
    def test_merchant(self, db_session):
        """Create test merchant"""
        merchant = Merchant(id=uuid.uuid4(), name="Test Merchant", currency="NGN")
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
            retailer_id=f"test_merchant_{uuid.uuid4().hex[:8]}_prod_{uuid.uuid4().hex[:8]}",
        )
        db_session.add(product)
        db_session.commit()
        return product

    @patch.object(CloudinaryClient, "upload_image_with_presets")
    @patch.object(CloudinaryClient, "verify_variant_url_exists")
    def test_upload_product_image_with_presets_standard(
        self, mock_verify, mock_upload, service, test_product
    ):
        """Test product image upload with standard preset profile"""
        mock_verify.return_value = True
        mock_upload.return_value = {
            "public_id": "sayar/products/merchant_id/image_123",
            "variants": {
                "main": ImageVariant(
                    url="https://example.com/main.jpg",
                    preset_id="main_catalog",
                    file_size_kb=245,
                    dimensions=ImageDimensions(width=1600, height=1067),
                    format="webp",
                    quality_score=85,
                    processing_time_ms=850,
                ),
                "thumb": ImageVariant(
                    url="https://example.com/thumb.jpg",
                    preset_id="dashboard_thumb",
                    file_size_kb=82,
                    dimensions=ImageDimensions(width=600, height=600),
                    format="webp",
                    quality_score=75,
                    processing_time_ms=420,
                ),
                "mobile": ImageVariant(
                    url="https://example.com/mobile.jpg", preset_id="mobile_optimized"
                ),
                "list": ImageVariant(
                    url="https://example.com/list.jpg", preset_id="product_list"
                ),
            },
            "width": 1200,
            "height": 800,
            "format": "jpg",
            "bytes": 80000,
            "version": 1234567890,
        }

        # Create test image content
        img = Image.new("RGB", (1200, 800), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        img_content = img_bytes.getvalue()

        request = UploadWithPresetsRequest(
            is_primary=True,
            alt_text="Test image",
            preset_profile=PresetProfile.STANDARD,
        )

        result = service.upload_product_image_with_presets(
            product_id=test_product.id,
            merchant_id=test_product.merchant_id,
            file_content=img_content,
            filename="test.jpg",
            request=request,
        )

        assert isinstance(result.id, uuid.UUID)
        assert result.product_id == test_product.id
        assert result.preset_profile == PresetProfile.STANDARD
        assert result.is_primary is True
        assert result.alt_text == "Test image"
        assert result.upload_status == "uploading"
        assert result.preset_version == 1

        # Check variants
        assert "main" in result.variants
        assert "thumb" in result.variants
        assert "mobile" in result.variants
        assert "list" in result.variants

        main_variant = result.variants["main"]
        assert main_variant.preset_id == "main_catalog"
        assert main_variant.file_size_kb == 245

        # Check database record
        image = (
            service.db.query(ProductImage).filter(ProductImage.id == result.id).first()
        )
        assert image is not None
        assert image.preset_profile == "standard"
        assert image.variants is not None
        assert len(image.variants) == 4
        assert image.optimization_stats is not None
        assert image.preset_version == 1

    @patch.object(CloudinaryClient, "upload_image_with_presets")
    def test_upload_product_image_with_presets_premium(
        self, mock_upload, service, test_product
    ):
        """Test product image upload with premium preset profile"""
        mock_upload.return_value = {
            "public_id": "sayar/products/merchant_id/image_123",
            "variants": {
                "main": ImageVariant(
                    url="https://example.com/main.jpg", preset_id="main_catalog"
                ),
                "thumb": ImageVariant(
                    url="https://example.com/thumb.jpg", preset_id="dashboard_thumb"
                ),
                "mobile": ImageVariant(
                    url="https://example.com/mobile.jpg", preset_id="mobile_optimized"
                ),
                "list": ImageVariant(
                    url="https://example.com/list.jpg", preset_id="product_list"
                ),
                "detail": ImageVariant(
                    url="https://example.com/detail.jpg", preset_id="detailed_view"
                ),
            },
            "width": 2000,
            "height": 1333,
            "format": "jpg",
            "bytes": 120000,
            "version": 1234567890,
        }

        img_content = b"fake_image_content"
        request = UploadWithPresetsRequest(
            is_primary=False, preset_profile=PresetProfile.PREMIUM
        )

        result = service.upload_product_image_with_presets(
            product_id=test_product.id,
            merchant_id=test_product.merchant_id,
            file_content=img_content,
            filename="test.jpg",
            request=request,
        )

        assert result.preset_profile == PresetProfile.PREMIUM
        assert "detail" in result.variants  # Premium profile includes detail variant

    def test_regenerate_variants_for_profile(self, service, test_product):
        """Test regenerating variants with a new preset profile"""
        # Create existing image
        image = ProductImage(
            id=uuid.uuid4(),
            product_id=test_product.id,
            merchant_id=test_product.merchant_id,
            cloudinary_public_id="test_public_id",
            secure_url="https://example.com/original.jpg",
            preset_profile="standard",
            variants={
                "main": {
                    "url": "https://example.com/old_main.jpg",
                    "preset_id": "main_catalog",
                }
            },
            optimization_stats={"original_profile": "standard"},
            preset_version=1,
            cloudinary_version=1234567890,
            upload_status="completed",
        )
        service.db.add(image)
        service.db.commit()

        with patch.object(
            service.cloudinary_client, "generate_variant_url"
        ) as mock_generate:
            mock_generate.side_effect = (
                lambda public_id, transformation, version: f"https://example.com/{transformation[:10]}.jpg"
            )

            result = service.regenerate_variants_for_profile(
                image_id=image.id,
                merchant_id=test_product.merchant_id,
                new_profile=PresetProfile.MOBILE_FIRST,
            )

            assert result.preset_profile == PresetProfile.MOBILE_FIRST
            assert result.preset_version == 1
            assert "main" in result.variants
            assert "catalog" in result.variants  # Mobile-first profile specific variant

            # Check database was updated
            updated_image = (
                service.db.query(ProductImage)
                .filter(ProductImage.id == image.id)
                .first()
            )
            assert updated_image.preset_profile == "mobile_first"
            assert "previous_profile" in updated_image.optimization_stats

    def test_get_preset_statistics(self, service, test_merchant):
        """Test getting preset usage statistics"""
        # Create some test statistics using raw SQL
        service.db.execute(
            """
            INSERT INTO cloudinary_preset_stats
            (merchant_id, preset_id, usage_count, avg_file_size_kb, avg_processing_time_ms, quality_score_avg, last_used_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(test_merchant.id),
                "main_catalog",
                25,
                245,
                850,
                85.5,
                datetime.utcnow(),
            ),
        )
        service.db.commit()

        stats = service.get_preset_statistics(
            merchant_id=test_merchant.id, preset_id="main_catalog", days=30
        )

        assert len(stats) == 1
        stat = stats[0]
        assert stat["preset_id"] == "main_catalog"
        assert stat["usage_count"] == 25
        assert stat["avg_file_size_kb"] == 245
        assert stat["avg_processing_time_ms"] == 850
        assert stat["quality_score_avg"] == 85.5

    def test_update_preset_statistics(self, service, test_merchant):
        """Test updating preset statistics"""
        variants = {
            "main": ImageVariant(
                url="https://example.com/main.jpg",
                preset_id="main_catalog",
                file_size_kb=250,
                processing_time_ms=800,
                quality_score=88,
            ),
            "thumb": ImageVariant(
                url="https://example.com/thumb.jpg",
                preset_id="dashboard_thumb",
                file_size_kb=75,
                processing_time_ms=400,
                quality_score=80,
            ),
        }

        # Call the private method
        service._update_preset_statistics(
            merchant_id=test_merchant.id, variants=variants, processing_time_ms=1200
        )

        # Check that stats were created
        stats = service.get_preset_statistics(merchant_id=test_merchant.id, days=1)

        assert len(stats) == 2

        main_stat = next((s for s in stats if s["preset_id"] == "main_catalog"), None)
        assert main_stat is not None
        assert main_stat["usage_count"] == 1
        assert main_stat["avg_file_size_kb"] == 250


class TestPresetAdminAPI:
    """Test admin API endpoints for preset management"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def admin_headers(self):
        """Create admin authorization headers"""
        return {"Authorization": "Bearer admin_token"}

    def test_list_presets_endpoint(self, client, admin_headers):
        """Test listing all presets"""
        with patch("src.auth.dependencies.get_current_admin_user"):
            response = client.get(
                "/api/v1/admin/cloudinary/presets/", headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "presets" in data["data"]

            presets = data["data"]["presets"]
            assert len(presets) >= 5  # At least 5 standard presets

            # Check preset structure
            main_preset = next((p for p in presets if p["id"] == "main_catalog"), None)
            assert main_preset is not None
            assert main_preset["name"] == "Main (Meta Catalog)"
            assert "transformation" in main_preset
            assert "constraints" in main_preset
            assert "quality_targets" in main_preset

    def test_list_preset_profiles_endpoint(self, client, admin_headers):
        """Test listing all preset profiles"""
        with patch("src.auth.dependencies.get_current_admin_user"):
            response = client.get(
                "/api/v1/admin/cloudinary/presets/profiles", headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "profiles" in data["data"]

            profiles = data["data"]["profiles"]
            assert len(profiles) == 4  # 4 standard profiles

            # Check profile structure
            standard_profile = next(
                (p for p in profiles if p["id"] == "standard"), None
            )
            assert standard_profile is not None
            assert standard_profile["name"] == "Standard Profile"
            assert "presets" in standard_profile
            assert "default_eager_variants" in standard_profile

    def test_test_preset_endpoint(self, client, admin_headers):
        """Test preset testing endpoint"""
        with patch("src.auth.dependencies.get_current_admin_user"), patch.object(
            CloudinaryClient, "test_preset_transformation"
        ) as mock_test:

            mock_test.return_value = {
                "success": True,
                "transformed_url": "https://example.com/transformed.jpg",
                "estimated_file_size_kb": 250,
                "dimensions": {"width": 1600, "height": 1067},
                "format": "webp",
                "quality_score": 85,
                "processing_time_ms": 500,
            }

            response = client.post(
                "/api/v1/admin/cloudinary/presets/test",
                headers=admin_headers,
                json={
                    "preset_id": "main_catalog",
                    "test_image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "transformed_url" in data

    def test_get_preset_statistics_endpoint(self, client, admin_headers, db_session):
        """Test getting preset statistics"""
        # Create test merchant and stats
        merchant = Merchant(id=uuid.uuid4(), name="Test", currency="NGN")
        db_session.add(merchant)
        db_session.commit()

        db_session.execute(
            """
            INSERT INTO cloudinary_preset_stats
            (merchant_id, preset_id, usage_count, avg_file_size_kb, avg_processing_time_ms, quality_score_avg, last_used_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (str(merchant.id), "main_catalog", 15, 240, 800, 87.0, datetime.utcnow()),
        )
        db_session.commit()

        with patch("src.auth.dependencies.get_current_admin_user"):
            response = client.get(
                f"/api/v1/admin/cloudinary/presets/stats?merchant_id={merchant.id}&days=7",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1

            stat = data[0]
            assert stat["preset_id"] == "main_catalog"
            assert stat["name"] == "Main (Meta Catalog)"
            assert stat["stats"]["usage_count"] == 15

    def test_validate_presets_endpoint(self, client, admin_headers):
        """Test preset validation endpoint"""
        with patch("src.auth.dependencies.get_current_admin_user"):
            response = client.get(
                "/api/v1/admin/cloudinary/presets/validate", headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["valid"] is True
            assert data["data"]["presets_count"] >= 5
            assert data["data"]["profiles_count"] == 4

    def test_health_check_endpoint(self, client, admin_headers):
        """Test preset system health check"""
        with patch("src.auth.dependencies.get_current_admin_user"), patch.object(
            CloudinaryService, "health_check"
        ) as mock_health:

            mock_health.return_value = {
                "configured": True,
                "cloud_name": "test-cloud",
                "verified_at": datetime.now(),
            }

            response = client.get(
                "/api/v1/admin/cloudinary/presets/health", headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["cloudinary"]["configured"] is True
            assert data["data"]["preset_config_valid"] is True

    def test_performance_metrics_endpoint(self, client, admin_headers, db_session):
        """Test performance metrics endpoint"""
        # Create test data
        merchant = Merchant(id=uuid.uuid4(), name="Test", currency="NGN")
        db_session.add(merchant)
        db_session.commit()

        recent_time = datetime.utcnow() - timedelta(days=1)
        db_session.execute(
            """
            INSERT INTO cloudinary_preset_stats
            (merchant_id, preset_id, usage_count, avg_file_size_kb, avg_processing_time_ms, quality_score_avg, last_used_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (str(merchant.id), "main_catalog", 50, 248, 750, 86.5, recent_time),
        )
        db_session.commit()

        with patch("src.auth.dependencies.get_current_admin_user"):
            response = client.get(
                "/api/v1/admin/cloudinary/presets/performance?days=7",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "performance_metrics" in data["data"]
            assert data["data"]["period_days"] == 7


class TestPresetErrorHandling:
    """Test error handling for preset operations"""

    @pytest.fixture
    def service(self, db_session):
        return CloudinaryService(db_session)

    def test_invalid_preset_profile(self, service):
        """Test handling of invalid preset profile"""
        # This would normally be caught by Pydantic validation
        # but testing service-level handling
        pass

    def test_missing_preset_id(self):
        """Test handling of missing preset ID"""
        with pytest.raises(ValueError):
            get_preset_by_id("nonexistent_preset")

    def test_malformed_transformation(self):
        """Test validation of malformed transformation strings"""
        from src.models.cloudinary import (
            CloudinaryTransformPreset,
            PresetConstraints,
            PresetUseCase,
        )

        with pytest.raises(ValueError):
            CloudinaryTransformPreset(
                id="invalid",
                name="Invalid Preset",
                description="Missing required parameters",
                transformation="w_800",  # Missing crop, format, quality
                use_cases=[PresetUseCase.MOBILE_OPTIMIZED],
                constraints=PresetConstraints(max_width=800, max_height=800),
            )

    def test_cloudinary_client_failure_fallback(self, service, monkeypatch):
        """Test fallback behavior when Cloudinary operations fail"""
        # This would test the service behavior when Cloudinary API is down
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
