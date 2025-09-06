"""
Discounts API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional, List
from uuid import UUID

from ..models.api import ValidateDiscountRequest, DiscountValidationResponse, ApiResponse, ApiErrorResponse
from ..models.errors import ErrorCode

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.get(
    "",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="List discounts",
    description="Get list of discounts for the current merchant"
)
async def list_discounts(
    status: Optional[str] = Query(None, description="Filter by discount status"),
    active: Optional[bool] = Query(None, description="Filter by active status")
):
    """
    Get list of discounts.
    
    - **status**: Filter by discount status
    - **active**: Filter by active status
    """
    # Stub implementation - returns sample response
    sample_discounts = [
        {
            "id": "aa0e8400-e29b-41d4-a716-446655440005",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "code": "SUMMER20",
            "type": "percent",
            "value_bp": 2000,
            "amount_kobo": None,
            "max_discount_kobo": 5000,
            "min_subtotal_kobo": 10000,
            "starts_at": "2025-06-01T00:00:00Z",
            "expires_at": "2025-08-31T23:59:59Z",
            "usage_limit_total": 1000,
            "usage_limit_per_customer": 1,
            "times_redeemed": 150,
            "status": "active",
            "stackable": False,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        }
    ]
    
    return ApiResponse(
        data=sample_discounts,
        message="Discounts retrieved successfully"
    )


@router.post(
    "",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="Create discount",
    description="Create a new discount for the current merchant"
)
async def create_discount(
    request: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a new discount.
    
    - **request**: Discount creation data
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e"),
        data={
            "id": "bb0e8400-e29b-41d4-a716-446655440006",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "code": request.get("code", "WINTER15"),
            "type": request.get("type", "percent"),
            "value_bp": request.get("value_bp", 1500),
            "amount_kobo": request.get("amount_kobo"),
            "max_discount_kobo": request.get("max_discount_kobo", 3000),
            "min_subtotal_kobo": request.get("min_subtotal_kobo", 5000),
            "starts_at": request.get("starts_at"),
            "expires_at": request.get("expires_at"),
            "usage_limit_total": request.get("usage_limit_total", 500),
            "usage_limit_per_customer": request.get("usage_limit_per_customer", 1),
            "times_redeemed": 0,
            "status": "active",
            "stackable": request.get("stackable", False),
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        },
        message="Discount created successfully"
    )


@router.post(
    "/validate",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="Validate discount",
    description="Validate a discount code for an order"
)
async def validate_discount(request: ValidateDiscountRequest):
    """
    Validate a discount code.
    
    - **request**: Discount validation request
    """
    # Stub implementation - returns sample response
    if request.code == "SUMMER20":
        validation_result = {
            "valid": True,
            "discount_kobo": 2000,  # 20% of 10000 kobo
            "reason": None
        }
    else:
        validation_result = {
            "valid": False,
            "discount_kobo": None,
            "reason": "Invalid discount code"
        }
    
    return ApiResponse(
        data=validation_result,
        message="Discount validation completed"
    )