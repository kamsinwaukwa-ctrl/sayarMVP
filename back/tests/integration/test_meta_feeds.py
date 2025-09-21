"""
Integration tests for Meta Feeds API endpoints
Tests complete end-to-end functionality with real database operations
"""

import pytest
import asyncio
import csv
import io
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch
import time

from src.models.sqlalchemy_models import Merchant, Product


@pytest.fixture
async def test_merchant_with_products(test_db_session):
    """Create test merchant with multiple products for feed testing"""
    # Create merchant
    merchant = Merchant(
        name="Test Beauty Store",
        slug="test-beauty-store",
        description="Premium beauty products",
        currency="NGN",
    )
    test_db_session.add(merchant)
    await test_db_session.flush()

    # Create products with different states
    products = [
        Product(
            merchant_id=merchant.id,
            title="Premium Face Cream",
            description="Anti-aging face cream with vitamin C",
            price_kobo=25000,  # 250.00 NGN
            stock=100,
            available_qty=95,  # Some reserved
            image_url="https://cdn.example.com/face-cream.jpg",
            sku="FC001",
            status="active",
            retailer_id=f"test-beauty-store_FC001",
            category_path="skincare/face/creams",
            meta_catalog_visible=True,
        ),
        Product(
            merchant_id=merchant.id,
            title="Luxury Lipstick",
            description="Long-lasting matte lipstick",
            price_kobo=15000,  # 150.00 NGN
            stock=50,
            available_qty=0,  # Out of stock
            image_url="https://cdn.example.com/lipstick.jpg",
            sku="LS001",
            status="active",
            retailer_id=f"test-beauty-store_LS001",
            category_path="makeup/lips",
            meta_catalog_visible=True,
        ),
        Product(
            merchant_id=merchant.id,
            title="Hidden Product",
            description="This should not appear in feed",
            price_kobo=30000,
            stock=10,
            available_qty=10,
            sku="HP001",
            status="active",
            retailer_id=f"test-beauty-store_HP001",
            meta_catalog_visible=False,  # Not visible in Meta catalog
        ),
        Product(
            merchant_id=merchant.id,
            title="Inactive Product",
            description="This should not appear in feed",
            price_kobo=20000,
            stock=5,
            available_qty=5,
            sku="IP001",
            status="inactive",  # Not active
            retailer_id=f"test-beauty-store_IP001",
            meta_catalog_visible=True,
        ),
    ]

    for product in products:
        test_db_session.add(product)

    await test_db_session.commit()

    return merchant, products


@pytest.fixture
async def empty_merchant(test_db_session):
    """Create test merchant with no products"""
    merchant = Merchant(
        name="New Store", slug="new-store", description="Just started", currency="NGN"
    )
    test_db_session.add(merchant)
    await test_db_session.commit()

    return merchant


class TestMetaFeedsAPI:
    """Test Meta Feeds API endpoints"""

    @pytest.mark.asyncio
    async def test_generate_feed_happy_path(
        self, app_client: AsyncClient, test_merchant_with_products
    ):
        """Test complete feed generation with real products"""
        merchant, products = test_merchant_with_products

        # Request feed
        response = await app_client.get(
            f"/api/v1/meta/feeds/{merchant.slug}/products.csv"
        )

        # Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "ETag" in response.headers
        assert "Last-Modified" in response.headers
        assert "Cache-Control" in response.headers
        assert (
            response.headers["X-Product-Count"] == "2"
        )  # Only visible, active products

        # Parse CSV content
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        # Verify CSV structure and content
        assert (
            len(rows) == 2
        )  # Only 2 products should be visible (active + meta_catalog_visible)

        # Check required CSV headers
        expected_headers = {
            "id",
            "title",
            "description",
            "availability",
            "condition",
            "price",
            "link",
            "image_link",
            "brand",
            "inventory",
            "product_type",
            "google_product_category",
        }
        assert set(rows[0].keys()) == expected_headers

        # Verify product data
        face_cream_row = next(
            (row for row in rows if row["title"] == "Premium Face Cream"), None
        )
        assert face_cream_row is not None
        assert face_cream_row["id"] == "test-beauty-store_FC001"
        assert face_cream_row["price"] == "250.00 NGN"
        assert face_cream_row["availability"] == "in stock"
        assert face_cream_row["brand"] == "Test Beauty Store"
        assert face_cream_row["inventory"] == "95"

        lipstick_row = next(
            (row for row in rows if row["title"] == "Luxury Lipstick"), None
        )
        assert lipstick_row is not None
        assert lipstick_row["availability"] == "out of stock"
        assert lipstick_row["inventory"] == "0"

    @pytest.mark.asyncio
    async def test_feed_caching_headers(
        self, app_client: AsyncClient, test_merchant_with_products
    ):
        """Test HTTP caching with ETag and Last-Modified"""
        merchant, _ = test_merchant_with_products

        # First request
        response1 = await app_client.get(
            f"/api/v1/meta/feeds/{merchant.slug}/products.csv"
        )
        assert response1.status_code == 200

        etag = response1.headers["ETag"]
        last_modified = response1.headers["Last-Modified"]

        # Second request with If-None-Match
        response2 = await app_client.get(
            f"/api/v1/meta/feeds/{merchant.slug}/products.csv",
            headers={"If-None-Match": etag},
        )
        assert response2.status_code == 304  # Not Modified

        # Third request with If-Modified-Since
        response3 = await app_client.get(
            f"/api/v1/meta/feeds/{merchant.slug}/products.csv",
            headers={"If-Modified-Since": last_modified},
        )
        assert response3.status_code == 304  # Not Modified

    @pytest.mark.asyncio
    async def test_empty_feed_new_merchant(
        self, app_client: AsyncClient, empty_merchant
    ):
        """Test feed generation for merchant with no products"""
        response = await app_client.get(
            f"/api/v1/meta/feeds/{empty_merchant.slug}/products.csv"
        )

        assert response.status_code == 200
        assert response.headers["X-Product-Count"] == "0"

        # Should return CSV headers only
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        assert len(lines) == 1  # Only header line

        # Verify headers are correct
        expected_headers = [
            "id",
            "title",
            "description",
            "availability",
            "condition",
            "price",
            "link",
            "image_link",
            "brand",
            "inventory",
            "product_type",
            "google_product_category",
        ]
        actual_headers = lines[0].split(",")
        assert actual_headers == expected_headers

    @pytest.mark.asyncio
    async def test_merchant_not_found(self, app_client: AsyncClient):
        """Test invalid merchant slug returns 404"""
        response = await app_client.get(
            "/api/v1/meta/feeds/nonexistent-merchant/products.csv"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rate_limiting(
        self, app_client: AsyncClient, test_merchant_with_products
    ):
        """Test rate limiting functionality"""
        merchant, _ = test_merchant_with_products

        # Mock the rate limit cache to simulate hitting the limit
        with patch("src.api.meta_feeds.rate_limit_cache", {}) as mock_cache:
            # Set up rate limit data to simulate hitting limit
            mock_cache["127.0.0.1"] = {
                "count": 60,  # At limit
                "window_start": time.time(),
            }

            response = await app_client.get(
                f"/api/v1/meta/feeds/{merchant.slug}/products.csv"
            )

            assert response.status_code == 429
            assert "Too many requests" in response.json()["detail"]
            assert response.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_feed_stats_endpoint(
        self, app_client: AsyncClient, test_merchant_with_products
    ):
        """Test feed stats endpoint"""
        merchant, _ = test_merchant_with_products

        response = await app_client.get(f"/api/v1/meta/feeds/{merchant.slug}/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["merchant_slug"] == merchant.slug
        assert "stats" in data
        assert "feed_url" in data

        stats = data["stats"]
        assert stats["total_products"] == 2  # Only active + visible products
        assert stats["visible_products"] == 2
        assert stats["in_stock_products"] == 1  # Only face cream is in stock

    @pytest.mark.asyncio
    async def test_csv_format_compliance(
        self, app_client: AsyncClient, test_merchant_with_products
    ):
        """Test CSV format compliance with Meta Commerce requirements"""
        merchant, _ = test_merchant_with_products

        response = await app_client.get(
            f"/api/v1/meta/feeds/{merchant.slug}/products.csv"
        )
        csv_content = response.text

        # Test CSV parsing doesn't raise errors
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        for row in rows:
            # Test required fields are present and valid
            assert row["id"]  # retailer_id should not be empty
            assert row["title"]  # title should not be empty
            assert row["availability"] in ["in stock", "out of stock"]
            assert row["condition"] == "new"
            assert "NGN" in row["price"]
            assert row["link"].startswith("http")
            assert row["brand"]

            # Test price format
            price_parts = row["price"].split()
            assert len(price_parts) == 2
            assert price_parts[1] == "NGN"
            assert float(price_parts[0]) >= 0

    @pytest.mark.asyncio
    async def test_feed_url_generation(
        self, app_client: AsyncClient, test_merchant_with_products
    ):
        """Test that product and image URLs are properly formatted"""
        merchant, _ = test_merchant_with_products

        response = await app_client.get(
            f"/api/v1/meta/feeds/{merchant.slug}/products.csv"
        )
        csv_content = response.text

        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        for row in rows:
            # Test product link format
            assert row["link"].startswith("http")
            assert "/products/" in row["link"]

            # Test image link format (should be absolute URL)
            if row["image_link"]:
                assert row["image_link"].startswith("http")

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self, app_client: AsyncClient, test_db_session
    ):
        """Test that merchants can only see their own products in feeds"""
        # Create two merchants with products
        merchant1 = Merchant(name="Store 1", slug="store-1")
        merchant2 = Merchant(name="Store 2", slug="store-2")

        test_db_session.add_all([merchant1, merchant2])
        await test_db_session.flush()

        # Add product to merchant1
        product1 = Product(
            merchant_id=merchant1.id,
            title="Product 1",
            price_kobo=10000,
            stock=10,
            available_qty=10,
            sku="P1",
            status="active",
            retailer_id="store-1_P1",
            meta_catalog_visible=True,
        )

        # Add product to merchant2
        product2 = Product(
            merchant_id=merchant2.id,
            title="Product 2",
            price_kobo=20000,
            stock=20,
            available_qty=20,
            sku="P2",
            status="active",
            retailer_id="store-2_P2",
            meta_catalog_visible=True,
        )

        test_db_session.add_all([product1, product2])
        await test_db_session.commit()

        # Test merchant1's feed only contains their product
        response1 = await app_client.get("/api/v1/meta/feeds/store-1/products.csv")
        csv_content1 = response1.text

        assert response1.status_code == 200
        assert "Product 1" in csv_content1
        assert "Product 2" not in csv_content1

        # Test merchant2's feed only contains their product
        response2 = await app_client.get("/api/v1/meta/feeds/store-2/products.csv")
        csv_content2 = response2.text

        assert response2.status_code == 200
        assert "Product 2" in csv_content2
        assert "Product 1" not in csv_content2

    @pytest.mark.asyncio
    async def test_performance_large_catalog(
        self, app_client: AsyncClient, test_db_session
    ):
        """Test feed generation performance with larger product catalog"""
        # Create merchant
        merchant = Merchant(name="Large Store", slug="large-store")
        test_db_session.add(merchant)
        await test_db_session.flush()

        # Create 100 products
        products = []
        for i in range(100):
            product = Product(
                merchant_id=merchant.id,
                title=f"Product {i:03d}",
                description=f"Description for product {i:03d}",
                price_kobo=10000 + (i * 100),
                stock=50,
                available_qty=45,
                sku=f"P{i:03d}",
                status="active",
                retailer_id=f"large-store_P{i:03d}",
                category_path="test/category",
                meta_catalog_visible=True,
            )
            products.append(product)

        test_db_session.add_all(products)
        await test_db_session.commit()

        # Test feed generation performance
        start_time = datetime.now()
        response = await app_client.get("/api/v1/meta/feeds/large-store/products.csv")
        duration = (datetime.now() - start_time).total_seconds()

        assert response.status_code == 200
        assert response.headers["X-Product-Count"] == "100"
        assert duration < 2.0  # Should complete in less than 2 seconds

        # Verify CSV content
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        assert len(lines) == 101  # 100 products + header


@pytest.mark.asyncio
async def test_rls_bypass_security(test_db_session):
    """Test that the RLS bypass function is secure and doesn't leak data"""
    # This test would be more comprehensive with actual RLS policies
    # For now, we test that the function exists and works correctly

    from src.services.meta_feed_service import MetaFeedService

    service = MetaFeedService(test_db_session)

    # Test function creation
    await service._ensure_feed_function_exists()

    # Test function call with non-existent merchant
    merchant, products = await service._get_merchant_feed_data("nonexistent-slug")

    assert merchant is None
    assert products == []
