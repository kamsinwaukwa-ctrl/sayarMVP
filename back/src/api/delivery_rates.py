"""
Delivery Rates API endpoints with OpenAPI documentation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from typing import Optional, List, Annotated
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.api import (
    CreateDeliveryRateRequest,
    UpdateDeliveryRateRequest,
    DeliveryRateResponse,
    ApiResponse,
    ApiErrorResponse,
)
from ..database.connection import get_db
from ..dependencies.auth import (
    get_current_user,
    get_current_admin,
    CurrentUser,
    CurrentAdmin,
)
from ..services.delivery_rates_service import DeliveryRatesService, DeliveryRateError

router = APIRouter(prefix="/delivery-rates", tags=["Delivery Rates"])


@router.get(
    "",
    response_model=ApiResponse[List[DeliveryRateResponse]],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="List delivery rates",
    description="Get list of delivery rates for the current merchant (admin + staff access)",
)
async def list_delivery_rates(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """
    Get list of delivery rates for the authenticated merchant.

    - **active**: Optional filter by active status
    - **Requires**: Admin or Staff role
    """
    try:
        service = DeliveryRatesService(db)
        rates = await service.list_rates(
            merchant_id=current_user.merchant_id, active_only=active
        )

        return ApiResponse(data=rates, message=f"Found {len(rates)} delivery rate(s)")

    except DeliveryRateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list delivery rates",
        )


@router.post(
    "",
    response_model=ApiResponse[DeliveryRateResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ApiErrorResponse, "description": "Validation error"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
    },
    summary="Create delivery rate",
    description="Create a new delivery rate for the current merchant (admin only)",
)
async def create_delivery_rate(
    request: CreateDeliveryRateRequest,
    current_user: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Create a new delivery rate.

    - **request**: Delivery rate creation data
    - **Requires**: Admin role only
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    """
    try:
        service = DeliveryRatesService(db)
        rate = await service.create_rate(
            merchant_id=current_user.merchant_id, request=request
        )

        return ApiResponse(
            id=rate.id, data=rate, message="Delivery rate created successfully"
        )

    except DeliveryRateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create delivery rate",
        )


@router.put(
    "/{rate_id}",
    response_model=ApiResponse[DeliveryRateResponse],
    responses={
        400: {
            "model": ApiErrorResponse,
            "description": "Validation error or business rule violation",
        },
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {"model": ApiErrorResponse, "description": "Delivery rate not found"},
        409: {
            "model": ApiErrorResponse,
            "description": "Cannot deactivate last active rate",
        },
    },
    summary="Update delivery rate",
    description="Update a specific delivery rate with business validation (admin only)",
)
async def update_delivery_rate(
    rate_id: UUID,
    request: UpdateDeliveryRateRequest,
    current_user: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Update delivery rate by ID.

    - **rate_id**: Delivery rate UUID
    - **request**: Partial delivery rate data to update
    - **Requires**: Admin role only
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    - **Business Rules**: Cannot deactivate the last active delivery rate
    """
    try:
        service = DeliveryRatesService(db)
        rate = await service.update_rate(
            merchant_id=current_user.merchant_id, rate_id=rate_id, request=request
        )

        return ApiResponse(
            id=rate.id, data=rate, message="Delivery rate updated successfully"
        )

    except DeliveryRateError as e:
        # Check if it's a business rule violation
        if "at least one active" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        elif "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update delivery rate",
        )


@router.delete(
    "/{rate_id}",
    response_model=ApiResponse[dict],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        403: {"model": ApiErrorResponse, "description": "Admin access required"},
        404: {"model": ApiErrorResponse, "description": "Delivery rate not found"},
        409: {
            "model": ApiErrorResponse,
            "description": "Cannot delete last active rate",
        },
    },
    summary="Delete delivery rate",
    description="Delete a specific delivery rate with business validation (admin only)",
)
async def delete_delivery_rate(
    rate_id: UUID,
    current_user: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Delete delivery rate by ID.

    - **rate_id**: Delivery rate UUID
    - **Requires**: Admin role only
    - **Idempotency-Key**: Optional header to ensure idempotent operation
    - **Business Rules**: Cannot delete the last active delivery rate
    """
    try:
        service = DeliveryRatesService(db)
        await service.delete_rate(merchant_id=current_user.merchant_id, rate_id=rate_id)

        return ApiResponse(
            id=rate_id,
            data={"deleted": True, "rate_id": str(rate_id)},
            message="Delivery rate deleted successfully",
        )

    except DeliveryRateError as e:
        # Check if it's a business rule violation
        if "at least one active" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        elif "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete delivery rate",
        )
