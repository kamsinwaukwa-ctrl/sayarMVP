"""
Discounts API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from typing import Optional, List, Annotated
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.api import (
    CreateDiscountRequest,
    UpdateDiscountRequest,
    DiscountResponse,
    ValidateDiscountRequest,
    DiscountValidationResponse,
    ApiResponse,
    ApiErrorResponse,
)
from ..models.errors import ErrorCode
from ..database.connection import get_db
from ..dependencies.auth import CurrentUser, CurrentAdmin
from ..services.discounts_service import DiscountsService, DiscountError
from ..utils.logger import log

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.get(
    "",
    response_model=ApiResponse[List[DiscountResponse]],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="List discounts",
    description="Get list of discounts for the current merchant with optional filtering",
)
async def list_discounts(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = Query(
        None, description="Filter by status (active, paused, expired)"
    ),
    active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """
    Get list of discounts for the authenticated merchant.

    **Access**: Admin and staff users can list discounts

    **Query Parameters**:
    - **status**: Filter by discount status ('active', 'paused', 'expired')
    - **active**: Filter by active status (true/false)

    **Returns**: List of discount objects with full details
    """
    try:
        service = DiscountsService(db)
        discounts = await service.list_discounts(
            merchant_id=current_user.merchant_id, status=status, active_only=active
        )

        return ApiResponse(
            ok=True, data=discounts, message=f"Retrieved {len(discounts)} discounts"
        )

    except DiscountError as e:
        log.error(
            "Failed to list discounts",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_discounts_list_error",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve discounts",
        )

    except Exception as e:
        log.error(
            "Unexpected error listing discounts",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_discounts_list_unexpected_error",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post(
    "",
    response_model=ApiResponse[DiscountResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Forbidden - admin required"},
        409: {"model": ApiErrorResponse, "description": "Duplicate discount code"},
    },
    summary="Create discount",
    description="Create a new discount code for the current merchant",
)
async def create_discount(
    discount_data: CreateDiscountRequest,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Create a new discount code.

    **Access**: Admin users only

    **Request Body**: Complete discount configuration including:
    - **code**: Unique discount code (will be normalized to uppercase)
    - **type**: 'percent' or 'fixed'
    - **value_bp**: Percentage in basis points (for percent discounts)
    - **amount_kobo**: Fixed amount in kobo (for fixed discounts)
    - **min_subtotal_kobo**: Minimum order amount required
    - **usage_limit_total**: Total usage limit (optional)
    - **usage_limit_per_customer**: Per-customer usage limit (optional)
    - **starts_at**: Discount start time (optional)
    - **expires_at**: Discount expiry time (optional)

    **Headers**:
    - **Idempotency-Key**: Optional header for idempotent operations

    **Returns**: Created discount object with generated ID
    """
    try:
        service = DiscountsService(db)
        discount = await service.create_discount(
            merchant_id=current_admin.merchant_id,
            discount_data=discount_data,
            idempotency_key=idempotency_key,
        )

        return ApiResponse(
            ok=True,
            id=discount.id,
            data=discount,
            message=f"Discount '{discount.code}' created successfully",
        )

    except DiscountError as e:
        error_msg = str(e)

        if "already exists" in error_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        elif any(
            word in error_msg.lower()
            for word in ["required", "invalid", "must be", "cannot"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create discount",
            )

    except Exception as e:
        log.error(
            "Unexpected error creating discount",
            extra={
                "merchant_id": str(current_admin.merchant_id),
                "code": discount_data.code,
                "error": str(e),
                "event_type": "api_discount_create_unexpected_error",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.put(
    "/{discount_id}",
    response_model=ApiResponse[DiscountResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Forbidden - admin required"},
        404: {"model": ApiErrorResponse, "description": "Discount not found"},
    },
    summary="Update discount",
    description="Update an existing discount (status, expiry, usage limits)",
)
async def update_discount(
    discount_id: UUID,
    update_data: UpdateDiscountRequest,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing discount.

    **Access**: Admin users only

    **Path Parameters**:
    - **discount_id**: UUID of the discount to update

    **Request Body**: Fields to update:
    - **status**: Change status to 'active' or 'paused'
    - **expires_at**: Update expiry date
    - **usage_limit_total**: Update total usage limit
    - **usage_limit_per_customer**: Update per-customer limit

    **Returns**: Updated discount object
    """
    try:
        service = DiscountsService(db)
        discount = await service.update_discount(
            merchant_id=current_admin.merchant_id,
            discount_id=discount_id,
            update_data=update_data,
        )

        return ApiResponse(
            ok=True,
            data=discount,
            message=f"Discount '{discount.code}' updated successfully",
        )

    except DiscountError as e:
        error_msg = str(e)

        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        elif any(
            word in error_msg.lower() for word in ["invalid", "must be", "cannot"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update discount",
            )

    except Exception as e:
        log.error(
            "Unexpected error updating discount",
            extra={
                "merchant_id": str(current_admin.merchant_id),
                "discount_id": str(discount_id),
                "error": str(e),
                "event_type": "api_discount_update_unexpected_error",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.delete(
    "/{discount_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Forbidden - admin required"},
        404: {"model": ApiErrorResponse, "description": "Discount not found"},
    },
    summary="Delete discount",
    description="Delete a discount permanently",
)
async def delete_discount(
    discount_id: UUID,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a discount permanently.

    **Access**: Admin users only

    **Path Parameters**:
    - **discount_id**: UUID of the discount to delete

    **Returns**: 204 No Content on success
    """
    try:
        service = DiscountsService(db)
        deleted = await service.delete_discount(
            merchant_id=current_admin.merchant_id, discount_id=discount_id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount with ID {discount_id} not found",
            )

        # Return 204 No Content (no response body)

    except HTTPException:
        raise
    except DiscountError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete discount",
        )
    except Exception as e:
        log.error(
            "Unexpected error deleting discount",
            extra={
                "merchant_id": str(current_admin.merchant_id),
                "discount_id": str(discount_id),
                "error": str(e),
                "event_type": "api_discount_delete_unexpected_error",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post(
    "/validate",
    response_model=ApiResponse[DiscountValidationResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
    },
    summary="Validate discount",
    description="Validate a discount code for checkout",
)
async def validate_discount(
    validation_request: ValidateDiscountRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Validate a discount code for an order.

    **Access**: Any authenticated user

    **Request Body**:
    - **code**: Discount code to validate
    - **subtotal_kobo**: Order subtotal in kobo
    - **customer_id**: Customer ID for usage limit checks (optional)

    **Returns**: Validation result with discount amount or failure reason
    """
    try:
        service = DiscountsService(db)
        result = await service.validate_discount(
            merchant_id=current_user.merchant_id, validation_request=validation_request
        )

        return ApiResponse(
            ok=True, data=result, message="Discount validation completed"
        )

    except DiscountError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation service error",
        )

    except Exception as e:
        log.error(
            "Unexpected error validating discount",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "code": validation_request.code,
                "error": str(e),
                "event_type": "api_discount_validate_unexpected_error",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
