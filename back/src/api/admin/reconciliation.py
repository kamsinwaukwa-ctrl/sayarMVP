"""
Admin API endpoints for Meta Catalog reconciliation management
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ...models.api import ApiResponse, ApiErrorResponse
from ...models.meta_reconciliation import (
    ReconciliationStatusResponse,
    ReconciliationHistoryResponse,
    TriggerReconciliationResponse,
    MerchantReconciliationStatusResponse,
    ReconciliationRun,
    ReconciliationRunType,
    MetaReconciliationRun
)
from ...models.sqlalchemy_models import Product
from ...services.meta_reconciliation_service import MetaReconciliationService
from ...workers.reconciliation_worker import trigger_manual_reconciliation_for_merchant
from ...dependencies.auth import get_current_admin, get_current_user
from ...database.connection import get_db
from ...utils.logger import get_logger
from ...utils.metrics import increment_counter
from ...utils.error_handling import create_error_response

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["admin-reconciliation"])


@router.get(
    "/admin/reconciliation/status",
    response_model=ApiResponse[ReconciliationStatusResponse],
    summary="Get system-wide reconciliation status",
    description="Get the latest reconciliation status across all merchants (admin only)"
)
async def get_reconciliation_status(
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> ApiResponse[ReconciliationStatusResponse]:
    """Get system-wide reconciliation status"""

    try:
        service = MetaReconciliationService(db)

        # Get the most recent run across all merchants
        query = select(MetaReconciliationRun).order_by(
            MetaReconciliationRun.started_at.desc()
        ).limit(1)

        result = await db.execute(query)
        latest_run = result.scalar_one_or_none()

        if not latest_run:
            return ApiResponse(
                ok=True,
                data=ReconciliationStatusResponse(
                    last_run_at=None,
                    status=None,
                    stats=None
                ),
                message="No reconciliation runs found"
            )

        # Convert to response model
        run = await service._get_run(latest_run.id)

        return ApiResponse(
            ok=True,
            data=ReconciliationStatusResponse(
                last_run_at=run.started_at,
                status=run.status,
                stats=run.stats
            ),
            message="Reconciliation status retrieved successfully"
        )

    except Exception as e:
        logger.error(
            "Failed to get reconciliation status",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                "RECONCILIATION_STATUS_ERROR",
                "Failed to retrieve reconciliation status"
            ).dict()
        )


@router.post(
    "/admin/reconciliation/trigger",
    response_model=ApiResponse[TriggerReconciliationResponse],
    summary="Trigger manual reconciliation",
    description="Trigger manual reconciliation for a specific merchant or all merchants (admin only)"
)
async def trigger_reconciliation(
    merchant_id: Optional[UUID] = Query(None, description="Merchant ID to reconcile (if not provided, reconciles all)"),
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> ApiResponse[TriggerReconciliationResponse]:
    """Trigger manual reconciliation"""

    try:
        # Rate limiting check - prevent too frequent manual triggers
        service = MetaReconciliationService(db)

        if merchant_id:
            # Check for recent manual runs for this merchant
            cutoff = datetime.utcnow() - timedelta(hours=1)
            query = select(func.count(MetaReconciliationRun.id)).where(
                and_(
                    MetaReconciliationRun.merchant_id == merchant_id,
                    MetaReconciliationRun.run_type == "manual",
                    MetaReconciliationRun.started_at > cutoff
                )
            )
            result = await db.execute(query)
            recent_count = result.scalar() or 0

            if recent_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=create_error_response(
                        "RECONCILIATION_RATE_LIMITED",
                        "Manual reconciliation can only be triggered once per hour per merchant"
                    ).dict()
                )

            # Trigger reconciliation for specific merchant
            run_id = await trigger_manual_reconciliation_for_merchant(merchant_id)

            logger.info(
                "Manual reconciliation triggered",
                extra={
                    "merchant_id": str(merchant_id),
                    "run_id": str(run_id),
                    "triggered_by": str(admin.id)
                }
            )

            increment_counter("meta_reconciliation_manual_triggers_total", {"scope": "merchant"})

            return ApiResponse(
                ok=True,
                data=TriggerReconciliationResponse(
                    job_id=run_id,
                    scheduled_at=datetime.utcnow()
                ),
                message=f"Manual reconciliation triggered for merchant {merchant_id}"
            )

        else:
            # Trigger reconciliation for all merchants (not implemented in this version)
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=create_error_response(
                    "FEATURE_NOT_IMPLEMENTED",
                    "System-wide manual reconciliation not yet implemented"
                ).dict()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to trigger reconciliation",
            extra={
                "merchant_id": str(merchant_id) if merchant_id else None,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                "RECONCILIATION_TRIGGER_ERROR",
                "Failed to trigger reconciliation"
            ).dict()
        )


@router.get(
    "/admin/reconciliation/history",
    response_model=ApiResponse[ReconciliationHistoryResponse],
    summary="Get reconciliation run history",
    description="Get paginated history of reconciliation runs across all merchants (admin only)"
)
async def get_reconciliation_history(
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    merchant_id: Optional[UUID] = Query(None, description="Filter by merchant ID"),
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> ApiResponse[ReconciliationHistoryResponse]:
    """Get reconciliation run history"""

    try:
        service = MetaReconciliationService(db)

        runs, total = await service.get_reconciliation_history(
            merchant_id=merchant_id,
            limit=limit,
            offset=offset
        )

        pagination = {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + limit < total
        }

        return ApiResponse(
            ok=True,
            data=ReconciliationHistoryResponse(
                runs=runs,
                total=total,
                pagination=pagination
            ),
            message="Reconciliation history retrieved successfully"
        )

    except Exception as e:
        logger.error(
            "Failed to get reconciliation history",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                "RECONCILIATION_HISTORY_ERROR",
                "Failed to retrieve reconciliation history"
            ).dict()
        )


# Merchant-scoped reconciliation endpoint
@router.get(
    "/reconciliation/status",
    response_model=ApiResponse[MerchantReconciliationStatusResponse],
    summary="Get merchant reconciliation status",
    description="Get reconciliation status for the current merchant"
)
async def get_merchant_reconciliation_status(
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApiResponse[MerchantReconciliationStatusResponse]:
    """Get reconciliation status for current merchant"""

    try:
        service = MetaReconciliationService(db)

        # Get latest run for this merchant
        latest_run = await service.get_latest_reconciliation_status(user.merchant_id)

        # Count pending sync jobs
        pending_sync_query = select(func.count()).select_from(
            select(Product.id).where(
                and_(
                    Product.merchant_id == user.merchant_id,
                    Product.meta_sync_status == "pending"
                )
            ).subquery()
        )

        result = await db.execute(pending_sync_query)
        sync_pending = result.scalar() or 0

        if latest_run:
            return ApiResponse(
                ok=True,
                data=MerchantReconciliationStatusResponse(
                    last_run_at=latest_run.started_at,
                    products_checked=latest_run.stats.products_checked,
                    drift_detected=latest_run.stats.drift_detected,
                    sync_pending=sync_pending
                ),
                message="Merchant reconciliation status retrieved successfully"
            )
        else:
            return ApiResponse(
                ok=True,
                data=MerchantReconciliationStatusResponse(
                    last_run_at=None,
                    products_checked=0,
                    drift_detected=0,
                    sync_pending=sync_pending
                ),
                message="No reconciliation runs found for this merchant"
            )

    except Exception as e:
        logger.error(
            "Failed to get merchant reconciliation status",
            extra={
                "merchant_id": str(user.merchant_id),
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                "MERCHANT_RECONCILIATION_STATUS_ERROR",
                "Failed to retrieve merchant reconciliation status"
            ).dict()
        )