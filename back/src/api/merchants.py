"""
Merchants API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from typing import Optional, Annotated
from uuid import UUID
import hashlib
import time
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

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
from ..services.meta_integration_service import MetaIntegrationService
from ..services.delivery_rates_service import DeliveryRatesService
from ..services.payment_provider_service import PaymentProviderService
from ..models.meta_integrations import MetaIntegrationStatus

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

    # Calculate meta_catalog completion from meta_integrations table
    meta_service = MetaIntegrationService(db)
    meta_integration = await meta_service._get_integration_by_merchant(current_user.merchant_id)

    # Meta catalog is complete if catalog_id is set (regardless of verification status)
    meta_catalog_complete = bool(meta_integration and meta_integration.catalog_id)

    # Calculate WhatsApp completion from meta_integrations table
    whatsapp_complete = bool(
        meta_integration
        and meta_integration.waba_id
        and meta_integration.app_id
        and meta_integration.system_user_token_encrypted
    )

    # Check if merchant has at least one active delivery rate
    try:
        delivery_rates_service = DeliveryRatesService(db)
        delivery_rates_list = await delivery_rates_service.list_rates(
            merchant_id=current_user.merchant_id,
            active_only=True
        )
        delivery_rates_complete = len(delivery_rates_list) > 0
    except Exception as e:
        # If there's an error checking delivery rates, default to False
        print(f"Error checking delivery rates completion: {e}")
        delivery_rates_complete = False

    # Check if merchant has at least one payment provider (regardless of active status for onboarding)
    try:
        # For onboarding progress, check if ANY payment provider records exist
        from ..models.sqlalchemy_models import PaymentProviderConfig
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == current_user.merchant_id
        )
        result = await db.execute(stmt)
        all_payment_providers = result.scalars().all()

        print(f"DEBUG: Found {len(all_payment_providers)} payment provider records for merchant {current_user.merchant_id}")
        for i, provider in enumerate(all_payment_providers):
            print(f"DEBUG: Provider {i}: type={provider.provider_type}, status={provider.verification_status}, active={provider.active}")

        # Payment setup is complete if merchant has at least one payment provider record
        payments_complete = len(all_payment_providers) > 0
        print(f"DEBUG: payments_complete = {payments_complete}")
    except Exception as e:
        print(f"Error checking payment provider completion: {e}")
        payments_complete = False

    progress = OnboardingProgressResponse(
        brand_basics=brand_basics_complete,
        meta_catalog=meta_catalog_complete,
        whatsapp=whatsapp_complete,
        delivery_rates=delivery_rates_complete,
        payments=payments_complete,
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
    current_user: CurrentPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Update current merchant's onboarding progress.

    Note: Currently this endpoint returns actual status rather than accepting updates,
    as progress is determined by database state, not manual flags.

    - **request**: Progress updates (currently ignored as status is auto-determined)
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    # Return actual progress status (same logic as GET endpoint)
    # In the future, this could accept manual overrides for specific steps

    # Get merchant service and check brand basics completion
    merchant_service = MerchantService(db)
    merchant = await merchant_service.get_merchant_by_id(current_user.merchant_id)

    brand_basics_complete = (
        merchant
        and merchant.description
        and merchant.logo_url
        and merchant.currency
    )

    # Check Meta catalog integration status
    meta_integration_service = MetaIntegrationService(db)
    meta_integration = await meta_integration_service.get_integration(
        current_user.merchant_id
    )

    meta_catalog_complete = (
        meta_integration
        and meta_integration.status == MetaIntegrationStatus.ACTIVE
        and meta_integration.catalog_id
        and meta_integration.app_id
        and meta_integration.system_user_token_encrypted
    )

    whatsapp_complete = (
        meta_integration
        and meta_integration.status == MetaIntegrationStatus.ACTIVE
        and meta_integration.phone_number_id
        and meta_integration.whatsapp_access_token_encrypted
        and meta_integration.app_id
        and meta_integration.system_user_token_encrypted
    )

    # Check if merchant has at least one active delivery rate
    try:
        delivery_rates_service = DeliveryRatesService(db)
        delivery_rates_list = await delivery_rates_service.list_rates(
            merchant_id=current_user.merchant_id,
            active_only=True
        )
        delivery_rates_complete = len(delivery_rates_list) > 0
    except Exception as e:
        # If there's an error checking delivery rates, default to False
        print(f"Error checking delivery rates completion: {e}")
        delivery_rates_complete = False

    # Check if merchant has at least one payment provider (regardless of active status for onboarding)
    try:
        # For onboarding progress, check if ANY payment provider records exist
        from ..models.sqlalchemy_models import PaymentProviderConfig
        stmt = select(PaymentProviderConfig).where(
            PaymentProviderConfig.merchant_id == current_user.merchant_id
        )
        result = await db.execute(stmt)
        all_payment_providers = result.scalars().all()

        print(f"DEBUG: Found {len(all_payment_providers)} payment provider records for merchant {current_user.merchant_id}")
        for i, provider in enumerate(all_payment_providers):
            print(f"DEBUG: Provider {i}: type={provider.provider_type}, status={provider.verification_status}, active={provider.active}")

        # Payment setup is complete if merchant has at least one payment provider record
        payments_complete = len(all_payment_providers) > 0
        print(f"DEBUG: payments_complete = {payments_complete}")
    except Exception as e:
        print(f"Error checking payment provider completion: {e}")
        payments_complete = False

    progress = OnboardingProgressResponse(
        brand_basics=brand_basics_complete,
        meta_catalog=meta_catalog_complete,
        whatsapp=whatsapp_complete,
        delivery_rates=delivery_rates_complete,
        payments=payments_complete,
    )

    return ApiResponse(
        data=progress, message="Onboarding progress updated successfully"
    )
