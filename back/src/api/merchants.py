"""
Merchants API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from typing import Optional
from uuid import UUID

from ..models.api import MerchantResponse, ApiResponse, ApiErrorResponse
from ..models.errors import ErrorCode

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get(
    "/me",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Merchant not found"}
    },
    summary="Get current merchant",
    description="Get information about the current user's merchant account"
)
async def get_current_merchant():
    """
    Get current merchant information.
    
    Requires valid JWT token with merchant_id claim.
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        data={
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Awesome Beauty Store",
            "slug": "awesome-beauty-store",
            "whatsapp_phone_e164": "+2341234567890",
            "logo_url": "https://example.com/logos/awesome-beauty.jpg",
            "description": "Premium beauty products store",
            "currency": "NGN",
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z"
        },
        message="Merchant retrieved successfully"
    )


@router.patch(
    "/me",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Merchant not found"}
    },
    summary="Update merchant",
    description="Update current merchant information"
)
async def update_merchant(
    request: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Update current merchant information.
    
    - **request**: Partial merchant data to update
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("9e0f1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d"),
        data={
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "name": request.get("name", "Awesome Beauty Store"),
            "slug": "awesome-beauty-store",
            "whatsapp_phone_e164": "+2341234567890",
            "logo_url": "https://example.com/logos/awesome-beauty.jpg",
            "description": "Premium beauty products store",
            "currency": "NGN",
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:05:00Z"  # Updated timestamp
        },
        message="Merchant updated successfully"
    )


@router.post(
    "/me/logo",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid file"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        413: {"model": ApiErrorResponse, "description": "File too large"}
    },
    summary="Upload merchant logo",
    description="Upload a logo image for the current merchant"
)
async def upload_merchant_logo(
    file: UploadFile = File(..., description="Logo image file"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Upload merchant logo image.
    
    - **file**: Logo image file (JPEG, PNG, WebP; max 5MB)
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Stub implementation - returns sample response
    return ApiResponse(
        id=UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"),
        data={
            "logo_url": "https://example.com/logos/new-logo.jpg",
            "message": "Logo uploaded successfully"
        },
        message="Logo uploaded successfully"
    )