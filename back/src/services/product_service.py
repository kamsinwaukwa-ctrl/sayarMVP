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
from ..services.meta_integration_service import MetaIntegrationService
from ..utils.outbox import enqueue_job
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_timer
from ..utils.error_handling import map_exception_to_response, create_error_response
from ..utils.product_generation import ProductFieldGenerator

logger = get_logger(__name__)

class ProductService:
    """Service class for product operations with Meta catalog sync"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.media_service = MediaService(db)
        self.meta_client = MetaCatalogClient()
        self.meta_integration_service = MetaIntegrationService(db)
        self.field_generator = ProductFieldGenerator(db)
    
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
            
            # Get merchant for field generation
            merchant = await self.field_generator.get_merchant(merchant_id)

            # 1. Default brand from merchant if missing
            brand = self.field_generator.default_brand_from_merchant(merchant.name, request.brand)

            # 2. Generate SKU if missing or validate existing
            sku = request.sku
            if not sku or not sku.strip():
                sku = await self.field_generator.generate_unique_sku(merchant_id, merchant.slug)
                increment_counter("products_created_with_auto_sku_total", tags={"merchant_id": str(merchant_id)})
            else:
                # Validate existing SKU uniqueness
                await self._validate_sku_uniqueness(merchant_id, sku)

            # 3. Generate MPN if missing
            mpn = request.mpn
            if not mpn or not mpn.strip():
                mpn = self.field_generator.generate_mpn(merchant.slug, sku)
                increment_counter("products_created_with_auto_mpn_total", tags={"merchant_id": str(merchant_id)})

            # Log auto-generation events
            if not request.brand:
                increment_counter("products_created_with_auto_brand_total", tags={"merchant_id": str(merchant_id)})
                logger.info(
                    "product_brand_defaulted",
                    extra={
                        "event_type": "product_brand_defaulted",
                        "merchant_id": str(merchant_id),
                        "brand": brand,
                        "merchant_name": merchant.name
                    }
                )

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
                "sku": sku,
                "brand": brand,
                "mpn": mpn,
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

            # Get merchant for field generation if needed
            merchant = None

            # Check SKU uniqueness if updating SKU
            if request.sku and request.sku != product.sku:
                await self._validate_sku_uniqueness(merchant_id, request.sku)

            # Never overwrite existing brand unless explicitly provided
            brand = request.brand if request.brand is not None else product.brand

            # Generate MPN if missing and we have SKU
            mpn = request.mpn
            sku = request.sku if request.sku is not None else product.sku

            if not mpn or not mpn.strip():
                if sku:
                    if not merchant:
                        merchant = await self.field_generator.get_merchant(merchant_id)
                    mpn = self.field_generator.generate_mpn(merchant.slug, sku)
                    increment_counter("products_created_with_auto_mpn_total", tags={"merchant_id": str(merchant_id)})
                    logger.info(
                        "product_mpn_generated",
                        extra={
                            "event_type": "product_mpn_generated",
                            "merchant_id": str(merchant_id),
                            "product_id": str(product_id),
                            "mpn": mpn,
                            "sku": sku
                        }
                    )
                else:
                    mpn = product.mpn

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

            # Always include resolved brand and mpn
            update_data["brand"] = brand
            update_data["mpn"] = mpn
            
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

            # Handle unpublish on status change (archived/hidden)
            if "status" in update_data:
                old_status = product.status
                new_status = updated_product.status

                # If status changed from active to archived/hidden, trigger unpublish
                if old_status == "active" and new_status in ["archived", "hidden"]:
                    await self.enqueue_unpublish_on_status_change(
                        product_id, merchant_id, old_status, new_status
                    )
            
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

    async def enqueue_manual_catalog_sync(self, product_id: UUID, merchant_id: UUID, requested_by: UUID) -> str:
        """
        Manually enqueue Meta catalog sync for a specific product

        Args:
            product_id: Product UUID
            merchant_id: Merchant UUID
            requested_by: User UUID who requested the sync

        Returns:
            Job ID for tracking

        Raises:
            ValueError: If product not found or sync already in progress
        """
        try:
            # Get product to check existence and sync status
            stmt = (
                select(Product)
                .where(and_(Product.id == product_id, Product.merchant_id == merchant_id))
            )
            result = await self.db.execute(stmt)
            product = result.fetchone()

            if not product:
                raise ValueError("Product not found")

            product_obj = ProductDB.model_validate(product)

            # Check if sync is already in progress
            if product_obj.meta_sync_status == MetaSyncStatus.SYNCING.value:
                raise ValueError("Meta Catalog sync is already in progress for this product")

            # Update sync status to pending
            update_stmt = (
                update(Product)
                .where(and_(Product.id == product_id, Product.merchant_id == merchant_id))
                .values(
                    meta_sync_status=MetaSyncStatus.PENDING.value,
                    updated_at=datetime.now()
                )
            )
            await self.db.execute(update_stmt)

            # Get merchant info for job payload
            merchant_stmt = select(Merchant).where(Merchant.id == merchant_id)
            merchant_result = await self.db.execute(merchant_stmt)
            merchant = merchant_result.fetchone()

            if not merchant:
                raise ValueError("Merchant not found")

            # Create job payload
            timestamp = datetime.now()
            payload = {
                "product_id": str(product_id),
                "merchant_id": str(merchant_id),
                "retailer_id": product_obj.retailer_id,
                "action": "manual_sync",
                "trigger": "manual",
                "requested_by": str(requested_by),
                "timestamp": timestamp.isoformat()
            }

            # Generate idempotency key with timestamp
            dedupe_key = f"catalog_sync:{merchant_id}:{product_id}:{timestamp.isoformat()}"

            # Enqueue job
            job_id = await enqueue_job(
                merchant_id=merchant_id,
                job_type="catalog_sync",
                payload=payload,
                dedupe_key=dedupe_key,
                max_attempts=5,
                delay_seconds=0  # Execute immediately for manual sync
            )

            await self.db.commit()

            logger.info(
                "manual_catalog_sync_enqueued",
                extra={
                    "event_type": "manual_catalog_sync_enqueued",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "retailer_id": product_obj.retailer_id,
                    "requested_by": str(requested_by),
                    "job_id": job_id,
                    "trigger": "manual"
                }
            )

            return job_id

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to enqueue manual catalog sync: {str(e)}", extra={
                "merchant_id": str(merchant_id),
                "product_id": str(product_id),
                "requested_by": str(requested_by),
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

    async def load_meta_credentials_for_worker(self, merchant_id: UUID):
        """Load Meta credentials for sync worker"""
        return await self.meta_integration_service.load_credentials_for_worker(merchant_id)

    async def enqueue_unpublish_on_status_change(
        self,
        product_id: UUID,
        merchant_id: UUID,
        old_status: str,
        new_status: str
    ) -> None:
        """Enqueue unpublish job when product status changes to archived/hidden"""
        try:
            # Get product details for job payload
            product = await self._get_product_by_id(product_id, merchant_id)
            if not product:
                logger.warning(f"Product not found for unpublish: {product_id}")
                return

            # Create unpublish job payload
            job_payload = {
                "type": "catalog_unpublish",
                "merchant_id": str(merchant_id),
                "product_id": str(product_id),
                "retailer_id": product.retailer_id,
                "action": "unpublish",
                "trigger": "status_change",
                "requested_by": None,
                "old_status": old_status,
                "new_status": new_status,
                "timestamp": datetime.now().isoformat()
            }

            # Generate idempotency key (no timestamp for deduplication)
            idempotency_key = f"catalog_unpublish:{merchant_id}:{product_id}:status_change"

            await enqueue_job(
                job_type="catalog_unpublish",
                payload=job_payload,
                idempotency_key=idempotency_key,
                db=self.db
            )

            # Log structured event
            logger.info(
                "product_unpublish_triggered",
                extra={
                    "event": "product_unpublish_triggered",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "trigger": "status_change",
                    "old_status": old_status,
                    "new_status": new_status,
                    "timestamp": datetime.now().isoformat()
                }
            )

            increment_counter(
                "meta_unpublish_requests_total",
                tags={"trigger": "status_change", "status": "enqueued"}
            )

        except Exception as e:
            logger.error(f"Failed to enqueue unpublish for product {product_id}: {str(e)}")
            increment_counter(
                "meta_unpublish_requests_total",
                tags={"trigger": "status_change", "status": "error"}
            )
            raise

    async def enqueue_force_unpublish(
        self,
        product_id: UUID,
        merchant_id: UUID,
        requested_by: UUID
    ) -> str:
        """Enqueue force unpublish job for admin operations"""
        try:
            # Get product details
            product = await self._get_product_by_id(product_id, merchant_id)
            if not product:
                raise ValueError(f"Product not found: {product_id}")

            # Check if product is already archived/hidden (already unpublished)
            if product.status in ["archived", "hidden"]:
                raise ValueError(f"Product is already unpublished (status: {product.status})")

            # Check if sync is in progress
            if product.meta_sync_status == "syncing":
                raise ValueError("Meta Catalog sync is already in progress for this product")

            # Create force unpublish job payload
            job_payload = {
                "type": "catalog_unpublish",
                "merchant_id": str(merchant_id),
                "product_id": str(product_id),
                "retailer_id": product.retailer_id,
                "action": "unpublish",
                "trigger": "manual",
                "requested_by": str(requested_by),
                "timestamp": datetime.now().isoformat()
            }

            # Generate unique idempotency key with timestamp for manual operations
            timestamp = int(datetime.now().timestamp())
            idempotency_key = f"catalog_unpublish:{merchant_id}:{product_id}:manual:{timestamp}"

            await enqueue_job(
                job_type="catalog_unpublish",
                payload=job_payload,
                idempotency_key=idempotency_key,
                db=self.db
            )

            # Log structured event
            logger.info(
                "product_force_unpublish_triggered",
                extra={
                    "event": "product_unpublish_triggered",
                    "merchant_id": str(merchant_id),
                    "product_id": str(product_id),
                    "trigger": "manual",
                    "requested_by": str(requested_by),
                    "timestamp": datetime.now().isoformat()
                }
            )

            increment_counter(
                "meta_unpublish_requests_total",
                tags={"trigger": "manual", "status": "enqueued"}
            )

            return idempotency_key

        except Exception as e:
            logger.error(f"Failed to enqueue force unpublish for product {product_id}: {str(e)}")
            increment_counter(
                "meta_unpublish_requests_total",
                tags={"trigger": "manual", "status": "error"}
            )
            raise