"""
Product Images API endpoints for Cloudinary integration
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from ..database import get_db
from ..auth import get_current_merchant
from ..models.sqlalchemy_models import Merchant
from ..models.api import (
    ApiResponse,
    CloudinaryHealthResponse,
    ProductImageResponse,
    ProductImageUploadRequest,
    SetPrimaryImageResponse,
    CloudinaryWebhookPayload
)
from ..models.cloudinary import (
    ProductImageWithVariantsResponse,
    UploadWithPresetsRequest,
    PresetProfile
)
from ..models.errors import APIError, ErrorCode, NotFoundError
from ..services.cloudinary_service import CloudinaryService

router = APIRouter()


@router.get(
    "/integrations/cloudinary/health",
    response_model=ApiResponse[CloudinaryHealthResponse],
    summary="Check Cloudinary platform health",
    description="Verify that platform Cloudinary credentials are configured and working"
)
async def cloudinary_health_check(
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Check Cloudinary platform health
    Verifies environment variables and API connectivity
    """
    try:
        service = CloudinaryService(db)
        health_data = service.health_check()

        if not health_data["configured"]:
            raise HTTPException(
                status_code=503,
                detail={
                    "ok": False,
                    "error": {
                        "code": "CLOUDINARY_NOT_CONFIGURED",
                        "message": "Cloudinary platform credentials not configured",
                        "details": {}
                    }
                }
            )

        return ApiResponse(
            data=CloudinaryHealthResponse(**health_data),
            message="Cloudinary platform is healthy"
        )

    except APIError as e:
        if e.code == ErrorCode.CLOUDINARY_HEALTHCHECK_FAILED:
            raise HTTPException(
                status_code=503,
                detail={
                    "ok": False,
                    "error": {
                        "code": "CLOUDINARY_HEALTHCHECK_FAILED",
                        "message": e.message,
                        "details": {}
                    }
                }
            )
        raise


@router.post(
    "/products/{product_id}/images",
    response_model=ApiResponse[ProductImageResponse],
    status_code=201,
    summary="Upload product image",
    description="Upload image to Cloudinary with automatic transformations"
)
async def upload_product_image(
    product_id: UUID,
    request: Request,
    image: UploadFile = File(..., description="Image file (PNG, JPG, WEBP, max 5MB)"),
    is_primary: bool = Form(False, description="Set as primary image"),
    alt_text: Optional[str] = Form(None, description="Alternative text for accessibility"),
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Upload product image to Cloudinary
    - Validates file size and format
    - Applies transformation presets (main + thumbnail)
    - Saves metadata to database
    - Triggers Meta catalog sync if primary image
    """
    try:
        # Read file content
        file_content = await image.read()

        # Create webhook URL for this deployment
        webhook_url = f"{request.base_url}api/v1/webhooks/cloudinary"

        service = CloudinaryService(db)
        result = service.upload_product_image(
            product_id=product_id,
            merchant_id=merchant.id,
            file_content=file_content,
            filename=image.filename or "upload",
            is_primary=is_primary,
            alt_text=alt_text,
            webhook_url=webhook_url
        )

        return ApiResponse(
            data=result,
            message="Image uploaded successfully"
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "ok": False,
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": str(e),
                    "details": {}
                }
            }
        )
    except APIError as e:
        status_code = 400
        if e.code in [ErrorCode.IMAGE_TOO_LARGE]:
            status_code = 413
        elif e.code in [ErrorCode.CLOUDINARY_UPLOAD_FAILED]:
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail={
                "ok": False,
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": {}
                }
            }
        )


@router.post(
    "/products/{product_id}/images/with-presets",
    response_model=ApiResponse[ProductImageWithVariantsResponse],
    status_code=201,
    summary="Upload image with preset transformations",
    description="Upload image to Cloudinary with preset-based transformations and variants"
)
async def upload_product_image_with_presets(
    product_id: UUID,
    request: Request,
    image: UploadFile = File(..., description="Image file (PNG, JPG, WEBP, max 5MB)"),
    is_primary: bool = Form(False, description="Set as primary image"),
    alt_text: Optional[str] = Form(None, description="Alternative text for accessibility"),
    preset_profile: PresetProfile = Form(PresetProfile.STANDARD, description="Preset profile to use"),
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Upload product image with preset-based transformations
    - Validates file size and format
    - Applies preset profile transformations (multiple variants)
    - Saves enhanced metadata to database
    - Triggers Meta catalog sync if primary image (using main variant URL)
    """
    try:
        # Read file content
        file_content = await image.read()

        # Create webhook URL for this deployment
        webhook_url = f"{request.base_url}api/v1/webhooks/cloudinary"

        # Create upload request
        upload_request = UploadWithPresetsRequest(
            is_primary=is_primary,
            alt_text=alt_text,
            preset_profile=preset_profile
        )

        service = CloudinaryService(db)
        result = service.upload_product_image_with_presets(
            product_id=product_id,
            merchant_id=merchant.id,
            file_content=file_content,
            filename=image.filename or "upload",
            request=upload_request,
            webhook_url=webhook_url
        )

        return ApiResponse(
            data=result,
            message=f"Image uploaded successfully with {preset_profile.value} preset profile"
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "ok": False,
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": str(e),
                    "details": {}
                }
            }
        )
    except APIError as e:
        # Map APIError codes to HTTP status codes
        status_code = 400
        if e.code in [ErrorCode.CLOUDINARY_NOT_CONFIGURED]:
            status_code = 503
        elif e.code in [ErrorCode.CLOUDINARY_UPLOAD_FAILED]:
            status_code = 502

        raise HTTPException(
            status_code=status_code,
            detail={
                "ok": False,
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": {}
                }
            }
        )


@router.delete(
    "/products/{product_id}/images/{image_id}",
    status_code=204,
    summary="Delete product image",
    description="Delete image from both database and Cloudinary"
)
async def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Delete product image
    - Removes from Cloudinary storage
    - Deletes database record
    - Clears primary image reference if applicable
    - Triggers Meta catalog sync if primary image
    """
    try:
        service = CloudinaryService(db)
        service.delete_product_image(
            image_id=image_id,
            merchant_id=merchant.id
        )

        return JSONResponse(content=None, status_code=204)

    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "ok": False,
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": str(e),
                    "details": {}
                }
            }
        )
    except APIError as e:
        status_code = 502 if e.code == ErrorCode.CLOUDINARY_DELETE_FAILED else 400
        raise HTTPException(
            status_code=status_code,
            detail={
                "ok": False,
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": {}
                }
            }
        )


@router.patch(
    "/products/{product_id}/images/{image_id}/primary",
    response_model=ApiResponse[SetPrimaryImageResponse],
    summary="Set primary image",
    description="Set an image as the primary image for a product"
)
async def set_primary_image(
    product_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Set image as primary for product
    - Unsets any existing primary image
    - Updates product primary_image_id
    - Triggers Meta catalog sync with new image URL
    """
    try:
        service = CloudinaryService(db)
        result = service.set_primary_image(
            image_id=image_id,
            product_id=product_id,
            merchant_id=merchant.id
        )

        return ApiResponse(
            data=result,
            message="Primary image updated successfully"
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "ok": False,
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": str(e),
                    "details": {}
                }
            }
        )


@router.get(
    "/products/{product_id}/images",
    response_model=ApiResponse[List[ProductImageResponse]],
    summary="Get product images",
    description="List all images for a product"
)
async def get_product_images(
    product_id: UUID,
    db: Session = Depends(get_db),
    merchant: Merchant = Depends(get_current_merchant)
):
    """
    Get all images for a product
    Returns images sorted by primary status then creation date
    """
    try:
        service = CloudinaryService(db)
        images = service.get_product_images(
            product_id=product_id,
            merchant_id=merchant.id
        )

        return ApiResponse(
            data=images,
            message=f"Found {len(images)} images"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve product images",
                    "details": {}
                }
            }
        )


@router.post(
    "/webhooks/cloudinary",
    summary="Cloudinary webhook",
    description="Process Cloudinary webhook callbacks for image metadata updates"
)
async def cloudinary_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Process Cloudinary webhook
    - Verifies webhook signature
    - Updates image metadata in database
    - Triggers catalog sync for completed primary images
    """
    try:
        # Get raw body and headers
        body = await request.body()
        signature = request.headers.get("X-Cld-Signature", "")
        timestamp = request.headers.get("X-Cld-Timestamp", "")

        if not signature or not timestamp:
            raise HTTPException(
                status_code=422,
                detail={
                    "ok": False,
                    "error": {
                        "code": "WEBHOOK_SIGNATURE_INVALID",
                        "message": "Missing required webhook headers",
                        "details": {}
                    }
                }
            )

        # Parse JSON payload
        import json
        try:
            payload_data = json.loads(body.decode())
            payload = CloudinaryWebhookPayload(**payload_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "ok": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Invalid webhook payload: {str(e)}",
                        "details": {}
                    }
                }
            )

        # Process webhook
        service = CloudinaryService(db)
        result = service.process_webhook(
            payload=payload,
            signature=signature,
            timestamp=timestamp,
            raw_body=body
        )

        return JSONResponse(content=result, status_code=200)

    except APIError as e:
        if e.code == ErrorCode.WEBHOOK_SIGNATURE_INVALID:
            raise HTTPException(
                status_code=422,
                detail={
                    "ok": False,
                    "error": {
                        "code": e.code.value,
                        "message": e.message,
                        "details": {}
                    }
                }
            )
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": {}
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to process webhook",
                    "details": {}
                }
            }
        )