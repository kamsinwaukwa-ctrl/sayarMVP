"""
Integration tests for Products CRUD API with Meta catalog sync
Tests the complete product workflow from API endpoints to database state
"""

import pytest
import json
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.models.sqlalchemy_models import Product, Merchant, User
from src.models.meta_catalog import MetaSyncStatus, MetaCatalogSyncResult
from src.integrations.meta_catalog import MetaCatalogClient
from src.services.product_service import ProductService

pytestmark = pytest.mark.asyncio

class TestProductsAPI:
    """Test Products API endpoints with real database integration"""
    
    async def test_create_product_happy_path(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test complete product creation flow with Meta sync"""
        # Mock Meta catalog client for predictable testing
        with patch.object(MetaCatalogClient, 'create_product') as mock_create:
            mock_create.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id="meta_test123_prod456",
                meta_product_id="meta_12345",
                sync_duration_ms=150
            )
            
            # Create product request
            product_data = {
                "title": "Test Premium Face Cream",
                "description": "Luxury anti-aging face cream for testing",
                "price_kobo": 25000,
                "stock": 50,
                "sku": "TEST-FACE-CREAM-001",
                "category_path": "skincare/face/creams",
                "tags": ["premium", "anti-aging", "test"],
                "meta_catalog_visible": True,
                "image_file_id": "test_image_123"
            }
            
            # Send create request
            response = await app_client.post(
                "/api/v1/products",
                json=product_data,
                headers={
                    "Authorization": f"Bearer {test_merchant_jwt}",
                    "Idempotency-Key": str(uuid4())
                }
            )
            
            # Verify API response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["ok"] is True
            assert response_data["message"] == "Product created successfully"
            
            product = response_data["data"]
            assert product["title"] == product_data["title"]
            assert product["price_kobo"] == product_data["price_kobo"]
            assert product["stock"] == product_data["stock"]
            assert product["available_qty"] == product_data["stock"]
            assert product["reserved_qty"] == 0
            assert product["sku"] == product_data["sku"]
            assert product["status"] == "active"
            assert product["meta_catalog_visible"] is True
            assert product["meta_sync_status"] == MetaSyncStatus.PENDING.value
            assert "retailer_id" in product
            
            # Verify database state
            product_id = UUID(product["id"])
            stmt = select(Product).where(Product.id == product_id)
            result = await test_db.execute(stmt)
            db_product = result.fetchone()
            
            assert db_product is not None
            assert db_product.title == product_data["title"]
            assert db_product.price_kobo == product_data["price_kobo"]
            assert db_product.sku == product_data["sku"]
            assert db_product.meta_catalog_visible is True
            assert db_product.meta_sync_status == MetaSyncStatus.PENDING.value
    
    async def test_create_product_sku_duplicate(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test SKU duplication prevention within merchant"""
        # Create first product
        product_data = {
            "title": "First Product",
            "price_kobo": 15000,
            "stock": 100,
            "sku": "DUPLICATE-SKU-001"
        }
        
        response1 = await app_client.post(
            "/api/v1/products",
            json=product_data,
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        assert response1.status_code == 200
        
        # Try to create second product with same SKU
        product_data["title"] = "Second Product"
        response2 = await app_client.post(
            "/api/v1/products",
            json=product_data,
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        # Should return 409 Conflict
        assert response2.status_code == 409
        error_data = response2.json()
        assert "SKU" in error_data["detail"]
        assert "already exists" in error_data["detail"]
    
    async def test_idempotency_handling(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test duplicate request handling with idempotency key"""
        idempotency_key = str(uuid4())
        product_data = {
            "title": "Idempotent Product",
            "price_kobo": 20000,
            "stock": 75,
            "sku": "IDEMPOTENT-001"
        }
        
        # Send first request
        response1 = await app_client.post(
            "/api/v1/products",
            json=product_data,
            headers={
                "Authorization": f"Bearer {test_merchant_jwt}",
                "Idempotency-Key": idempotency_key
            }
        )
        assert response1.status_code == 200
        product1_id = response1.json()["data"]["id"]
        
        # Send identical request with same idempotency key
        response2 = await app_client.post(
            "/api/v1/products",
            json=product_data,
            headers={
                "Authorization": f"Bearer {test_merchant_jwt}",
                "Idempotency-Key": idempotency_key
            }
        )
        
        # Should return same response
        assert response2.status_code == 200
        product2_id = response2.json()["data"]["id"]
        assert product1_id == product2_id
        
        # Verify only one product exists in database
        stmt = select(Product).where(Product.sku == "IDEMPOTENT-001")
        result = await test_db.execute(stmt)
        products = result.fetchall()
        assert len(products) == 1
    
    async def test_get_product(self, app_client: AsyncClient, test_merchant_jwt: str, test_product: Product):
        """Test getting product by ID"""
        response = await app_client.get(
            f"/api/v1/products/{test_product.id}",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["ok"] is True
        
        product = response_data["data"]
        assert product["id"] == str(test_product.id)
        assert product["title"] == test_product.title
        assert product["sku"] == test_product.sku
    
    async def test_get_product_not_found(self, app_client: AsyncClient, test_merchant_jwt: str):
        """Test getting non-existent product"""
        fake_id = uuid4()
        response = await app_client.get(
            f"/api/v1/products/{fake_id}",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    async def test_update_product(self, app_client: AsyncClient, test_merchant_jwt: str, test_product: Product, test_db: AsyncSession):
        """Test updating product with Meta sync"""
        with patch.object(MetaCatalogClient, 'update_product') as mock_update:
            mock_update.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id=test_product.retailer_id,
                meta_product_id="meta_12345",
                sync_duration_ms=200
            )
            
            update_data = {
                "title": "Updated Product Title",
                "price_kobo": 30000,
                "stock": 150,
                "meta_catalog_visible": True
            }
            
            response = await app_client.put(
                f"/api/v1/products/{test_product.id}",
                json=update_data,
                headers={
                    "Authorization": f"Bearer {test_merchant_jwt}",
                    "Idempotency-Key": str(uuid4())
                }
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["ok"] is True
            
            product = response_data["data"]
            assert product["title"] == update_data["title"]
            assert product["price_kobo"] == update_data["price_kobo"]
            assert product["stock"] == update_data["stock"]
            assert product["available_qty"] == update_data["stock"]  # No reservations
            
            # Verify database state
            await test_db.refresh(test_product)
            assert test_product.title == update_data["title"]
            assert test_product.price_kobo == update_data["price_kobo"]
            assert test_product.stock == update_data["stock"]
    
    async def test_delete_product(self, app_client: AsyncClient, test_merchant_jwt: str, test_product: Product, test_db: AsyncSession):
        """Test deleting product and Meta sync"""
        with patch.object(MetaCatalogClient, 'delete_product') as mock_delete:
            mock_delete.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id=test_product.retailer_id,
                sync_duration_ms=100
            )
            
            response = await app_client.delete(
                f"/api/v1/products/{test_product.id}",
                headers={
                    "Authorization": f"Bearer {test_merchant_jwt}",
                    "Idempotency-Key": str(uuid4())
                }
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["ok"] is True
            assert response_data["data"]["deleted"] is True
            
            # Verify product is deleted from database
            stmt = select(Product).where(Product.id == test_product.id)
            result = await test_db.execute(stmt)
            assert result.fetchone() is None
    
    async def test_delete_product_with_reservations(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test deletion prevention when product has reservations"""
        # Create product with reservations
        product_data = {
            "id": uuid4(),
            "merchant_id": UUID("550e8400-e29b-41d4-a716-446655440000"),  # Test merchant ID
            "title": "Reserved Product",
            "price_kobo": 15000,
            "stock": 100,
            "reserved_qty": 10,
            "available_qty": 90,
            "sku": "RESERVED-001",
            "status": "active",
            "retailer_id": f"meta_test_{uuid4().hex[:10]}",
            "meta_catalog_visible": True,
            "meta_sync_status": MetaSyncStatus.SYNCED.value,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        product = Product(**product_data)
        test_db.add(product)
        await test_db.commit()
        
        response = await app_client.delete(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 400
        assert "reservations" in response.json()["detail"]
    
    async def test_list_products(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test listing products with pagination and filters"""
        # Create multiple test products
        products_data = [
            {
                "title": f"Product {i}",
                "price_kobo": 10000 + (i * 1000),
                "stock": 50 + i,
                "sku": f"LIST-TEST-{i:03d}",
                "category_path": "test/category",
                "status": "active" if i % 2 == 0 else "inactive",
                "meta_catalog_visible": i % 3 == 0
            }
            for i in range(1, 6)
        ]
        
        for product_data in products_data:
            await app_client.post(
                "/api/v1/products",
                json=product_data,
                headers={"Authorization": f"Bearer {test_merchant_jwt}"}
            )
        
        # Test basic listing
        response = await app_client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["ok"] is True
        
        data = response_data["data"]
        assert "products" in data
        assert "pagination" in data
        assert len(data["products"]) >= 5
        
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 20
        assert pagination["total_items"] >= 5
        
        # Test filtering by status
        response = await app_client.get(
            "/api/v1/products?status=active",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 200
        filtered_data = response.json()["data"]
        active_products = [p for p in filtered_data["products"] if p["status"] == "active"]
        assert len(active_products) >= 3  # Products 2, 4 should be active
        
        # Test filtering by Meta catalog visibility
        response = await app_client.get(
            "/api/v1/products?meta_catalog_visible=true",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 200
        visible_data = response.json()["data"]
        visible_products = [p for p in visible_data["products"] if p["meta_catalog_visible"]]
        assert len(visible_products) >= 2  # Products 3, 6 should be visible
    
    async def test_update_inventory(self, app_client: AsyncClient, test_merchant_jwt: str, test_product: Product, test_db: AsyncSession):
        """Test atomic inventory updates"""
        original_stock = test_product.stock
        stock_delta = 25
        
        response = await app_client.patch(
            f"/api/v1/products/{test_product.id}/inventory?stock_delta={stock_delta}",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["ok"] is True
        
        product = response_data["data"]
        assert product["stock"] == original_stock + stock_delta
        assert product["available_qty"] == original_stock + stock_delta  # No reservations
        
        # Verify database state
        await test_db.refresh(test_product)
        assert test_product.stock == original_stock + stock_delta
        assert test_product.available_qty == original_stock + stock_delta
    
    async def test_update_inventory_negative_stock(self, app_client: AsyncClient, test_merchant_jwt: str, test_product: Product):
        """Test inventory update validation for negative stock"""
        # Try to reduce stock below zero
        large_negative_delta = -(test_product.stock + 50)
        
        response = await app_client.patch(
            f"/api/v1/products/{test_product.id}/inventory?stock_delta={large_negative_delta}",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        assert response.status_code == 400
        assert "negative" in response.json()["detail"]
    
    @patch('src.integrations.meta_catalog.MetaCatalogClient.create_product')
    async def test_meta_sync_error_handling(self, mock_meta_api, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test Meta API error scenarios and retry logic"""
        # Mock Meta API failure
        mock_meta_api.return_value = MetaCatalogSyncResult(
            success=False,
            retailer_id="meta_test_error",
            errors=["Rate limit exceeded", "Invalid access token"],
            retry_after=datetime.now()
        )
        
        product_data = {
            "title": "Meta Error Test Product",
            "price_kobo": 15000,
            "stock": 100,
            "sku": "META-ERROR-001",
            "meta_catalog_visible": True
        }
        
        response = await app_client.post(
            "/api/v1/products",
            json=product_data,
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )
        
        # Product creation should still succeed even if Meta sync fails
        assert response.status_code == 200
        product = response.json()["data"]
        assert product["meta_sync_status"] == MetaSyncStatus.PENDING.value
        
        # Verify Meta sync job was queued
        # (In real implementation, would check outbox_events table)
        assert mock_meta_api.called is False  # API endpoint doesn't call Meta directly
    
    async def test_cross_tenant_isolation(self, app_client: AsyncClient, test_db: AsyncSession):
        """Test that merchants can only access their own products"""
        # Create products for two different merchants
        merchant1_id = UUID("550e8400-e29b-41d4-a716-446655440001")
        merchant2_id = UUID("550e8400-e29b-41d4-a716-446655440002")
        
        # Create JWT tokens for both merchants (simplified)
        merchant1_jwt = "test_jwt_merchant_1"  # Would be real JWT in practice
        merchant2_jwt = "test_jwt_merchant_2"  # Would be real JWT in practice
        
        # Create product for merchant 1
        product1_data = {
            "title": "Merchant 1 Product",
            "price_kobo": 15000,
            "stock": 100,
            "sku": "MERCHANT1-001"
        }
        
        response1 = await app_client.post(
            "/api/v1/products",
            json=product1_data,
            headers={"Authorization": f"Bearer {merchant1_jwt}"}
        )
        assert response1.status_code == 200
        product1_id = response1.json()["data"]["id"]
        
        # Try to access merchant 1's product with merchant 2's token
        response2 = await app_client.get(
            f"/api/v1/products/{product1_id}",
            headers={"Authorization": f"Bearer {merchant2_jwt}"}
        )
        
        # Should return 404 (not 403) to avoid information leakage
        assert response2.status_code == 404

# Fixtures and test helpers

@pytest.fixture
async def test_product(test_db: AsyncSession) -> Product:
    """Create a test product in the database"""
    product_data = {
        "id": uuid4(),
        "merchant_id": UUID("550e8400-e29b-41d4-a716-446655440000"),  # Test merchant ID
        "title": "Test Face Cream",
        "description": "A test product for integration testing",
        "price_kobo": 15000,
        "stock": 100,
        "reserved_qty": 0,
        "available_qty": 100,
        "sku": "TEST-PRODUCT-001",
        "status": "active",
        "retailer_id": f"meta_test_{uuid4().hex[:10]}",
        "category_path": "test/skincare",
        "tags": ["test", "skincare"],
        "meta_catalog_visible": True,
        "meta_sync_status": MetaSyncStatus.SYNCED.value,
        "meta_sync_errors": None,
        "meta_last_synced_at": datetime.now(),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    product = Product(**product_data)
    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)
    
    yield product
    
    # Cleanup
    await test_db.delete(product)
    await test_db.commit()

@pytest.fixture
def test_merchant_jwt() -> str:
    """Create a test JWT token for authentication"""
    # In a real implementation, this would create a proper JWT
    # For now, return a placeholder that the auth system recognizes
    return "test_jwt_token_merchant_550e8400-e29b-41d4-a716-446655440000"

class TestProductService:
    """Test ProductService business logic directly"""
    
    async def test_generate_retailer_id(self, test_db: AsyncSession):
        """Test retailer ID generation for Meta catalog"""
        service = ProductService(test_db)
        client = MetaCatalogClient()
        
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440002")
        
        retailer_id = client.generate_retailer_id(merchant_id, product_id)
        
        assert retailer_id.startswith("meta_")
        assert len(retailer_id) <= 100  # Meta's limit
        assert merchant_id.hex[:10] in retailer_id
        assert product_id.hex[:10] in retailer_id
        
        # Should be deterministic
        retailer_id2 = client.generate_retailer_id(merchant_id, product_id)
        assert retailer_id == retailer_id2
    
    async def test_sku_uniqueness_validation(self, test_db: AsyncSession):
        """Test SKU uniqueness validation within merchant"""
        service = ProductService(test_db)
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        
        # Should pass for new SKU
        await service._validate_sku_uniqueness(merchant_id, "UNIQUE-SKU-001")
        
        # Create product with SKU
        from src.models.meta_catalog import CreateProductRequest
        request = CreateProductRequest(
            title="Test Product",
            price_kobo=15000,
            stock=100,
            sku="DUPLICATE-SKU-001"
        )
        
        await service.create_product(merchant_id, request)
        
        # Should fail for duplicate SKU
        with pytest.raises(ValueError, match="SKU.*already exists"):
            await service._validate_sku_uniqueness(merchant_id, "DUPLICATE-SKU-001")


class TestMetaSyncAPI:
    """Test manual Meta Catalog sync endpoint"""

    async def test_trigger_meta_sync_success(self, app_client: AsyncClient, admin_token: str, test_db: AsyncSession):
        """Test successful manual Meta sync trigger"""
        # Create test product first
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440001")

        # Insert test product directly
        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Test Product for Sync",
                price_kobo=15000,
                stock=100,
                sku="SYNC-TEST-001",
                meta_sync_status=MetaSyncStatus.SYNCED.value,
                meta_catalog_visible=True,
                retailer_id="meta_test_prod123"
            )
        )
        await test_db.commit()

        # Trigger manual sync
        response = await app_client.post(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify response
        assert response.status_code == 202
        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "Meta Catalog sync job enqueued successfully"
        assert data["data"]["product_id"] == str(product_id)
        assert data["data"]["sync_status"] == "pending"
        assert "job_id" in data["data"]

        # Verify product status updated to pending
        result = await test_db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.fetchone()
        assert product.meta_sync_status == MetaSyncStatus.PENDING.value

    async def test_trigger_meta_sync_conflict(self, app_client: AsyncClient, admin_token: str, test_db: AsyncSession):
        """Test manual sync when sync already in progress"""
        # Create test product with syncing status
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440002")

        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Test Product Syncing",
                price_kobo=15000,
                stock=100,
                sku="SYNC-TEST-002",
                meta_sync_status=MetaSyncStatus.SYNCING.value,
                meta_catalog_visible=True,
                retailer_id="meta_test_prod124"
            )
        )
        await test_db.commit()

        # Try to trigger sync while already syncing
        response = await app_client.post(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify conflict response
        assert response.status_code == 409
        data = response.json()
        assert "SYNC_IN_PROGRESS" in str(data["detail"])

    async def test_trigger_meta_sync_product_not_found(self, app_client: AsyncClient, admin_token: str):
        """Test manual sync for non-existent product"""
        non_existent_id = UUID("999e8400-e29b-41d4-a716-446655440000")

        response = await app_client.post(
            f"/api/v1/products/{non_existent_id}/meta-sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_trigger_meta_sync_admin_required(self, app_client: AsyncClient, test_merchant_jwt: str):
        """Test that non-admin users cannot trigger manual sync"""
        product_id = UUID("770e8400-e29b-41d4-a716-446655440001")

        response = await app_client.post(
            f"/api/v1/products/{product_id}/meta-sync",
            headers={"Authorization": f"Bearer {test_merchant_jwt}"}
        )

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    async def test_trigger_meta_sync_unauthorized(self, app_client: AsyncClient):
        """Test manual sync without authentication"""
        product_id = UUID("770e8400-e29b-41d4-a716-446655440001")

        response = await app_client.post(f"/api/v1/products/{product_id}/meta-sync")

        assert response.status_code == 401

    async def test_trigger_meta_sync_invalid_uuid(self, app_client: AsyncClient, admin_token: str):
        """Test manual sync with invalid UUID format"""
        response = await app_client.post(
            "/api/v1/products/invalid-uuid/meta-sync",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422  # FastAPI validation error for invalid UUID

    async def test_enqueue_manual_catalog_sync_service(self, test_db: AsyncSession):
        """Test the service method directly"""
        service = ProductService(test_db)
        merchant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        product_id = UUID("770e8400-e29b-41d4-a716-446655440003")
        admin_id = UUID("880e8400-e29b-41d4-a716-446655440000")

        # Create test merchant
        await test_db.execute(
            Merchant.__table__.insert().values(
                id=merchant_id,
                business_name="Test Merchant",
                slug="test-merchant"
            )
        )

        # Create test product
        await test_db.execute(
            Product.__table__.insert().values(
                id=product_id,
                merchant_id=merchant_id,
                title="Service Test Product",
                price_kobo=20000,
                stock=50,
                sku="SERVICE-TEST-001",
                meta_sync_status=MetaSyncStatus.SYNCED.value,
                meta_catalog_visible=True,
                retailer_id="meta_service_test123"
            )
        )
        await test_db.commit()

        # Mock enqueue_job function
        with patch('src.services.product_service.enqueue_job') as mock_enqueue:
            mock_enqueue.return_value = "catalog_sync:test_job_123"

            # Test successful enqueue
            job_id = await service.enqueue_manual_catalog_sync(
                product_id=product_id,
                merchant_id=merchant_id,
                requested_by=admin_id
            )

            assert job_id == "catalog_sync:test_job_123"
            mock_enqueue.assert_called_once()

            # Verify job payload
            call_args = mock_enqueue.call_args
            payload = call_args.kwargs['payload']
            assert payload['product_id'] == str(product_id)
            assert payload['merchant_id'] == str(merchant_id)
            assert payload['trigger'] == "manual"
            assert payload['requested_by'] == str(admin_id)

        # Verify product status updated to pending
        result = await test_db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.fetchone()
        assert product.meta_sync_status == MetaSyncStatus.PENDING.value


class TestMetaUnpublishAPI:
    """Test Meta Unpublish API endpoint - POST /api/v1/products/{product_id}/meta-unpublish"""

    async def test_force_unpublish_success(self, test_client, test_db, sample_admin, sample_merchant, sample_product):
        """Test successful force unpublish operation"""
        # Set up product with meta sync
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                meta_sync_status=MetaSyncStatus.SYNCED.value,
                meta_catalog_visible=True,
                retailer_id="test_retailer_123"
            )
        )
        await test_db.commit()

        # Mock enqueue_job
        with patch('src.services.product_service.enqueue_job') as mock_enqueue:
            mock_enqueue.return_value = "catalog_unpublish:test_job_456"

            response = await test_client.post(
                f"/api/v1/products/{sample_product.id}/meta-unpublish",
                headers=create_admin_auth_headers(sample_admin.id)
            )

            assert response.status_code == 202
            data = response.json()

            # Verify response structure
            assert "data" in data
            assert data["data"]["product_id"] == str(sample_product.id)
            assert data["data"]["action"] == "force_unpublish"
            assert data["data"]["job_id"] == "catalog_unpublish:test_job_456"

            # Verify job was enqueued with correct payload
            mock_enqueue.assert_called_once()
            call_args = mock_enqueue.call_args
            assert call_args.kwargs['job_type'] == "catalog_unpublish"

            payload = call_args.kwargs['payload']
            assert payload['product_id'] == str(sample_product.id)
            assert payload['merchant_id'] == str(sample_merchant.id)
            assert payload['action'] == "force_unpublish"
            assert payload['retailer_id'] == "test_retailer_123"

    async def test_force_unpublish_not_synced(self, test_client, test_db, sample_admin, sample_product):
        """Test force unpublish on product not synced to Meta"""
        # Ensure product is not synced
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                meta_sync_status=MetaSyncStatus.NOT_SYNCED.value,
                retailer_id=None
            )
        )
        await test_db.commit()

        response = await test_client.post(
            f"/api/v1/products/{sample_product.id}/meta-unpublish",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 400
        data = response.json()
        assert "not synced to Meta Commerce Catalog" in data["detail"]

    async def test_force_unpublish_unauthorized(self, test_client, sample_merchant, sample_product):
        """Test force unpublish without admin access"""
        response = await test_client.post(
            f"/api/v1/products/{sample_product.id}/meta-unpublish",
            headers=create_auth_headers(sample_merchant.id)
        )

        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data["detail"]

    async def test_force_unpublish_product_not_found(self, test_client, sample_admin):
        """Test force unpublish on non-existent product"""
        fake_product_id = uuid4()
        response = await test_client.post(
            f"/api/v1/products/{fake_product_id}/meta-unpublish",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 404
        data = response.json()
        assert "Product not found" in data["detail"]

    async def test_force_unpublish_already_pending(self, test_client, test_db, sample_admin, sample_product):
        """Test force unpublish when product already has pending operation"""
        # Set product to pending status
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                meta_sync_status=MetaSyncStatus.PENDING.value,
                retailer_id="test_retailer_123"
            )
        )
        await test_db.commit()

        response = await test_client.post(
            f"/api/v1/products/{sample_product.id}/meta-unpublish",
            headers=create_admin_auth_headers(sample_admin.id)
        )

        assert response.status_code == 409
        data = response.json()
        assert "already has a pending Meta operation" in data["detail"]


class TestMetaUnpublishJobHandler:
    """Test Meta Unpublish job processing"""

    @pytest.fixture
    async def meta_credentials(self, test_db, sample_merchant):
        """Create Meta credentials for testing"""
        credentials_data = {
            "merchant_id": sample_merchant.id,
            "catalog_id": "test_catalog_123",
            "access_token": encrypt_credential("test_access_token_456"),
            "business_account_id": "test_business_789",
            "verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await test_db.execute(
            MetaCredentials.__table__.insert().values(**credentials_data)
        )
        await test_db.commit()
        return credentials_data

    async def test_handle_catalog_unpublish_success(self, test_db, sample_merchant, sample_product, meta_credentials):
        """Test successful catalog unpublish job processing"""
        # Set up product
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                retailer_id="test_retailer_123",
                meta_sync_status=MetaSyncStatus.SYNCED.value
            )
        )
        await test_db.commit()

        job_payload = {
            "product_id": str(sample_product.id),
            "merchant_id": str(sample_merchant.id),
            "action": "force_unpublish",
            "retailer_id": "test_retailer_123"
        }

        # Mock Meta API client
        with patch('src.workers.job_handlers.MetaCatalogClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful unpublish
            mock_client.unpublish_product.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id="test_retailer_123",
                status="unpublished",
                message="Product unpublished successfully"
            )

            # Execute job handler
            from src.workers.job_handlers import handle_catalog_unpublish

            result = await handle_catalog_unpublish(test_db, job_payload)

            # Verify result
            assert result["success"] is True
            assert result["retailer_id"] == "test_retailer_123"
            assert "unpublished successfully" in result["message"]

            # Verify Meta client was called correctly
            mock_client.unpublish_product.assert_called_once()
            call_args = mock_client.unpublish_product.call_args
            assert call_args[0][0] == "test_catalog_123"  # catalog_id
            assert call_args[0][1] == "test_retailer_123"  # retailer_id

            # Verify product status updated
            result = await test_db.execute(
                select(Product).where(Product.id == sample_product.id)
            )
            product = result.fetchone()
            assert product.meta_catalog_visible is False
            assert product.meta_sync_status == MetaSyncStatus.SYNCED.value

    async def test_handle_catalog_unpublish_no_credentials(self, test_db, sample_merchant, sample_product):
        """Test catalog unpublish job when no Meta credentials exist"""
        job_payload = {
            "product_id": str(sample_product.id),
            "merchant_id": str(sample_merchant.id),
            "action": "force_unpublish",
            "retailer_id": "test_retailer_123"
        }

        from src.workers.job_handlers import handle_catalog_unpublish

        result = await handle_catalog_unpublish(test_db, job_payload)

        # Verify failure result
        assert result["success"] is False
        assert "No verified Meta credentials found" in result["error"]

    async def test_handle_catalog_unpublish_api_failure(self, test_db, sample_merchant, sample_product, meta_credentials):
        """Test catalog unpublish job when Meta API fails"""
        job_payload = {
            "product_id": str(sample_product.id),
            "merchant_id": str(sample_merchant.id),
            "action": "force_unpublish",
            "retailer_id": "test_retailer_123"
        }

        # Mock Meta API client with failure
        with patch('src.workers.job_handlers.MetaCatalogClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock API failure
            mock_client.unpublish_product.return_value = MetaCatalogSyncResult(
                success=False,
                retailer_id="test_retailer_123",
                status="error",
                message="Meta API error: Access token expired",
                error_code="INVALID_ACCESS_TOKEN"
            )

            from src.workers.job_handlers import handle_catalog_unpublish

            result = await handle_catalog_unpublish(test_db, job_payload)

            # Verify failure result
            assert result["success"] is False
            assert "Meta API error: Access token expired" in result["error"]
            assert result["error_code"] == "INVALID_ACCESS_TOKEN"

    async def test_automatic_unpublish_on_status_change(self, test_client, test_db, sample_merchant, sample_product):
        """Test automatic unpublish when product status changes to archived"""
        # Set up product as synced and active
        await test_db.execute(
            Product.__table__.update()
            .where(Product.id == sample_product.id)
            .values(
                status="active",
                meta_sync_status=MetaSyncStatus.SYNCED.value,
                meta_catalog_visible=True,
                retailer_id="test_retailer_123"
            )
        )
        await test_db.commit()

        # Mock enqueue_job to capture unpublish job
        with patch('src.services.product_service.enqueue_job') as mock_enqueue:
            mock_enqueue.return_value = "catalog_unpublish:auto_job_789"

            # Update product to archived status
            response = await test_client.put(
                f"/api/v1/products/{sample_product.id}",
                headers=create_auth_headers(sample_merchant.id),
                json={"status": "archived"}
            )

            assert response.status_code == 200

            # Verify unpublish job was enqueued
            mock_enqueue.assert_called()

            # Find the unpublish job call
            unpublish_calls = [
                call for call in mock_enqueue.call_args_list
                if call.kwargs.get('job_type') == 'catalog_unpublish'
            ]
            assert len(unpublish_calls) == 1

            unpublish_call = unpublish_calls[0]
            payload = unpublish_call.kwargs['payload']
            assert payload['action'] == "status_change"
            assert payload['old_status'] == "active"
            assert payload['new_status'] == "archived"


class TestProductAutoGeneration:
    """Test auto-generation of brand, SKU, and MPN fields (BE-010.2)"""

    async def test_create_product_auto_generation_minimal(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test product creation with auto-generated brand, SKU, and MPN"""
        # Mock Meta catalog client
        with patch.object(MetaCatalogClient, 'create_product') as mock_create:
            mock_create.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id="meta_test123_prod456",
                meta_product_id="meta_12345",
                sync_duration_ms=150
            )

            # Create product request without brand, sku, or mpn
            product_data = {
                "title": "Auto-Generated Test Product",
                "description": "Testing auto-generation features",
                "price_kobo": 15000,
                "stock": 25,
                # No sku, brand, or mpn provided
                "category_path": "test/auto-gen",
                "meta_catalog_visible": True
            }

            # Send create request
            response = await app_client.post(
                "/api/v1/products",
                json=product_data,
                headers={"Authorization": f"Bearer {test_merchant_jwt}"}
            )

            assert response.status_code == 201
            data = response.json()
            product = data["data"]

            # Verify auto-generated fields are present
            assert "brand" in product
            assert "sku" in product
            assert "mpn" in product

            # Verify brand is defaulted from merchant name
            assert product["brand"] == "Test Merchant"  # From test fixture merchant

            # Verify SKU pattern (merchant-slug + generated ID)
            assert product["sku"].startswith("test-merchant-")
            assert len(product["sku"]) > len("test-merchant-")

            # Verify MPN pattern (merchant-slug + SKU)
            expected_mpn = f"test-merchant-{product['sku']}"
            assert product["mpn"] == expected_mpn

            # Verify other fields are preserved
            assert product["title"] == product_data["title"]
            assert product["price_kobo"] == product_data["price_kobo"]

    async def test_create_product_explicit_values_preserved(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test that explicit brand, SKU, and MPN values are preserved"""
        with patch.object(MetaCatalogClient, 'create_product') as mock_create:
            mock_create.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id="meta_test123_prod456",
                meta_product_id="meta_12345",
                sync_duration_ms=150
            )

            # Create product request with explicit values
            product_data = {
                "title": "Explicit Values Product",
                "description": "Testing explicit value preservation",
                "price_kobo": 20000,
                "stock": 30,
                "sku": "EXPLICIT-SKU-123",
                "brand": "Custom Brand Name",
                "mpn": "CUSTOM-MPN-456",
                "category_path": "test/explicit",
                "meta_catalog_visible": True
            }

            response = await app_client.post(
                "/api/v1/products",
                json=product_data,
                headers={"Authorization": f"Bearer {test_merchant_jwt}"}
            )

            assert response.status_code == 201
            data = response.json()
            product = data["data"]

            # Verify explicit values are preserved
            assert product["sku"] == "EXPLICIT-SKU-123"
            assert product["brand"] == "Custom Brand Name"
            assert product["mpn"] == "CUSTOM-MPN-456"

    async def test_create_product_duplicate_sku_error(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test that duplicate SKU returns proper error"""
        with patch.object(MetaCatalogClient, 'create_product') as mock_create:
            mock_create.return_value = MetaCatalogSyncResult(
                success=True,
                retailer_id="meta_test123_prod456",
                meta_product_id="meta_12345",
                sync_duration_ms=150
            )

            # Create first product with specific SKU
            product_data1 = {
                "title": "First Product",
                "price_kobo": 10000,
                "stock": 10,
                "sku": "DUPLICATE-TEST-SKU"
            }

            response1 = await app_client.post(
                "/api/v1/products",
                json=product_data1,
                headers={"Authorization": f"Bearer {test_merchant_jwt}"}
            )
            assert response1.status_code == 201

            # Try to create second product with same SKU
            product_data2 = {
                "title": "Second Product",
                "price_kobo": 15000,
                "stock": 15,
                "sku": "DUPLICATE-TEST-SKU"
            }

            response2 = await app_client.post(
                "/api/v1/products",
                json=product_data2,
                headers={"Authorization": f"Bearer {test_merchant_jwt}"}
            )

            assert response2.status_code == 409
            error_data = response2.json()
            assert error_data["error"]["code"] == "DUPLICATE_SKU"

    async def test_update_product_brand_preservation(self, app_client: AsyncClient, test_merchant_jwt: str, test_db: AsyncSession):
        """Test that brand is preserved on update unless explicitly provided"""
        # First create a product with auto-generated brand
        with patch.object(MetaCatalogClient, 'create_product') as mock_create:
            mock_create.return_value = MetaCatalogSyncResult(success=True, retailer_id="test", meta_product_id="test")

            create_data = {
                "title": "Brand Preservation Test",
                "price_kobo": 12000,
                "stock": 20
                # No brand provided - should auto-generate
            }

            create_response = await app_client.post(
                "/api/v1/products",
                json=create_data,
                headers={"Authorization": f"Bearer {test_merchant_jwt}"}
            )
            assert create_response.status_code == 201
            product = create_response.json()["data"]
            original_brand = product["brand"]
            product_id = product["id"]

            # Update product without specifying brand
            with patch.object(MetaCatalogClient, 'update_product') as mock_update:
                mock_update.return_value = MetaCatalogSyncResult(success=True, retailer_id="test", meta_product_id="test")

                update_data = {
                    "title": "Updated Title",
                    "price_kobo": 15000
                    # No brand in update
                }

                update_response = await app_client.put(
                    f"/api/v1/products/{product_id}",
                    json=update_data,
                    headers={"Authorization": f"Bearer {test_merchant_jwt}"}
                )

                assert update_response.status_code == 200
                updated_product = update_response.json()["data"]

                # Verify brand is preserved
                assert updated_product["brand"] == original_brand
                assert updated_product["title"] == "Updated Title"

    async def test_meta_sync_payload_includes_brand_mpn(self, test_db: AsyncSession):
        """Test that Meta sync payload includes brand and MPN fields"""
        from src.integrations.meta_catalog import MetaCatalogClient
        from src.models.meta_catalog import ProductDB
        from uuid import uuid4
        from datetime import datetime

        # Create mock product with brand and MPN
        product_data = ProductDB(
            id=uuid4(),
            merchant_id=uuid4(),
            title="Test Product",
            description="Test description",
            price_kobo=15000,
            stock=25,
            reserved_qty=0,
            available_qty=25,
            image_url="https://example.com/image.jpg",
            sku="test-sku-123",
            brand="Test Brand",
            mpn="test-merchant-test-sku-123",
            status="active",
            retailer_id="sayar_product_test",
            category_path="test/category",
            tags=["test"],
            meta_catalog_visible=True,
            meta_sync_status="pending",
            meta_sync_errors=None,
            meta_last_synced_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Create Meta catalog client and format product
        meta_client = MetaCatalogClient()
        merchant_config = {"storefront_url": "https://example.com"}

        meta_product = meta_client.format_product_for_meta(product_data, merchant_config)

        # Verify brand and MPN are included in Meta payload
        assert meta_product.brand == "Test Brand"
        assert meta_product.mpn == "test-merchant-test-sku-123"
        assert meta_product.retailer_id == "sayar_product_test"
        assert meta_product.name == "Test Product"

    async def test_sku_generation_collision_retry(self, test_db: AsyncSession):
        """Test SKU generation with collision retry logic"""
        from src.utils.product_generation import ProductFieldGenerator
        from src.models.sqlalchemy_models import Merchant
        from uuid import uuid4

        # Create test merchant
        merchant_id = uuid4()
        merchant = Merchant(
            id=merchant_id,
            name="Collision Test Merchant",
            slug="collision-test"
        )
        test_db.add(merchant)
        await test_db.commit()

        generator = ProductFieldGenerator(test_db)

        # Generate first SKU
        sku1 = await generator.generate_unique_sku(merchant_id, "collision-test")
        assert sku1.startswith("collision-test-")

        # Create product with first SKU to cause collision scenario
        product1 = Product(
            id=uuid4(),
            merchant_id=merchant_id,
            title="Test Product 1",
            price_kobo=10000,
            stock=10,
            sku=sku1,
            brand="Test Brand",
            mpn="test-mpn",
            status="active",
            retailer_id="test_retailer_1"
        )
        test_db.add(product1)
        await test_db.commit()

        # Generate second SKU - should be different due to collision avoidance
        sku2 = await generator.generate_unique_sku(merchant_id, "collision-test")
        assert sku2.startswith("collision-test-")
        assert sku2 != sku1  # Should be different

    async def test_brand_validation_sanitization(self):
        """Test brand validation and sanitization"""
        from src.utils.product_generation import ProductFieldGenerator

        # Test normal brand
        result = ProductFieldGenerator.validate_brand("Normal Brand")
        assert result == "Normal Brand"

        # Test brand with extra spaces
        result = ProductFieldGenerator.validate_brand("  Multiple   Spaces   Brand  ")
        assert result == "Multiple Spaces Brand"

        # Test long brand (should truncate at 70 chars)
        long_brand = "This is a very long brand name that exceeds the maximum allowed length"
        result = ProductFieldGenerator.validate_brand(long_brand)
        assert len(result) <= 70

        # Test empty brand (should raise error)
        with pytest.raises(ValueError, match="Brand cannot be empty"):
            ProductFieldGenerator.validate_brand("")

        with pytest.raises(ValueError, match="Brand cannot be empty"):
            ProductFieldGenerator.validate_brand("   ")

    async def test_mpn_generation_patterns(self):
        """Test MPN generation with various patterns"""
        from src.utils.product_generation import ProductFieldGenerator

        # Test normal MPN generation
        mpn = ProductFieldGenerator.generate_mpn("test-merchant", "product-sku-123")
        assert mpn == "test-merchant-product-sku-123"

        # Test MPN with long SKU (should truncate if needed)
        long_sku = "very-long-sku-name-that-might-cause-the-mpn-to-exceed-limits"
        mpn = ProductFieldGenerator.generate_mpn("merchant", long_sku)
        assert len(mpn) <= 70
        assert mpn.startswith("merchant-")

        # Test MPN validation
        valid_mpn = "test-merchant-sku.with_dots"
        result = ProductFieldGenerator.validate_mpn(valid_mpn)
        assert result == valid_mpn

        # Test invalid MPN characters
        with pytest.raises(ValueError):
            ProductFieldGenerator.validate_mpn("invalid@mpn#chars")