"""
Products API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.api import CreateProductRequest, UpdateProductRequest, ProductResponse, ApiResponse, ApiErrorResponse, MetaSyncResponse, MetaSyncStatusResponse, MetaUnpublishResponse
from ..models.meta_catalog import ProductFilters, ProductPagination
from ..models.sqlalchemy_models import Product
from ..models.errors import ErrorCode
from ..services.product_service import ProductService
from ..services.meta_catalog_service import MetaSyncReasonNormalizer
from ..dependencies.auth import get_current_user, get_current_admin
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


@router.post(
    "/{product_id}/meta-sync",
    response_model=ApiResponse[MetaSyncResponse],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid product_id format"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {"model": ApiErrorResponse, "description": "Product not found"},
        409: {"model": ApiErrorResponse, "description": "Sync already in progress"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Manually trigger Meta Catalog sync",
    description="Manually enqueue Meta Catalog sync job for a specific product (admin only)"
)
async def trigger_meta_sync(
    product_id: UUID,
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger Meta Catalog sync for a product.

    This endpoint allows administrators to manually re-trigger Meta Catalog
    synchronization for a specific product. Useful when sync issues occur
    or when immediate sync is needed.

    - **product_id**: Product UUID to sync
    - **Admin access required**: Only admin users can trigger manual sync

    Returns 202 Accepted with job details for async processing.
    """
    try:
        service = ProductService(db)

        # Enqueue manual catalog sync
        job_id = await service.enqueue_manual_catalog_sync(
            product_id=product_id,
            merchant_id=admin.merchant_id,
            requested_by=admin.id
        )

        # Increment success metric
        increment_counter("sayar_manual_sync_requests_total", tags={
            "merchant_id": str(admin.merchant_id),
            "status": "success"
        })

        response_data = MetaSyncResponse(
            product_id=product_id,
            sync_status="pending",
            job_id=job_id
        )

        return ApiResponse(
            id=product_id,
            data=response_data,
            message="Meta Catalog sync job enqueued successfully"
        )

    except ValueError as e:
        error_msg = str(e)

        # Increment conflict metric for sync in progress
        if "already in progress" in error_msg:
            increment_counter("sayar_manual_sync_conflicts_total", tags={
                "merchant_id": str(admin.merchant_id)
            })
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "SYNC_IN_PROGRESS",
                    "message": "Meta Catalog sync is already in progress for this product",
                    "details": {
                        "product_id": str(product_id),
                        "current_status": "syncing"
                    }
                }
            )

        # Product not found
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Other validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    except Exception as e:
        # Increment error metric
        increment_counter("sayar_manual_sync_requests_total", tags={
            "merchant_id": str(admin.merchant_id),
            "status": "error"
        })

        logger.error(f"Failed to trigger manual sync: {str(e)}", extra={
            "merchant_id": str(admin.merchant_id),
            "product_id": str(product_id),
            "requested_by": str(admin.id),
            "error": str(e)
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger Meta Catalog sync"
        )


@router.get(
    "/{product_id}/meta-sync",
    response_model=MetaSyncStatusResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Forbidden"},
        404: {"model": ApiErrorResponse, "description": "Product not found"}
    },
    summary="Get Meta Catalog sync status",
    description="Get current Meta Catalog sync status and human-readable reason for a product"
)
async def get_meta_sync_status(
    product_id: UUID,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get Meta Catalog sync status for a product.

    Returns current sync status, human-readable reason for errors,
    and sync timing information for merchant status monitoring.

    - **product_id**: Product UUID to check status for
    - **Admin/Staff access**: Both admin and staff users can check status
    - **Merchant isolation**: Only returns status for products owned by user's merchant

    Returns status with optional reason for error cases.
    """
    try:
        # Get product with sync status fields
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.merchant_id == user.merchant_id)
        )
        result = await db.execute(stmt)
        product = result.fetchone()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Extract sync fields
        sync_status = product.meta_sync_status or "pending"
        sync_errors = product.meta_sync_errors or []
        last_synced_at = product.meta_last_synced_at
        sync_reason = product.meta_sync_reason

        # Backfill reason if missing (for legacy rows)
        if not sync_reason and sync_status == "error" and sync_errors:
            sync_reason = MetaSyncReasonNormalizer.normalize_errors(sync_errors, sync_status)

            # Persist the normalized reason for future requests
            if sync_reason:
                try:
                    from sqlalchemy import update
                    update_stmt = (
                        update(Product)
                        .where(Product.id == product_id)
                        .values(meta_sync_reason=sync_reason)
                    )
                    await db.execute(update_stmt)
                    await db.commit()
                except Exception as e:
                    # Log but don't fail the request if update fails
                    logger.warning(f"Failed to backfill sync reason: {str(e)}", extra={
                        "product_id": str(product_id),
                        "merchant_id": str(user.merchant_id)
                    })
                    await db.rollback()

        # Log status check for metrics
        logger.info(
            "meta_sync_status_checked",
            extra={
                "event_type": "meta_sync_status_checked",
                "merchant_id": str(user.merchant_id),
                "product_id": str(product_id),
                "status": sync_status,
                "has_reason": bool(sync_reason)
            }
        )

        # Increment metrics
        increment_counter("meta_sync_status_requests_total", tags={
            "merchant_id": str(user.merchant_id),
            "status": sync_status
        })

        if sync_reason:
            reason_category = MetaSyncReasonNormalizer.get_reason_category(sync_reason)
            increment_counter("meta_sync_reason_category_total", tags={
                "category": reason_category
            })

        # Build response (retry_count and next_retry_at are optional telemetry)
        response_data = MetaSyncStatusResponse(
            status=sync_status,
            reason=sync_reason,
            last_synced_at=last_synced_at,
            retry_count=None,  # Optional telemetry - set to None as per spec
            next_retry_at=None  # Optional telemetry - set to None as per spec
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Meta sync status: {str(e)}", extra={
            "merchant_id": str(user.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Meta sync status"
        )


@router.post(
    "/{product_id}/meta-unpublish",
    response_model=ApiResponse[MetaUnpublishResponse],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": ApiResponse, "description": "Unpublish job enqueued successfully"},
        400: {"model": ApiErrorResponse, "description": "Product already unpublished"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {"model": ApiErrorResponse, "description": "Product not found"},
        409: {"model": ApiErrorResponse, "description": "Sync in progress"},
        500: {"model": ApiErrorResponse, "description": "Internal server error"}
    },
    summary="Force unpublish product from Meta Catalog",
    description="Force unpublish a product from Meta Commerce Catalog (admin only)"
)
async def force_unpublish_product(
    product_id: UUID,
    admin = Depends(get_current_admin),  # Admin only
    db: AsyncSession = Depends(get_db)
):
    """
    Force unpublish a product from Meta Commerce Catalog.

    Requires admin role. Enqueues an unpublish job that will set the product's
    availability to "out of stock" and visibility to "hidden" in Meta Catalog.

    - **product_id**: UUID of the product to unpublish
    """
    try:
        service = ProductService(db)

        # Attempt to enqueue force unpublish job
        job_id = await service.enqueue_force_unpublish(
            product_id=product_id,
            merchant_id=admin.merchant_id,
            requested_by=admin.user_id
        )

        # Create response data
        response_data = MetaUnpublishResponse(
            product_id=product_id,
            action="force_unpublish",
            job_id=job_id
        )

        # Log successful enqueue
        logger.info(
            "force_unpublish_enqueued",
            extra={
                "event": "force_unpublish_enqueued",
                "merchant_id": str(admin.merchant_id),
                "product_id": str(product_id),
                "requested_by": str(admin.user_id),
                "job_id": job_id
            }
        )

        increment_counter(
            "meta_unpublish_requests_total",
            tags={"trigger": "manual", "status": "enqueued"}
        )

        return ApiResponse(
            ok=True,
            id=product_id,
            data=response_data,
            message="Meta Catalog unpublish job enqueued successfully"
        )

    except ValueError as e:
        error_message = str(e)
        logger.warning(f"Force unpublish validation error: {error_message}", extra={
            "merchant_id": str(admin.merchant_id),
            "product_id": str(product_id),
            "error": error_message
        })

        increment_counter(
            "meta_unpublish_requests_total",
            tags={"trigger": "manual", "status": "error"}
        )

        # Determine appropriate error response based on the error message
        if "not found" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        elif "already unpublished" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        elif "sync is already in progress" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Meta Catalog sync is already in progress for this product"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force unpublish product: {str(e)}", extra={
            "merchant_id": str(admin.merchant_id),
            "product_id": str(product_id),
            "error": str(e)
        })

        increment_counter(
            "meta_unpublish_requests_total",
            tags={"trigger": "manual", "status": "error"}
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue Meta unpublish job"
        )