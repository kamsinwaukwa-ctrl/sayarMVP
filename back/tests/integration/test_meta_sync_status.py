"""
Integration tests for Meta sync status API and reason normalization
Tests the complete status checking workflow from API endpoints to database state
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.sqlalchemy_models import Product, Merchant, User
from src.models.meta_catalog import MetaSyncStatus
from src.services.meta_catalog_service import MetaSyncReasonNormalizer

pytestmark = pytest.mark.asyncio


class TestMetaSyncStatusAPI:
    """Test Meta sync status endpoint"""

    async def test_get_sync_status_success_synced(
        self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession
    ):
        """Test successful status retrieval for synced product"""
        # Create test product with synced status
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440001")

        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Test Synced Product",
                price_kobo=15000,
                stock=100,
                sku="SYNC-TEST-001",
                meta_sync_status=MetaSyncStatus.SYNCED.value,
                meta_catalog_visible=True,
                meta_last_synced_at=datetime.now(),
                retailer_id="meta_test_prod123",
            )
        )
        await test_db.commit()

        # Get sync status
        response = await app_client.get(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "synced"
        assert data["reason"] is None
        assert data["last_synced_at"] is not None

    async def test_get_sync_status_error_with_reason(
        self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession
    ):
        """Test status retrieval for product with error and reason"""
        # Create test product with error status and reason
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440002")
        error_reason = "Product image is invalid or missing. Please upload a valid image and try again."

        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Test Error Product",
                price_kobo=15000,
                stock=100,
                sku="SYNC-TEST-002",
                meta_sync_status=MetaSyncStatus.ERROR.value,
                meta_catalog_visible=True,
                meta_sync_errors=["Invalid image_url parameter"],
                meta_sync_reason=error_reason,
                retailer_id="meta_test_prod124",
            )
        )
        await test_db.commit()

        # Get sync status
        response = await app_client.get(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["reason"] == error_reason
        assert data["last_synced_at"] is None

    async def test_get_sync_status_pending_no_reason(
        self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession
    ):
        """Test status retrieval for pending product"""
        # Create test product with pending status
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440003")

        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Test Pending Product",
                price_kobo=15000,
                stock=100,
                sku="SYNC-TEST-003",
                meta_sync_status=MetaSyncStatus.PENDING.value,
                meta_catalog_visible=True,
                retailer_id="meta_test_prod125",
            )
        )
        await test_db.commit()

        # Get sync status
        response = await app_client.get(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["reason"] is None
        assert data["last_synced_at"] is None

    async def test_get_sync_status_product_not_found(
        self, app_client: AsyncClient, test_merchant_jwt: str
    ):
        """Test status retrieval for non-existent product"""
        non_existent_id = UUID("999e8400-e29b-41d4-a716-446655440000")

        response = await app_client.get(
            f"/api/v1/products/{non_existent_id}/meta-sync",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_sync_status_cross_tenant_isolation(
        self, app_client: AsyncClient, test_db: AsyncSession
    ):
        """Test that users cannot access other merchants' product status"""
        # Create product for one merchant
        merchant1_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        merchant2_id = UUID("550e8400-e29b-41d4-a716-446655440001")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440004")

        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant1_id,
                title="Merchant 1 Product",
                price_kobo=15000,
                stock=100,
                sku="CROSS-TENANT-001",
                meta_sync_status=MetaSyncStatus.SYNCED.value,
                meta_catalog_visible=True,
                retailer_id="meta_test_cross",
            )
        )
        await test_db.commit()

        # Create JWT for merchant 2
        merchant2_jwt = "test_jwt_token_merchant_550e8400-e29b-41d4-a716-446655440001"

        # Try to access merchant 1's product with merchant 2's JWT
        response = await app_client.get(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {merchant2_jwt}"},
        )

        assert response.status_code == 404

    async def test_get_sync_status_unauthorized(self, app_client: AsyncClient):
        """Test status retrieval without authentication"""
        product_id = UUID("770e8400-e29b-41d4-a716-446655440001")

        response = await app_client.get(f"/api/v1/products/{product_id}/meta-sync")

        assert response.status_code == 401

    async def test_legacy_rows_reason_backfilled_on_read(
        self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession
    ):
        """Test that legacy rows get reason backfilled on first read"""
        # Create test product with error status but no reason (legacy row)
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440005")

        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Legacy Error Product",
                price_kobo=15000,
                stock=100,
                sku="LEGACY-TEST-001",
                meta_sync_status=MetaSyncStatus.ERROR.value,
                meta_catalog_visible=True,
                meta_sync_errors=[
                    "Invalid image_url parameter",
                    "Authentication failed",
                ],
                meta_sync_reason=None,  # Legacy row with no reason
                retailer_id="meta_legacy_prod",
            )
        )
        await test_db.commit()

        # Get sync status (should trigger backfill)
        response = await app_client.get(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"},
        )

        # Verify response has reason
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["reason"] is not None
        assert len(data["reason"]) > 0

        # Verify database was updated with backfilled reason
        result = await test_db.execute(select(Product).where(Product.id == product_id))
        product = result.fetchone()
        assert product.meta_sync_reason is not None


class TestMetaSyncReasonNormalizer:
    """Test reason normalization logic"""

    async def test_reason_normalization_image_error(self):
        """Test normalization of image-related errors"""
        errors = ["Invalid image_url parameter", "Missing image_link"]
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "image" in reason.lower()
        assert "upload" in reason.lower() or "missing" in reason.lower()

    async def test_reason_normalization_auth_error(self):
        """Test normalization of authentication errors"""
        errors = ["OAuth error with code 190", "Invalid access token"]
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "authentication" in reason.lower() or "reconnect" in reason.lower()

    async def test_reason_normalization_rate_limit(self):
        """Test normalization of rate limit errors"""
        errors = ["Rate limit exceeded", "Too many requests"]
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "rate" in reason.lower() or "too many" in reason.lower()

    async def test_reason_normalization_unknown_error(self):
        """Test normalization of unknown errors"""
        errors = ["Some unknown server error", "Unexpected response"]
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "unexpected" in reason.lower() or "try again" in reason.lower()

    async def test_reason_normalization_policy_block(self):
        """Test normalization of policy block errors"""
        errors = ["Product blocked by policy", "Code 368 violation"]
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "blocked" in reason.lower()

    async def test_reason_normalization_price_format(self):
        """Test normalization of price format errors"""
        errors = ["Invalid price format", "Price must be numeric"]
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "price" in reason.lower() and "format" in reason.lower()

    async def test_reason_normalization_no_errors_for_success(self):
        """Test that successful status returns no reason"""
        errors = []
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "synced")

        assert reason is None

    async def test_reason_normalization_no_errors_for_pending(self):
        """Test that pending status returns no reason"""
        errors = []
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "pending")

        assert reason is None

    async def test_reason_normalization_empty_errors_fallback(self):
        """Test fallback for empty errors list"""
        errors = []
        reason = MetaSyncReasonNormalizer.normalize_errors(errors, "error")

        assert "unexpected" in reason.lower()

    async def test_get_reason_category_auth(self):
        """Test reason category classification for auth errors"""
        reason = "Authentication failed. Reconnect catalog credentials."
        category = MetaSyncReasonNormalizer.get_reason_category(reason)

        assert category == "auth"

    async def test_get_reason_category_missing_image(self):
        """Test reason category classification for image errors"""
        reason = "Missing image_link. Add a primary product image."
        category = MetaSyncReasonNormalizer.get_reason_category(reason)

        assert category == "missing_image"

    async def test_get_reason_category_price_format(self):
        """Test reason category classification for price errors"""
        reason = "Price format invalid. Use like 123.45 NGN."
        category = MetaSyncReasonNormalizer.get_reason_category(reason)

        assert category == "price_format"

    async def test_get_reason_category_policy_block(self):
        """Test reason category classification for policy blocks"""
        reason = "Temporarily blocked by Meta. Try again later."
        category = MetaSyncReasonNormalizer.get_reason_category(reason)

        assert category == "policy_block"

    async def test_get_reason_category_unknown(self):
        """Test reason category classification for unknown errors"""
        reason = "Some other error message"
        category = MetaSyncReasonNormalizer.get_reason_category(reason)

        assert category == "unknown"


# Test fixtures
@pytest.fixture
def test_merchant_jwt() -> str:
    """Create a test JWT token for authentication"""
    return "test_jwt_token_merchant_550e8400-e29b-41d4-a716-446655440000"
