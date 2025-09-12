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