"""
Products API endpoints with OpenAPI documentation and Meta catalog integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID

from ..database.connection import get_db
from ..dependencies.auth import get_current_user
from ..models.api import CreateProductRequest, ProductResponse, ApiResponse, ApiErrorResponse, PaginationParams
from ..models.database import ProductDB, UserDB
from ..models.meta_catalog import ProductSyncStatus, UpdateProductSyncRequest
from ..models.errors import ErrorCode
from ..services.product_service import ProductService
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter

logger = get_logger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="List products",
    description="Get paginated list of products for the current merchant"
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: Optional[str] = Query(None, description="Sort field and direction (e.g., 'created_at:desc')"),
    status: Optional[str] = Query(None, description="Filter by product status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title, description, or SKU"),
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of products.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **sort**: Sort field and direction
    - **status**: Filter by product status
    - **category**: Filter by category
    - **search**: Search in title, description, or SKU
    """
    logger.info("Listing products", extra={
        "event_type": "products_list_start",
        "merchant_id": str(current_user.merchant_id),
        "user_id": str(current_user.id),
        "page": page,
        "page_size": page_size
    })
    
    try:
        product_service = ProductService(db)
        
        products, total_count = await product_service.list_products(
            merchant_id=current_user.merchant_id,
            page=page,
            page_size=page_size,
            status_filter=status,
            search=search,
            category=category,
            sort=sort
        )
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
        
        logger.info("Products listed successfully", extra={
            "event_type": "products_listed",
            "merchant_id": str(current_user.merchant_id),
            "product_count": len(products),
            "total_count": total_count
        })
        
        increment_counter("products_list_requests_total", {
            "merchant_id": str(current_user.merchant_id)
        })
        
        return ApiResponse(
            data={
                "products": [product.dict() for product in products],
                "pagination": pagination
            },
            message="Products retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error listing products", extra={
            "event_type": "products_list_error",
            "merchant_id": str(current_user.merchant_id),
            "error": str(e)
        })
        raise


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        409: {"model": ApiErrorResponse, "description": "Conflict - SKU already exists"}
    },
    summary="Create product",
    description="Create a new product for the current merchant"
)
async def create_product(
    request: CreateProductRequest,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a new product with Meta catalog integration.
    
    - **request**: Product creation data
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    logger.info("Creating product", extra={
        "event_type": "product_create_start",
        "merchant_id": str(current_user.merchant_id),
        "user_id": str(current_user.id),
        "sku": request.sku,
        "idempotency_key": idempotency_key
    })
    
    try:
        product_service = ProductService(db)
        
        product = await product_service.create_product(
            merchant_id=current_user.merchant_id,
            product_data=request,
            idempotency_key=idempotency_key
        )
        
        logger.info("Product created successfully", extra={
            "event_type": "product_created",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product.id),
            "sku": product.sku
        })
        
        return ApiResponse(
            id=product.id,
            data=product.dict(),
            message="Product created successfully"
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions from service layer
    except Exception as e:
        logger.error("Unexpected error creating product", extra={
            "event_type": "product_create_error",
            "merchant_id": str(current_user.merchant_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating product"
        )


@router.get(
    "/{product_id}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"}
    },
    summary="Get product",
    description="Get a specific product by ID"
)
async def get_product(
    product_id: UUID,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get product by ID with tenant isolation.
    
    - **product_id**: Product UUID
    """
    logger.info("Getting product", extra={
        "event_type": "product_get_start",
        "merchant_id": str(current_user.merchant_id),
        "product_id": str(product_id)
    })
    
    try:
        product_service = ProductService(db)
        
        product = await product_service.get_product(
            merchant_id=current_user.merchant_id,
            product_id=product_id
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        logger.info("Product retrieved successfully", extra={
            "event_type": "product_retrieved",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id)
        })
        
        return ApiResponse(
            data=product.dict(),
            message="Product retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving product", extra={
            "event_type": "product_get_error",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving product"
        )


@router.put(
    "/{product_id}",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"},
        409: {"model": ApiErrorResponse, "description": "Conflict - SKU already exists"}
    },
    summary="Update product",
    description="Update a specific product"
)
async def update_product(
    product_id: UUID,
    request: Dict[str, Any],
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Update product by ID with Meta catalog sync.
    
    - **product_id**: Product UUID
    - **request**: Partial product data to update
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    logger.info("Updating product", extra={
        "event_type": "product_update_start",
        "merchant_id": str(current_user.merchant_id),
        "product_id": str(product_id),
        "idempotency_key": idempotency_key
    })
    
    try:
        product_service = ProductService(db)
        
        # Validate that only allowed fields are being updated
        allowed_fields = {
            "title", "description", "price_kobo", "stock", "sku", 
            "status", "category_path", "tags", "image_url"
        }
        invalid_fields = set(request.keys()) - allowed_fields
        if invalid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid fields: {', '.join(invalid_fields)}"
            )
        
        product = await product_service.update_product(
            merchant_id=current_user.merchant_id,
            product_id=product_id,
            update_data=request,
            idempotency_key=idempotency_key
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        logger.info("Product updated successfully", extra={
            "event_type": "product_updated",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id)
        })
        
        return ApiResponse(
            id=product_id,
            data=product.dict(),
            message="Product updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating product", extra={
            "event_type": "product_update_error",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error updating product"
        )


@router.delete(
    "/{product_id}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"}
    },
    summary="Delete product",
    description="Delete a specific product"
)
async def delete_product(
    product_id: UUID,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Delete product by ID with Meta catalog cleanup.
    
    - **product_id**: Product UUID
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    logger.info("Deleting product", extra={
        "event_type": "product_delete_start",
        "merchant_id": str(current_user.merchant_id),
        "product_id": str(product_id),
        "idempotency_key": idempotency_key
    })
    
    try:
        product_service = ProductService(db)
        
        deleted = await product_service.delete_product(
            merchant_id=current_user.merchant_id,
            product_id=product_id,
            idempotency_key=idempotency_key
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        logger.info("Product deleted successfully", extra={
            "event_type": "product_deleted",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id)
        })
        
        return ApiResponse(
            id=product_id,
            data={"deleted": True},
            message="Product deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting product", extra={
            "event_type": "product_delete_error",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting product"
        )


# Additional endpoints for Meta catalog integration

@router.get(
    "/{product_id}/sync-status",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"}
    },
    summary="Get product sync status",
    description="Get Meta catalog synchronization status for a product"
)
async def get_product_sync_status(
    product_id: UUID,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get Meta catalog sync status for a product.
    
    - **product_id**: Product UUID
    """
    try:
        product_service = ProductService(db)
        
        sync_status = await product_service.get_sync_status(
            merchant_id=current_user.merchant_id,
            product_id=product_id
        )
        
        if not sync_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return ApiResponse(
            data=sync_status.dict(),
            message="Sync status retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting sync status", extra={
            "event_type": "product_sync_status_error",
            "merchant_id": str(current_user.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting sync status"
        )