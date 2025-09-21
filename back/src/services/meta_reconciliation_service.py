"""
Meta Catalog Reconciliation Service
Compares local product data with Meta Catalog and detects drift
"""

import asyncio
import json
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.orm import selectinload

from ..models.meta_reconciliation import (
    MetaItem,
    ReconciliationRunType,
    ReconciliationStatus,
    DriftAction,
    ProductFieldDrift,
    ProductReconciliationResult,
    ReconciliationRunStats,
    ReconciliationRun,
    MetaReconciliationRun,
    MetaDriftLog,
    format_price,
    format_availability,
    normalize_image_url
)
from ..models.sqlalchemy_models import Product, Merchant
from ..models.meta_catalog import MetaCatalogConfig
from ..integrations.meta_catalog import MetaCatalogClient, MetaCatalogError
from ..services.product_service import ProductService
from ..services.meta_integration_service import MetaIntegrationService
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_histogram, set_gauge
from ..utils.outbox import enqueue_job
from ..utils.retry import retryable, RetryConfig

logger = get_logger(__name__)


class MetaReconciliationService:
    """Service for reconciling local product data with Meta Catalog"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.meta_catalog_client = MetaCatalogClient()
        self.product_service = ProductService(db)
        self.meta_integration_service = MetaIntegrationService(db)

    async def start_reconciliation_run(
        self,
        merchant_id: UUID,
        run_type: ReconciliationRunType
    ) -> UUID:
        """Start a new reconciliation run"""

        # Check for recent runs to prevent duplicates
        if await self._has_recent_run(merchant_id, run_type):
            logger.info(
                "Skipping reconciliation run due to recent run",
                extra={
                    "merchant_id": str(merchant_id),
                    "run_type": run_type.value
                }
            )
            return None

        # Count total eligible products
        total_products = await self._count_eligible_products(merchant_id)

        # Create reconciliation run record
        run = MetaReconciliationRun(
            merchant_id=merchant_id,
            run_type=run_type.value,
            status=ReconciliationStatus.RUNNING.value,
            products_total=total_products,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        logger.info(
            "Started reconciliation run",
            extra={
                "event_type": "reconciliation_started",
                "merchant_id": str(merchant_id),
                "run_id": str(run.id),
                "run_type": run_type.value,
                "products_total": total_products
            }
        )

        increment_counter("meta_reconciliation_runs_total", {"status": "started"})
        return run.id

    async def run_reconciliation(
        self,
        merchant_id: UUID,
        run_type: ReconciliationRunType
    ) -> Optional[ReconciliationRun]:
        """Execute complete reconciliation for a merchant"""

        run_id = await self.start_reconciliation_run(merchant_id, run_type)
        if not run_id:
            return None

        start_time = datetime.utcnow()

        try:
            # Load Meta credentials
            meta_config = await self._load_meta_credentials(merchant_id)
            if not meta_config:
                await self._mark_run_failed(
                    run_id,
                    "No verified Meta credentials found for merchant"
                )
                return await self._get_run(run_id)

            # Get eligible products
            products = await self._get_eligible_products(merchant_id)

            # Reconcile products in batches
            stats = ReconciliationRunStats()
            batch_size = 50  # Configurable batch size

            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                batch_results = await self._reconcile_product_batch(
                    run_id, batch, meta_config
                )

                # Update stats
                for result in batch_results:
                    stats.products_checked += 1
                    if result.has_drift:
                        stats.drift_detected += 1
                    if result.sync_triggered:
                        stats.syncs_triggered += 1
                    if result.error:
                        stats.errors_count += 1

                # Update progress
                await self._update_run_progress(run_id, stats)

            # Mark run as completed
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            stats.duration_ms = duration_ms

            await self._mark_run_completed(run_id, stats)

            logger.info(
                "Completed reconciliation run",
                extra={
                    "event_type": "reconciliation_completed",
                    "merchant_id": str(merchant_id),
                    "run_id": str(run_id),
                    "duration_ms": duration_ms,
                    "products_checked": stats.products_checked,
                    "drift_detected": stats.drift_detected,
                    "syncs_triggered": stats.syncs_triggered,
                    "errors_count": stats.errors_count
                }
            )

            # Record metrics
            increment_counter("meta_reconciliation_runs_total", {"status": "completed"})
            record_histogram("meta_reconciliation_duration_seconds", duration_ms / 1000)
            increment_counter("meta_products_checked_total", {}, stats.products_checked)
            increment_counter("meta_drift_detected_total", {}, stats.drift_detected)
            increment_counter("meta_syncs_triggered_total", {}, stats.syncs_triggered)

            return await self._get_run(run_id)

        except Exception as e:
            await self._mark_run_failed(run_id, str(e))
            logger.error(
                "Reconciliation run failed",
                extra={
                    "merchant_id": str(merchant_id),
                    "run_id": str(run_id),
                    "error": str(e)
                },
                exc_info=True
            )
            increment_counter("meta_reconciliation_runs_total", {"status": "failed"})
            return await self._get_run(run_id)

    async def _reconcile_product_batch(
        self,
        run_id: UUID,
        products: List[Product],
        meta_config: MetaCatalogConfig
    ) -> List[ProductReconciliationResult]:
        """Reconcile a batch of products with Meta Catalog"""

        if not products:
            return []

        retailer_ids = [f"sayar_product_{product.id}" for product in products]

        try:
            # Fetch Meta catalog data
            meta_items = await self._fetch_meta_catalog_data(
                meta_config.catalog_id, retailer_ids, meta_config
            )

            results = []
            for product in products:
                retailer_id = f"sayar_product_{product.id}"
                meta_item = meta_items.get(retailer_id)

                result = await self._reconcile_single_product(
                    run_id, product, meta_item, retailer_id
                )
                results.append(result)

            return results

        except Exception as e:
            logger.error(
                "Failed to reconcile product batch",
                extra={
                    "run_id": str(run_id),
                    "product_count": len(products),
                    "error": str(e)
                }
            )

            # Return error results for all products in batch
            return [
                ProductReconciliationResult(
                    product_id=product.id,
                    retailer_id=f"sayar_product_{product.id}",
                    has_drift=False,
                    error=f"Batch reconciliation failed: {str(e)}"
                )
                for product in products
            ]

    async def _reconcile_single_product(
        self,
        run_id: UUID,
        product: Product,
        meta_item: Optional[MetaItem],
        retailer_id: str
    ) -> ProductReconciliationResult:
        """Reconcile a single product with its Meta Catalog representation"""

        drift_fields = []

        # Handle missing remote item
        if meta_item is None:
            drift_fields.append(ProductFieldDrift(
                field_name="missing_remote",
                local_value="exists",
                meta_value="missing",
                action_taken=DriftAction.SYNC_TRIGGERED
            ))
        else:
            # Compare individual fields
            drift_fields.extend(await self._compare_product_fields(product, meta_item))

        has_drift = len(drift_fields) > 0
        sync_triggered = False
        error = None

        # Trigger sync if drift detected and auto-sync enabled
        if has_drift:
            try:
                await self._trigger_product_sync(product.id, product.merchant_id)
                sync_triggered = True

                # Log drift detection
                for drift in drift_fields:
                    drift.action_taken = DriftAction.SYNC_TRIGGERED
                    await self._log_drift(run_id, product, drift)

                logger.info(
                    "Product drift detected and sync triggered",
                    extra={
                        "event_type": "product_drift_detected",
                        "merchant_id": str(product.merchant_id),
                        "run_id": str(run_id),
                        "product_id": str(product.id),
                        "retailer_id": retailer_id,
                        "drift_fields": [d.field_name for d in drift_fields],
                        "sync_triggered": True
                    }
                )

            except Exception as e:
                error = f"Failed to trigger sync: {str(e)}"
                logger.error(
                    "Failed to trigger product sync after drift detection",
                    extra={
                        "product_id": str(product.id),
                        "error": str(e)
                    }
                )

                # Update drift actions to failed
                for drift in drift_fields:
                    drift.action_taken = DriftAction.FAILED
                    await self._log_drift(run_id, product, drift)

        return ProductReconciliationResult(
            product_id=product.id,
            retailer_id=retailer_id,
            has_drift=has_drift,
            drift_fields=drift_fields,
            sync_triggered=sync_triggered,
            error=error
        )

    async def _compare_product_fields(
        self,
        product: Product,
        meta_item: MetaItem
    ) -> List[ProductFieldDrift]:
        """Compare product fields and detect drift"""

        drift_fields = []

        # Compare price
        local_price = format_price(product.price_kobo)
        meta_price = meta_item.get("price")
        if local_price != meta_price:
            drift_fields.append(ProductFieldDrift(
                field_name="price_kobo",
                local_value=local_price,
                meta_value=meta_price,
                action_taken=DriftAction.SYNC_TRIGGERED
            ))

        # Compare availability/stock
        local_availability = format_availability(product.stock)
        meta_availability = meta_item.get("availability")
        if local_availability != meta_availability:
            drift_fields.append(ProductFieldDrift(
                field_name="stock",
                local_value=local_availability,
                meta_value=meta_availability,
                action_taken=DriftAction.SYNC_TRIGGERED
            ))

        # Compare title
        local_title = product.title
        meta_title = meta_item.get("title")
        if local_title != meta_title:
            drift_fields.append(ProductFieldDrift(
                field_name="title",
                local_value=local_title,
                meta_value=meta_title,
                action_taken=DriftAction.SYNC_TRIGGERED
            ))

        # Compare primary image URL
        if hasattr(product, 'primary_image_url') and product.primary_image_url:
            local_image = normalize_image_url(product.primary_image_url)
            meta_image = normalize_image_url(meta_item.get("image_link", ""))
            if local_image != meta_image:
                drift_fields.append(ProductFieldDrift(
                    field_name="image_url",
                    local_value=local_image,
                    meta_value=meta_image,
                    action_taken=DriftAction.SYNC_TRIGGERED
                ))

        return drift_fields

    @retryable(config=RetryConfig(max_attempts=3, exponential_base=2.0))
    async def _fetch_meta_catalog_data(
        self,
        catalog_id: str,
        retailer_ids: List[str],
        config: MetaCatalogConfig
    ) -> Dict[str, MetaItem]:
        """Fetch product data from Meta Catalog API"""

        try:
            # Use the Meta catalog client to fetch items
            # This is a simplified implementation - in practice would use batch endpoint
            result = await self.meta_catalog_client.get_catalog_items(
                catalog_id=catalog_id,
                retailer_ids=retailer_ids,
                config=config
            )

            return result.get("items", {})

        except MetaCatalogError as e:
            logger.error(
                "Meta API error during reconciliation",
                extra={
                    "catalog_id": catalog_id,
                    "error_code": e.error_code,
                    "error_message": e.message
                }
            )
            raise

    async def _trigger_product_sync(self, product_id: UUID, merchant_id: UUID):
        """Trigger a product re-sync via outbox job"""

        await enqueue_job(
            db=self.db,
            job_type="catalog_sync",
            payload={
                "product_id": str(product_id),
                "merchant_id": str(merchant_id),
                "trigger": "reconciliation",
                "action": "update",
                "timestamp": datetime.utcnow().isoformat()
            },
            deduplication_key=f"reconciliation_sync:{merchant_id}:{product_id}",
            merchant_id=merchant_id
        )

    async def _log_drift(
        self,
        run_id: UUID,
        product: Product,
        drift: ProductFieldDrift
    ):
        """Log detected drift to database"""

        drift_log = MetaDriftLog(
            reconciliation_run_id=run_id,
            product_id=product.id,
            merchant_id=product.merchant_id,
            field_name=drift.field_name,
            local_value=drift.local_value,
            meta_value=drift.meta_value,
            action_taken=drift.action_taken.value,
            created_at=datetime.utcnow()
        )

        self.db.add(drift_log)
        await self.db.commit()

    async def _load_meta_credentials(self, merchant_id: UUID) -> Optional[MetaCatalogConfig]:
        """Load Meta credentials for merchant"""
        try:
            return await self.meta_integration_service.get_credentials_for_worker(merchant_id)
        except Exception as e:
            logger.warning(
                "Failed to load Meta credentials for reconciliation",
                extra={
                    "merchant_id": str(merchant_id),
                    "error": str(e)
                }
            )
            return None

    async def _get_eligible_products(self, merchant_id: UUID) -> List[Product]:
        """Get products eligible for reconciliation"""

        query = select(Product).where(
            and_(
                Product.merchant_id == merchant_id,
                Product.status == "active",
                Product.meta_sync_status == "synced",
                Product.retailer_id.isnot(None)
            )
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _count_eligible_products(self, merchant_id: UUID) -> int:
        """Count products eligible for reconciliation"""

        query = select(func.count(Product.id)).where(
            and_(
                Product.merchant_id == merchant_id,
                Product.status == "active",
                Product.meta_sync_status == "synced",
                Product.retailer_id.isnot(None)
            )
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _has_recent_run(
        self,
        merchant_id: UUID,
        run_type: ReconciliationRunType,
        window_minutes: int = 60
    ) -> bool:
        """Check if there's a recent run within the specified window"""

        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

        query = select(func.count(MetaReconciliationRun.id)).where(
            and_(
                MetaReconciliationRun.merchant_id == merchant_id,
                MetaReconciliationRun.run_type == run_type.value,
                MetaReconciliationRun.started_at > cutoff
            )
        )

        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def _update_run_progress(self, run_id: UUID, stats: ReconciliationRunStats):
        """Update reconciliation run progress"""

        query = select(MetaReconciliationRun).where(MetaReconciliationRun.id == run_id)
        result = await self.db.execute(query)
        run = result.scalar_one_or_none()

        if run:
            run.products_checked = stats.products_checked
            run.drift_detected = stats.drift_detected
            run.syncs_triggered = stats.syncs_triggered
            run.errors_count = stats.errors_count
            run.updated_at = datetime.utcnow()

            await self.db.commit()

    async def _mark_run_completed(self, run_id: UUID, stats: ReconciliationRunStats):
        """Mark reconciliation run as completed"""

        query = select(MetaReconciliationRun).where(MetaReconciliationRun.id == run_id)
        result = await self.db.execute(query)
        run = result.scalar_one_or_none()

        if run:
            run.status = ReconciliationStatus.COMPLETED.value
            run.completed_at = datetime.utcnow()
            run.duration_ms = stats.duration_ms
            run.products_checked = stats.products_checked
            run.drift_detected = stats.drift_detected
            run.syncs_triggered = stats.syncs_triggered
            run.errors_count = stats.errors_count
            run.updated_at = datetime.utcnow()

            await self.db.commit()

    async def _mark_run_failed(self, run_id: UUID, error_message: str):
        """Mark reconciliation run as failed"""

        query = select(MetaReconciliationRun).where(MetaReconciliationRun.id == run_id)
        result = await self.db.execute(query)
        run = result.scalar_one_or_none()

        if run:
            run.status = ReconciliationStatus.FAILED.value
            run.completed_at = datetime.utcnow()
            run.last_error = error_message
            run.updated_at = datetime.utcnow()

            await self.db.commit()

    async def _get_run(self, run_id: UUID) -> Optional[ReconciliationRun]:
        """Get reconciliation run by ID"""

        query = select(MetaReconciliationRun).where(MetaReconciliationRun.id == run_id)
        result = await self.db.execute(query)
        run_db = result.scalar_one_or_none()

        if not run_db:
            return None

        stats = ReconciliationRunStats(
            products_total=run_db.products_total,
            products_checked=run_db.products_checked,
            drift_detected=run_db.drift_detected,
            syncs_triggered=run_db.syncs_triggered,
            errors_count=run_db.errors_count,
            duration_ms=run_db.duration_ms
        )

        return ReconciliationRun(
            id=run_db.id,
            merchant_id=run_db.merchant_id,
            run_type=ReconciliationRunType(run_db.run_type),
            status=ReconciliationStatus(run_db.status),
            stats=stats,
            started_at=run_db.started_at,
            completed_at=run_db.completed_at,
            last_error=run_db.last_error
        )

    # Public API methods for endpoints

    async def get_reconciliation_history(
        self,
        merchant_id: Optional[UUID] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[ReconciliationRun], int]:
        """Get reconciliation run history"""

        # Build query
        query = select(MetaReconciliationRun)
        count_query = select(func.count(MetaReconciliationRun.id))

        if merchant_id:
            query = query.where(MetaReconciliationRun.merchant_id == merchant_id)
            count_query = count_query.where(MetaReconciliationRun.merchant_id == merchant_id)

        query = query.order_by(desc(MetaReconciliationRun.started_at)).limit(limit).offset(offset)

        # Execute queries
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        runs_db = result.scalars().all()
        total = count_result.scalar() or 0

        # Convert to response models
        runs = []
        for run_db in runs_db:
            stats = ReconciliationRunStats(
                products_total=run_db.products_total,
                products_checked=run_db.products_checked,
                drift_detected=run_db.drift_detected,
                syncs_triggered=run_db.syncs_triggered,
                errors_count=run_db.errors_count,
                duration_ms=run_db.duration_ms
            )

            runs.append(ReconciliationRun(
                id=run_db.id,
                merchant_id=run_db.merchant_id,
                run_type=ReconciliationRunType(run_db.run_type),
                status=ReconciliationStatus(run_db.status),
                stats=stats,
                started_at=run_db.started_at,
                completed_at=run_db.completed_at,
                last_error=run_db.last_error
            ))

        return runs, total

    async def get_latest_reconciliation_status(
        self,
        merchant_id: UUID
    ) -> Optional[ReconciliationRun]:
        """Get the latest reconciliation run for a merchant"""

        query = select(MetaReconciliationRun).where(
            MetaReconciliationRun.merchant_id == merchant_id
        ).order_by(desc(MetaReconciliationRun.started_at)).limit(1)

        result = await self.db.execute(query)
        run_db = result.scalar_one_or_none()

        if not run_db:
            return None

        return await self._get_run(run_db.id)