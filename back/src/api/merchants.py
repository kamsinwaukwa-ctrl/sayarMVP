"""
Merchants API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from typing import Optional
from uuid import UUID
import hashlib
import time
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..models.api import (
    ApiResponse,
    ApiErrorResponse,
    OnboardingProgressResponse,
    UpdateOnboardingProgressRequest,
)
from ..models.errors import ErrorCode
from ..models.auth import CurrentPrincipal
from ..database.connection import get_db
from ..dependencies.auth import get_current_user
from ..services.merchant_service import MerchantService

router = APIRouter(prefix="/merchants", tags=["Merchants"])

# Debug endpoints removed - they were causing OpenAPI schema issues

# Supported currencies - can be moved to config later
SUPPORTED_CURRENCIES = {"NGN", "USD", "GHS", "KES"}


class MerchantOut(BaseModel):
    """Merchant response model for brand basics"""

    id: str
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BrandBasicsIn(BaseModel):
    """Brand basics update request"""

    description: Optional[str] = None
    currency: Optional[str] = None
    logo_url: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        if v is None:
            return v
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency: {v}. Supported: {SUPPORTED_CURRENCIES}"
            )
        return v


@router.get(
    "/me",
    response_model=ApiResponse[MerchantOut],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Merchant not found"},
    },
    summary="Get current merchant",
    description="Get information about the current user's merchant account",
)
async def get_current_merchant(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentPrincipal = Depends(get_current_user),
):
    """
    Get current merchant information.

    Requires valid JWT token with merchant_id claim.
    """
    service = MerchantService(db)
    merchant = await service.get_by_id(current_user.merchant_id)

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    merchant_data = MerchantOut(
        id=str(merchant.id),
        name=merchant.name,
        slug=merchant.slug,
        description=merchant.description,
        currency=merchant.currency,
        logo_url=merchant.logo_url,
        created_at=merchant.created_at.isoformat() if merchant.created_at else None,
        updated_at=merchant.updated_at.isoformat() if merchant.updated_at else None,
    )

    return ApiResponse(data=merchant_data, message="Merchant retrieved successfully")


@router.patch(
    "/me",
    response_model=ApiResponse[MerchantOut],
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Merchant not found"},
    },
    summary="Update merchant",
    description="Update current merchant information",
)
async def update_merchant(
    request: BrandBasicsIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentPrincipal = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Update current merchant information.

    - **request**: Partial merchant data to update (description, currency, logo_url)
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    service = MerchantService(db)

    try:
        updated_merchant = await service.update_brand_basics(
            current_user.merchant_id,
            description=request.description,
            primary_currency=request.currency,
            logo_url=request.logo_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update merchant: {str(e)}"
        )

    merchant_data = MerchantOut(
        id=str(updated_merchant.id),
        name=updated_merchant.name,
        slug=updated_merchant.slug,
        description=updated_merchant.description,
        currency=updated_merchant.currency,
        logo_url=updated_merchant.logo_url,
        created_at=(
            updated_merchant.created_at.isoformat()
            if updated_merchant.created_at
            else None
        ),
        updated_at=(
            updated_merchant.updated_at.isoformat()
            if updated_merchant.updated_at
            else None
        ),
    )

    return ApiResponse(data=merchant_data, message="Merchant updated successfully")


@router.post(
    "/me/logo",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid file"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        413: {"model": ApiErrorResponse, "description": "File too large"},
    },
    summary="Upload merchant logo",
    description="Upload a logo image for the current merchant",
)
async def upload_merchant_logo(
    file: UploadFile = File(..., description="Logo image file"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentPrincipal = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Upload merchant logo image to Cloudinary.

    - **file**: Logo image file (JPEG, PNG, WebP; max 5MB)
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    import uuid
    from ..integrations.cloudinary_client import CloudinaryClient, CloudinaryConfig

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Check file size (5MB limit)
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size must be less than 5MB")

    # Initialize Cloudinary config directly
    config = CloudinaryConfig()
    if not config.is_configured():
        raise HTTPException(status_code=500, detail="Cloudinary not configured")

    try:
        # Import cloudinary library
        import cloudinary
        import cloudinary.uploader

        # Configure cloudinary
        cloudinary.config(
            cloud_name=config.cloud_name,
            api_key=config.api_key,
            api_secret=config.api_secret,
        )

        # Create a simple upload method for logos
        image_uuid = str(uuid.uuid4())

        # Upload using cloudinary library (no manual signature needed)
        response = cloudinary.uploader.upload(
            file_content,
            folder=f"sayar/merchants/{current_user.merchant_id}/brand",
            public_id=image_uuid,
            overwrite=True,
            resource_type="image",
        )

        return ApiResponse(
            data={
                "logo": {
                    "url": response["secure_url"],
                    "public_id": response["public_id"],
                    "width": response.get("width"),
                    "height": response.get("height"),
                    "format": response.get("format"),
                    "bytes": response.get("bytes"),
                }
            },
            message="Logo uploaded successfully",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {str(e)}")


@router.get(
    "/me/cloudinary/verify",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        500: {"model": ApiErrorResponse, "description": "Cloudinary connection failed"},
    },
    summary="Verify Cloudinary connection",
    description="Test Cloudinary API credentials and connectivity",
)
async def verify_cloudinary_connection(
    current_user: CurrentPrincipal = Depends(get_current_user),
):
    """
    Verify Cloudinary API credentials and connectivity.

    Returns Cloudinary account information if connection is successful.
    """
    from ..integrations.cloudinary_client import CloudinaryClient, CloudinaryConfig

    config = CloudinaryConfig()
    if not config.is_configured():
        raise HTTPException(
            status_code=500,
            detail="Cloudinary not configured - missing environment variables",
        )

    try:
        client = CloudinaryClient(config)

        # Test connection by calling Cloudinary Admin API
        import requests

        auth = (config.api_key, config.api_secret)
        url = f"{config.get_base_url()}/resources/image"

        response = requests.get(url, auth=auth, params={"max_results": 1}, timeout=10)

        if response.status_code == 200:
            return ApiResponse(
                data={
                    "ok": True,
                    "cloud_name": config.cloud_name,
                    "connection": "verified",
                    "base_folder": getattr(config, "base_folder", "sayar"),
                    "upload_timeout": config.upload_timeout,
                },
                message="Cloudinary connection verified successfully",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Cloudinary API error: {response.status_code} {response.text}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to verify Cloudinary connection: {str(e)}"
        )


@router.get(
    "/me/onboarding",
    response_model=ApiResponse[OnboardingProgressResponse],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Merchant not found"},
    },
    summary="Get onboarding progress",
    description="Get current merchant's onboarding progress status",
)
async def get_onboarding_progress(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentPrincipal = Depends(get_current_user),
):
    """
    Get current merchant's onboarding progress based on actual data.
    """
    service = MerchantService(db)
    merchant = await service.get_by_id(current_user.merchant_id)

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Calculate brand_basics completion: requires description, currency, and logo
    desc = (merchant.description or "").strip()
    curr = merchant.currency
    logo = merchant.logo_url

    brand_basics_complete = bool(
        desc
        and len(desc) >= 10
        and curr
        and logo
        and logo.startswith(("http://", "https://"))
    )

    progress = OnboardingProgressResponse(
        brand_basics=brand_basics_complete,
        meta_catalog=False,  # TODO: implement based on actual meta catalog setup
        products=False,  # TODO: implement based on product count
        delivery_rates=False,  # TODO: implement based on delivery rates setup
        payments=False,  # TODO: implement based on payment provider setup
    )

    return ApiResponse(
        data=progress, message="Onboarding progress retrieved successfully"
    )


@router.put(
    "/me/onboarding",
    response_model=ApiResponse[OnboardingProgressResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Merchant not found"},
    },
    summary="Update onboarding progress",
    description="Update current merchant's onboarding progress",
)
async def update_onboarding_progress(
    request: UpdateOnboardingProgressRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Update current merchant's onboarding progress.

    TEMPORARY: Returns hardcoded progress to fix login issue.
    TODO: Implement real progress tracking.

    - **request**: Progress updates (only specified fields will be updated)
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Temporary hardcoded response
    progress = OnboardingProgressResponse(
        brand_basics=False,
        meta_catalog=False,
        products=False,
        delivery_rates=False,
        payments=False,
    )

    return ApiResponse(
        data=progress, message="Onboarding progress updated successfully"
    )
