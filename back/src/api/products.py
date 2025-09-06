"""
Products API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional, List
from uuid import UUID

from ..models.api import CreateProductRequest, ProductResponse, ApiResponse, ApiErrorResponse, PaginationParams
from ..models.errors import ErrorCode

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
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get paginated list of products.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **sort**: Sort field and direction
    - **status**: Filter by product status
    - **category**: Filter by category
    """
    # Stub implementation - returns sample response
    sample_products = [
        {
            "id": "770e8400-e29b-41d4-a716-446655440002",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "title": "Premium Face Cream",
            "description": "Luxury anti-aging face cream with natural ingredients",
            "price_kobo": 15000,
            "stock": 100,
            "reserved_qty": 5,
            "available_qty": 95,
            "image_url": "https://example.com/images/face-cream.jpg",
            "sku": "FACE-CREAM-001",
            "status": "active",
            "retailer_id": "meta_1234567890",
            "category_path": "skincare/face/creams",
            "tags": ["premium", "anti-aging", "natural"],
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        }
    ]
    
    return ApiResponse(
        data=sample_products,
        message="Products retrieved successfully"
    )


@router.post(
    "",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="Create product",
    description="Create a new product for the current merchant"
)
async def create_product(
    request: CreateProductRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a new product.
    
    - **request**: Product creation data
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"),
        data={
            "id": "880e8400-e29b-41d4-a716-446655440003",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "title": request.title,
            "description": request.description,
            "price_kobo": request.price_kobo,
            "stock": request.stock,
            "reserved_qty": 0,
            "available_qty": request.stock,
            "image_url": None,
            "sku": request.sku,
            "status": "active",
            "retailer_id": f"meta_{UUID().hex[:10]}",
            "category_path": request.category_path,
            "tags": request.tags or [],
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        },
        message="Product created successfully"
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
async def get_product(product_id: UUID):
    """
    Get product by ID.
    
    - **product_id**: Product UUID
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        data={
            "id": product_id,
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "title": "Premium Face Cream",
            "description": "Luxury anti-aging face cream with natural ingredients",
            "price_kobo": 15000,
            "stock": 100,
            "reserved_qty": 5,
            "available_qty": 95,
            "image_url": "https://example.com/images/face-cream.jpg",
            "sku": "FACE-CREAM-001",
            "status": "active",
            "retailer_id": "meta_1234567890",
            "category_path": "skincare/face/creams",
            "tags": ["premium", "anti-aging", "natural"],
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        },
        message="Product retrieved successfully"
    )


@router.put(
    "/{product_id}",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Product not found"}
    },
    summary="Update product",
    description="Update a specific product"
)
async def update_product(
    product_id: UUID,
    request: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Update product by ID.
    
    - **product_id**: Product UUID
    - **request**: Partial product data to update
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f"),
        data={
            "id": product_id,
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "title": request.get("title", "Premium Face Cream"),
            "description": request.get("description", "Luxury anti-aging face cream with natural ingredients"),
            "price_kobo": request.get("price_kobo", 15000),
            "stock": request.get("stock", 100),
            "reserved_qty": 5,
            "available_qty": 95,
            "image_url": "https://example.com/images/face-cream.jpg",
            "sku": "FACE-CREAM-001",
            "status": "active",
            "retailer_id": "meta_1234567890",
            "category_path": "skincare/face/creams",
            "tags": ["premium", "anti-aging", "natural"],
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:05:00Z"  # Updated timestamp
        },
        message="Product updated successfully"
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Delete product by ID.
    
    - **product_id**: Product UUID
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a"),
        data={"deleted": True},
        message="Product deleted successfully"
    )