"""
Products API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.api import CreateProductRequest, UpdateProductRequest, ProductResponse, ApiResponse, ApiErrorResponse
from ..models.meta_catalog import ProductFilters, ProductPagination
from ..models.errors import ErrorCode
from ..services.product_service import ProductService
from ..dependencies.auth import get_current_user
from ..database.connection import get_db
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
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    status: Optional[str] = Query(None, description="Filter by product status"),
    category_path: Optional[str] = Query(None, description="Filter by category path"),
    meta_sync_status: Optional[str] = Query(None, description="Filter by Meta sync status"),
    meta_catalog_visible: Optional[bool] = Query(None, description="Filter by Meta catalog visibility"),
    principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of products.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **sort_by**: Sort field (default: created_at)
    - **sort_order**: Sort order asc/desc (default: desc)
    - **status**: Filter by product status
    - **category_path**: Filter by category path
    - **meta_sync_status**: Filter by Meta sync status
    - **meta_catalog_visible**: Filter by Meta catalog visibility
    """
    try:
        service = ProductService(db)
        
        # Create filters and pagination objects
        filters = ProductFilters(
            status=status,
            category_path=category_path,
            meta_sync_status=meta_sync_status,
            meta_catalog_visible=meta_catalog_visible
        )
        
        pagination = ProductPagination(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        products, total_count = await service.list_products(
            merchant_id=principal.merchant_id,
            filters=filters,
            pagination=pagination
        )
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        response_data = {
            "products": [product.model_dump() for product in products],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
        return ApiResponse(
            data=response_data,
            message=f"Retrieved {len(products)} products"
        )
        
    except Exception as e:
        logger.error(f"Failed to list products: {str(e)}", extra={
            "merchant_id": str(principal.merchant_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve products"
        )


@router.post(
    "",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        409: {"model": ApiErrorResponse, "description": "SKU already exists"}
    },
    summary="Create product",
    description="Create a new product for the current merchant"
)
async def create_product(
    request: CreateProductRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product.
    
    - **request**: Product creation data
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    try:
        service = ProductService(db)
        
        product = await service.create_product(
            merchant_id=principal.merchant_id,
            request=request,
            idempotency_key=idempotency_key
        )
        
        return ApiResponse(
            id=product.id,
            data=product.model_dump(),
            message="Product created successfully"
        )
        
    except ValueError as e:
        if "SKU" in str(e) and "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create product: {str(e)}", extra={
            "merchant_id": str(principal.merchant_id),
            "idempotency_key": idempotency_key,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
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
    principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get product by ID.
    
    - **product_id**: Product UUID
    """
    try:
        service = ProductService(db)
        
        product = await service.get_product(
            product_id=product_id,
            merchant_id=principal.merchant_id
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return ApiResponse(
            data=product.model_dump(),
            message="Product retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get product: {str(e)}", extra={
            "merchant_id": str(principal.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product"
        )


@router.put(
    "/{product_id}",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"},
        409: {"model": ApiErrorResponse, "description": "SKU already exists"}
    },
    summary="Update product",
    description="Update a specific product"
)
async def update_product(
    product_id: UUID,
    request: UpdateProductRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update product by ID.
    
    - **product_id**: Product UUID
    - **request**: Partial product data to update
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    try:
        service = ProductService(db)
        
        product = await service.update_product(
            product_id=product_id,
            merchant_id=principal.merchant_id,
            request=request,
            idempotency_key=idempotency_key
        )
        
        return ApiResponse(
            id=product_id,
            data=product.model_dump(),
            message="Product updated successfully"
        )
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "SKU" in str(e) and "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update product: {str(e)}", extra={
            "merchant_id": str(principal.merchant_id),
            "product_id": str(product_id),
            "idempotency_key": idempotency_key,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )


@router.delete(
    "/{product_id}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"},
        400: {"model": ApiErrorResponse, "description": "Cannot delete product with reservations"}
    },
    summary="Delete product",
    description="Delete a specific product"
)
async def delete_product(
    product_id: UUID,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete product by ID.
    
    - **product_id**: Product UUID
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    try:
        service = ProductService(db)
        
        deleted = await service.delete_product(
            product_id=product_id,
            merchant_id=principal.merchant_id,
            idempotency_key=idempotency_key
        )
        
        return ApiResponse(
            id=product_id,
            data={"deleted": deleted},
            message="Product deleted successfully"
        )
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "reservations" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete product: {str(e)}", extra={
            "merchant_id": str(principal.merchant_id),
            "product_id": str(product_id),
            "idempotency_key": idempotency_key,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )


@router.patch(
    "/{product_id}/inventory",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid inventory operation"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"}
    },
    summary="Update product inventory",
    description="Update product stock level atomically"
)
async def update_inventory(
    product_id: UUID,
    stock_delta: int = Query(..., description="Stock change (positive or negative)"),
    principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update product inventory atomically.
    
    - **product_id**: Product UUID
    - **stock_delta**: Stock change amount (can be negative)
    """
    try:
        service = ProductService(db)
        
        product = await service.update_inventory(
            product_id=product_id,
            merchant_id=principal.merchant_id,
            stock_delta=stock_delta
        )
        
        return ApiResponse(
            id=product_id,
            data=product.model_dump(),
            message=f"Inventory updated by {stock_delta}"
        )
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update inventory: {str(e)}", extra={
            "merchant_id": str(principal.merchant_id),
            "product_id": str(product_id),
            "stock_delta": stock_delta,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update inventory"
        )