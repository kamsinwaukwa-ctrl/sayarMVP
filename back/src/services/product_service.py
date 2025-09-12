"""
Product service for business logic and Meta catalog synchronization
Handles product CRUD operations with automatic Meta Commerce Catalog sync
"""

import hashlib
import json
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.dialects.postgresql import insert

from ..models.meta_catalog import (
    CreateProductRequest, 
    UpdateProductRequest, 
    ProductDB, 
    IdempotencyKeyDB,
    ProductFilters,
    ProductPagination,
    MetaSyncStatus
)
from ..models.sqlalchemy_models import Product, Merchant
from ..integrations.meta_catalog import MetaCatalogClient
from ..services.media_service import MediaService
from ..utils.outbox import enqueue_job
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer
from ..utils.error_handling import map_exception_to_response, create_error_response

logger = get_logger(__name__)

class ProductService:
    """Service class for product operations with Meta catalog sync"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.media_service = MediaService(db)
        self.meta_client = MetaCatalogClient()
        self.error_handler = ErrorHandler()
    
    async def create_product(
        self,
        merchant_id: UUID,
        request: CreateProductRequest,
        idempotency_key: Optional[str] = None
    ) -> ProductDB:
        """Create a new product with Meta catalog sync"""
        start_time = datetime.now()
        
        try:
            # Handle idempotency
            if idempotency_key:
                existing_response = await self._check_idempotency(
                    idempotency_key, merchant_id, "POST /api/v1/products", request.model_dump()
                )
                if existing_response:
                    logger.info(f"Returning idempotent response for product creation: {idempotency_key}")
                    return ProductDB.model_validate(existing_response)
            
            # Check SKU uniqueness within merchant
            await self._validate_sku_uniqueness(merchant_id, request.sku)
            
            # Handle image upload if provided
            image_url = None
            if request.image_file_id:
                image_url = await self.media_service.get_file_url(request.image_file_id)
            
            # Generate stable retailer_id for Meta catalog
            product_id = uuid4()
            retailer_id = self.meta_client.generate_retailer_id(merchant_id, product_id)
            
            # Create product in database
            product_data = {
                "id": product_id,
                "merchant_id": merchant_id,
                "title": request.title,
                "description": request.description,
                "price_kobo": request.price_kobo,
                "stock": request.stock,
                "reserved_qty": 0,
                "available_qty": request.stock,
                "image_url": image_url,
                "sku": request.sku,
                "status": "active",
                "retailer_id": retailer_id,
                "category_path": request.category_path,
                "tags": request.tags or [],
                "meta_catalog_visible": request.meta_catalog_visible,
                "meta_sync_status": MetaSyncStatus.PENDING.value,
                "meta_sync_errors": None,
                "meta_last_synced_at": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Insert product
            stmt = insert(Product).values(**product_data)
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Convert to Pydantic model
            product = ProductDB(**product_data)
            
            # Store idempotency response
            if idempotency_key:
                await self._store_idempotency_response(
                    idempotency_key, merchant_id, "POST /api/v1/products", 
                    request.model_dump(), product.model_dump()
                )
            
            # Queue Meta catalog sync if enabled
            if request.meta_catalog_visible:
                await self._queue_catalog_sync(product_id, "create")
            
            # Emit structured logs
            logger.info(
                "product_created",
                extra={
                    "event_type": "product_created",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "retailer_id": retailer_id,
                    "sku": request.sku,
                    "meta_catalog_visible": request.meta_catalog_visible,
                    "idempotency_key": idempotency_key
                }
            )
            
            # Record metrics
            increment_counter("products_created_total", tags={"merchant_id": str(merchant_id)})
            record_timer("product_creation_duration_seconds", 
                        (datetime.now() - start_time).total_seconds())
            
            return product
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create product: {str(e)}", extra={
                "merchant_id": str(merchant_id),
                "idempotency_key": idempotency_key,
                "error": str(e)
            })
            raise
    
    async def update_product(
        self,
        product_id: UUID,
        merchant_id: UUID,
        request: UpdateProductRequest,
        idempotency_key: Optional[str] = None
    ) -> ProductDB:
        """Update existing product with Meta catalog sync"""
        start_time = datetime.now()
        
        try:
            # Handle idempotency
            if idempotency_key:
                existing_response = await self._check_idempotency(
                    idempotency_key, merchant_id, f"PUT /api/v1/products/{product_id}", 
                    request.model_dump(exclude_none=True)
                )
                if existing_response:
                    logger.info(f"Returning idempotent response for product update: {idempotency_key}")
                    return ProductDB.model_validate(existing_response)
            
            # Get existing product
            product = await self._get_product_by_id(product_id, merchant_id)
            if not product:
                raise ValueError(f"Product not found: {product_id}")
            
            # Check SKU uniqueness if updating SKU
            if request.sku and request.sku != product.sku:
                await self._validate_sku_uniqueness(merchant_id, request.sku)
            
            # Handle image upload if provided
            image_url = product.image_url
            if request.image_file_id:
                image_url = await self.media_service.get_file_url(request.image_file_id)
            
            # Prepare update data
            update_data = {}
            update_fields = request.model_dump(exclude_none=True)
            
            for field, value in update_fields.items():
                if field == "image_file_id":
                    continue  # Handled separately
                update_data[field] = value
            
            if image_url != product.image_url:
                update_data["image_url"] = image_url
            
            # Calculate available_qty if stock changed
            if "stock" in update_data:
                update_data["available_qty"] = update_data["stock"] - product.reserved_qty
            
            # Update meta sync status if visibility changed
            if "meta_catalog_visible" in update_data:
                if update_data["meta_catalog_visible"] != product.meta_catalog_visible:
                    update_data["meta_sync_status"] = MetaSyncStatus.PENDING.value
                    update_data["meta_sync_errors"] = None
            
            update_data["updated_at"] = datetime.now()
            
            # Update product in database
            stmt = (
                update(Product)
                .where(and_(Product.id == product_id, Product.merchant_id == merchant_id))
                .values(**update_data)
                .returning(Product)
            )
            result = await self.db.execute(stmt)
            updated_product_row = result.fetchone()
            
            if not updated_product_row:
                raise ValueError(f"Failed to update product: {product_id}")
            
            await self.db.commit()
            
            # Convert to Pydantic model
            updated_product = ProductDB.model_validate(updated_product_row)
            
            # Store idempotency response
            if idempotency_key:
                await self._store_idempotency_response(
                    idempotency_key, merchant_id, f"PUT /api/v1/products/{product_id}",
                    request.model_dump(exclude_none=True), updated_product.model_dump()
                )
            
            # Queue Meta catalog sync if needed
            needs_sync = (
                updated_product.meta_catalog_visible and 
                (product.meta_catalog_visible != updated_product.meta_catalog_visible or
                 any(field in update_data for field in ["title", "description", "price_kobo", "stock", "image_url"]))
            )
            
            if needs_sync:
                await self._queue_catalog_sync(product_id, "update")
            elif not updated_product.meta_catalog_visible and product.meta_catalog_visible:
                # Product was made invisible, delete from catalog
                await self._queue_catalog_sync(product_id, "delete")
            
            # Emit structured logs
            logger.info(
                "product_updated",
                extra={
                    "event_type": "product_updated",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "retailer_id": updated_product.retailer_id,
                    "updated_fields": list(update_data.keys()),
                    "idempotency_key": idempotency_key
                }
            )
            
            # Record metrics
            increment_counter("products_updated_total", tags={"merchant_id": str(merchant_id)})
            record_timer("product_update_duration_seconds", 
                        (datetime.now() - start_time).total_seconds())
            
            return updated_product
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update product: {str(e)}", extra={
                "merchant_id": str(merchant_id),
                "product_id": str(product_id),
                "idempotency_key": idempotency_key,
                "error": str(e)
            })
            raise
    
    async def delete_product(
        self,
        product_id: UUID,
        merchant_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> bool:
        """Delete product and remove from Meta catalog"""
        try:
            # Handle idempotency
            if idempotency_key:
                existing_response = await self._check_idempotency(
                    idempotency_key, merchant_id, f"DELETE /api/v1/products/{product_id}", {}
                )
                if existing_response:
                    logger.info(f"Returning idempotent response for product deletion: {idempotency_key}")
                    return existing_response.get("deleted", False)
            
            # Get existing product
            product = await self._get_product_by_id(product_id, merchant_id)
            if not product:
                raise ValueError(f"Product not found: {product_id}")
            
            # Check if product has active reservations
            if product.reserved_qty > 0:
                raise ValueError("Cannot delete product with active inventory reservations")
            
            # Delete product from database
            stmt = delete(Product).where(
                and_(Product.id == product_id, Product.merchant_id == merchant_id)
            )
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                raise ValueError(f"Failed to delete product: {product_id}")
            
            await self.db.commit()
            
            # Store idempotency response
            if idempotency_key:
                await self._store_idempotency_response(
                    idempotency_key, merchant_id, f"DELETE /api/v1/products/{product_id}",
                    {}, {"deleted": True}
                )
            
            # Queue Meta catalog sync to remove product
            if product.meta_catalog_visible:
                await self._queue_catalog_sync(product_id, "delete")
            
            # Emit structured logs
            logger.info(
                "product_deleted",
                extra={
                    "event_type": "product_deleted",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "retailer_id": product.retailer_id,
                    "idempotency_key": idempotency_key
                }
            )
            
            # Record metrics
            increment_counter("products_deleted_total", tags={"merchant_id": str(merchant_id)})
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete product: {str(e)}", extra={
                "merchant_id": str(merchant_id),
                "product_id": str(product_id),
                "idempotency_key": idempotency_key,
                "error": str(e)
            })
            raise
    
    async def get_product(self, product_id: UUID, merchant_id: UUID) -> Optional[ProductDB]:
        """Get product by ID"""
        product = await self._get_product_by_id(product_id, merchant_id)
        return product
    
    async def list_products(
        self,
        merchant_id: UUID,
        filters: ProductFilters,
        pagination: ProductPagination
    ) -> Tuple[List[ProductDB], int]:
        """List products with filtering and pagination"""
        try:
            # Build base query
            query = select(Product).where(Product.merchant_id == merchant_id)
            count_query = select(func.count(Product.id)).where(Product.merchant_id == merchant_id)
            
            # Apply filters
            filter_conditions = []
            
            if filters.status:
                filter_conditions.append(Product.status == filters.status)
            
            if filters.category_path:
                filter_conditions.append(Product.category_path.like(f"{filters.category_path}%"))
            
            if filters.meta_sync_status:
                filter_conditions.append(Product.meta_sync_status == filters.meta_sync_status.value)
            
            if filters.meta_catalog_visible is not None:
                filter_conditions.append(Product.meta_catalog_visible == filters.meta_catalog_visible)
            
            if filters.tags:
                # JSON array contains any of the specified tags
                tag_conditions = [
                    func.jsonb_exists(Product.tags, tag) for tag in filters.tags
                ]
                filter_conditions.append(or_(*tag_conditions))
            
            if filter_conditions:
                query = query.where(and_(*filter_conditions))
                count_query = count_query.where(and_(*filter_conditions))
            
            # Apply sorting
            sort_column = getattr(Product, pagination.sort_by, Product.created_at)
            if pagination.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            # Apply pagination
            offset = (pagination.page - 1) * pagination.page_size
            query = query.offset(offset).limit(pagination.page_size)
            
            # Execute queries
            products_result = await self.db.execute(query)
            count_result = await self.db.execute(count_query)
            
            products = [ProductDB.model_validate(row) for row in products_result.fetchall()]
            total_count = count_result.scalar() or 0
            
            logger.debug(f"Listed {len(products)} products for merchant {merchant_id}")
            
            return products, total_count
            
        except Exception as e:
            logger.error(f"Failed to list products: {str(e)}", extra={
                "merchant_id": str(merchant_id),
                "error": str(e)
            })
            raise
    
    async def update_inventory(
        self,
        product_id: UUID,
        merchant_id: UUID,
        stock_delta: int
    ) -> ProductDB:
        """Update product inventory atomically"""
        try:
            # Get current product with row lock
            stmt = (
                select(Product)
                .where(and_(Product.id == product_id, Product.merchant_id == merchant_id))
                .with_for_update()
            )
            result = await self.db.execute(stmt)
            product_row = result.fetchone()
            
            if not product_row:
                raise ValueError(f"Product not found: {product_id}")
            
            product = ProductDB.model_validate(product_row)
            new_stock = product.stock + stock_delta
            
            if new_stock < 0:
                raise ValueError("Stock cannot be negative")
            
            if new_stock < product.reserved_qty:
                raise ValueError("Stock cannot be less than reserved quantity")
            
            # Update inventory
            new_available_qty = new_stock - product.reserved_qty
            update_stmt = (
                update(Product)
                .where(and_(Product.id == product_id, Product.merchant_id == merchant_id))
                .values(
                    stock=new_stock,
                    available_qty=new_available_qty,
                    updated_at=datetime.now(),
                    meta_sync_status=MetaSyncStatus.PENDING.value if product.meta_catalog_visible else product.meta_sync_status
                )
                .returning(Product)
            )
            
            result = await self.db.execute(update_stmt)
            updated_product_row = result.fetchone()
            await self.db.commit()
            
            updated_product = ProductDB.model_validate(updated_product_row)
            
            # Queue Meta catalog sync if visible
            if updated_product.meta_catalog_visible:
                await self._queue_catalog_sync(product_id, "update")
            
            logger.info(
                "inventory_updated",
                extra={
                    "event_type": "inventory_updated",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "stock_delta": stock_delta,
                    "new_stock": new_stock,
                    "available_qty": new_available_qty
                }
            )
            
            return updated_product
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update inventory: {str(e)}", extra={
                "merchant_id": str(merchant_id),
                "product_id": str(product_id),
                "stock_delta": stock_delta,
                "error": str(e)
            })
            raise
    
    # Private helper methods
    
    async def _get_product_by_id(self, product_id: UUID, merchant_id: UUID) -> Optional[ProductDB]:
        """Get product by ID and merchant ID"""
        stmt = select(Product).where(
            and_(Product.id == product_id, Product.merchant_id == merchant_id)
        )
        result = await self.db.execute(stmt)
        product_row = result.fetchone()
        
        if product_row:
            return ProductDB.model_validate(product_row)
        return None
    
    async def _validate_sku_uniqueness(self, merchant_id: UUID, sku: str, exclude_id: Optional[UUID] = None):
        """Validate SKU uniqueness within merchant"""
        conditions = [Product.merchant_id == merchant_id, Product.sku == sku]
        if exclude_id:
            conditions.append(Product.id != exclude_id)
        
        stmt = select(Product.id).where(and_(*conditions))
        result = await self.db.execute(stmt)
        
        if result.fetchone():
            increment_counter("sku_duplicate_errors_total", tags={"merchant_id": str(merchant_id)})
            raise ValueError(f"SKU '{sku}' already exists for this merchant")
    
    async def _queue_catalog_sync(self, product_id: UUID, action: str):
        """Queue Meta catalog sync job"""
        try:
            # Get product and merchant info for job payload
            stmt = (
                select(Product, Merchant)
                .join(Merchant, Product.merchant_id == Merchant.id)
                .where(Product.id == product_id)
            )
            result = await self.db.execute(stmt)
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Product not found for catalog sync: {product_id}")
                return
            
            product, merchant = row
            
            # Create job payload
            payload = {
                "action": action,
                "product_id": str(product_id),
                "retailer_id": product.retailer_id,
                "merchant_meta_config": {
                    "catalog_id": "placeholder_catalog_id",  # Would come from merchant settings
                    "access_token": "encrypted_token"  # Would be encrypted in real implementation
                }
            }
            
            # Generate dedupe key
            dedupe_key = f"catalog_sync_{product_id}_{action}"
            
            # Enqueue job
            job_id = await enqueue_job(
                merchant_id=product.merchant_id,
                job_type="catalog_sync",
                payload=payload,
                dedupe_key=dedupe_key,
                max_attempts=5,
                db=self.db
            )
            
            logger.info(
                "catalog_sync_queued",
                extra={
                    "event_type": "catalog_sync_queued",
                    "merchant_id": str(product.merchant_id),
                    "product_id": str(product_id),
                    "retailer_id": product.retailer_id,
                    "action": action,
                    "job_id": str(job_id)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to queue catalog sync: {str(e)}", extra={
                "product_id": str(product_id),
                "action": action,
                "error": str(e)
            })
    
    async def _check_idempotency(
        self,
        key: str,
        merchant_id: UUID,
        endpoint: str,
        request_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for existing idempotency key"""
        request_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()
        
        stmt = select(IdempotencyKeyDB).where(
            and_(
                IdempotencyKeyDB.key == key,
                IdempotencyKeyDB.merchant_id == merchant_id,
                IdempotencyKeyDB.endpoint == endpoint,
                IdempotencyKeyDB.request_hash == request_hash
            )
        )
        result = await self.db.execute(stmt)
        idempotency_row = result.fetchone()
        
        if idempotency_row:
            idempotency_key = IdempotencyKeyDB.model_validate(idempotency_row)
            return idempotency_key.response_data
        
        return None
    
    async def _store_idempotency_response(
        self,
        key: str,
        merchant_id: UUID,
        endpoint: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any]
    ):
        """Store idempotency response"""
        request_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()
        
        idempotency_data = {
            "id": uuid4(),
            "key": key,
            "merchant_id": merchant_id,
            "endpoint": endpoint,
            "request_hash": request_hash,
            "response_data": response_data,
            "created_at": datetime.now()
        }
        
        stmt = insert(IdempotencyKeyDB).values(**idempotency_data)
        await self.db.execute(stmt)
        # Note: commit is handled by calling method