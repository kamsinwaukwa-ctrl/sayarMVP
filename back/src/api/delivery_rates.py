"""
Delivery Rates API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional, List
from uuid import UUID

from ..models.api import CreateDeliveryRateRequest, DeliveryRateResponse, ApiResponse, ApiErrorResponse
from ..models.errors import ErrorCode

router = APIRouter(prefix="/delivery-rates", tags=["Delivery Rates"])


@router.get(
    "",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="List delivery rates",
    description="Get list of delivery rates for the current merchant"
)
async def list_delivery_rates(
    active: Optional[bool] = Query(None, description="Filter by active status")
):
    """
    Get list of delivery rates.
    
    - **active**: Filter by active status
    """
    # Stub implementation - returns sample response
    sample_rates = [
        {
            "id": "880e8400-e29b-41d4-a716-446655440003",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Lagos Mainland Delivery",
            "areas_text": "Ikeja, Surulere, Yaba, Mushin",
            "price_kobo": 1500,
            "description": "Next day delivery within Lagos Mainland",
            "active": True,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        }
    ]
    
    return ApiResponse(
        data=sample_rates,
        message="Delivery rates retrieved successfully"
    )


@router.post(
    "",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="Create delivery rate",
    description="Create a new delivery rate for the current merchant"
)
async def create_delivery_rate(
    request: CreateDeliveryRateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a new delivery rate.
    
    - **request**: Delivery rate creation data
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b"),
        data={
            "id": "990e8400-e29b-41d4-a716-446655440004",
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": request.name,
            "areas_text": request.areas_text,
            "price_kobo": request.price_kobo,
            "description": request.description,
            "active": True,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        },
        message="Delivery rate created successfully"
    )


@router.put(
    "/{rate_id}",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Delivery rate not found"}
    },
    summary="Update delivery rate",
    description="Update a specific delivery rate"
)
async def update_delivery_rate(
    rate_id: UUID,
    request: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Update delivery rate by ID.
    
    - **rate_id**: Delivery rate UUID
    - **request**: Partial delivery rate data to update
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c"),
        data={
            "id": rate_id,
            "merchant_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": request.get("name", "Lagos Mainland Delivery"),
            "areas_text": request.get("areas_text", "Ikeja, Surulere, Yaba, Mushin"),
            "price_kobo": request.get("price_kobo", 1500),
            "description": request.get("description", "Next day delivery within Lagos Mainland"),
            "active": request.get("active", True),
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:05:00Z"  # Updated timestamp
        },
        message="Delivery rate updated successfully"
    )


@router.delete(
    "/{rate_id}",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Delivery rate not found"}
    },
    summary="Delete delivery rate",
    description="Delete a specific delivery rate"
)
async def delete_delivery_rate(
    rate_id: UUID,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Delete delivery rate by ID.
    
    - **rate_id**: Delivery rate UUID
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d"),
        data={"deleted": True},
        message="Delivery rate deleted successfully"
    )