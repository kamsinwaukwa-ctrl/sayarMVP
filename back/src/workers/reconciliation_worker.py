"""
Meta Catalog Reconciliation Worker
Scheduled job that runs nightly to detect drift between local and Meta catalog data
"""

import asyncio
import os
from typing import List
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..models.sqlalchemy_models import Merchant
from ..models.meta_reconciliation import ReconciliationRunType
from ..services.meta_reconciliation_service import MetaReconciliationService
from ..database.connection import AsyncSessionLocal
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, set_gauge

logger = get_logger(__name__)


class ReconciliationWorker:
    """Scheduled worker for Meta Catalog reconciliation"""

    def __init__(self):
        self.enabled = (
            os.getenv("META_RECONCILIATION_ENABLED", "true").lower() == "true"
        )
        self.schedule = os.getenv(
            "META_RECONCILIATION_SCHEDULE", "0 2 * * *"
        )  # Daily at 2 AM UTC
        self.batch_size = int(os.getenv("META_RECONCILIATION_BATCH_SIZE", "50"))
        self.timeout_minutes = int(
            os.getenv("META_RECONCILIATION_TIMEOUT_MINUTES", "30")
        )
        self.max_concurrent = int(os.getenv("META_RECONCILIATION_MAX_CONCURRENT", "3"))
        self.scheduler = None

    def start(self, scheduler: AsyncIOScheduler):
        """Start the reconciliation worker"""
        if not self.enabled:
            logger.info("Meta reconciliation worker is disabled")
            return

        self.scheduler = scheduler

        # Add scheduled job
        scheduler.add_job(
            func=self._run_scheduled_reconciliation,
            trigger=CronTrigger.from_crontab(self.schedule),
            id="meta_reconciliation_cron",
            name="Meta Catalog Reconciliation",
            max_instances=1,  # Prevent overlapping runs
            coalesce=True,  # If multiple runs are scheduled, only run the latest
            misfire_grace_time=300,  # Allow 5 minutes grace for missed runs
        )

        logger.info(
            "Meta reconciliation worker started",
            extra={
                "schedule": self.schedule,
                "batch_size": self.batch_size,
                "timeout_minutes": self.timeout_minutes,
                "max_concurrent": self.max_concurrent,
            },
        )

    async def _run_scheduled_reconciliation(self):
        """Execute scheduled reconciliation for all merchants"""
        logger.info("Starting scheduled Meta reconciliation")

        start_time = datetime.utcnow()
        merchants_processed = 0
        merchants_failed = 0
        total_drift_detected = 0
        total_syncs_triggered = 0

        try:
            # Get all merchants with Meta integrations
            async with AsyncSessionLocal() as db:
                merchants = await self._get_eligible_merchants(db)

            if not merchants:
                logger.info("No eligible merchants found for reconciliation")
                return

            logger.info(
                "Found eligible merchants for reconciliation",
                extra={"merchant_count": len(merchants)},
            )

            # Process merchants in batches to control concurrency
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def process_merchant(merchant_id: UUID) -> tuple[bool, int, int]:
                """Process single merchant with semaphore control"""
                async with semaphore:
                    return await self._reconcile_merchant(merchant_id)

            # Create tasks for all merchants
            tasks = [process_merchant(merchant.id) for merchant in merchants]

            # Execute tasks with timeout
            timeout_seconds = self.timeout_minutes * 60
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=timeout_seconds
            )

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "Merchant reconciliation failed",
                        extra={
                            "merchant_id": str(merchants[i].id),
                            "error": str(result),
                        },
                    )
                    merchants_failed += 1
                elif isinstance(result, tuple):
                    success, drift_count, sync_count = result
                    if success:
                        merchants_processed += 1
                        total_drift_detected += drift_count
                        total_syncs_triggered += sync_count
                    else:
                        merchants_failed += 1

            duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                "Completed scheduled Meta reconciliation",
                extra={
                    "event_type": "scheduled_reconciliation_completed",
                    "duration_seconds": duration_seconds,
                    "merchants_total": len(merchants),
                    "merchants_processed": merchants_processed,
                    "merchants_failed": merchants_failed,
                    "total_drift_detected": total_drift_detected,
                    "total_syncs_triggered": total_syncs_triggered,
                },
            )

            # Record metrics
            increment_counter(
                "meta_reconciliation_scheduled_runs_total", {"status": "completed"}
            )
            set_gauge("meta_reconciliation_merchants_processed", merchants_processed)
            set_gauge("meta_reconciliation_merchants_failed", merchants_failed)

        except asyncio.TimeoutError:
            logger.error(
                "Scheduled reconciliation timed out",
                extra={"timeout_minutes": self.timeout_minutes},
            )
            increment_counter(
                "meta_reconciliation_scheduled_runs_total", {"status": "timeout"}
            )

        except Exception as e:
            logger.error(
                "Scheduled reconciliation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            increment_counter(
                "meta_reconciliation_scheduled_runs_total", {"status": "failed"}
            )

    async def _reconcile_merchant(self, merchant_id: UUID) -> tuple[bool, int, int]:
        """Reconcile a single merchant"""
        try:
            async with AsyncSessionLocal() as db:
                reconciliation_service = MetaReconciliationService(db)

                # Run reconciliation
                run = await reconciliation_service.run_reconciliation(
                    merchant_id=merchant_id, run_type=ReconciliationRunType.SCHEDULED
                )

                if run and run.status.value == "completed":
                    return True, run.stats.drift_detected, run.stats.syncs_triggered
                else:
                    return False, 0, 0

        except Exception as e:
            logger.error(
                "Failed to reconcile merchant",
                extra={"merchant_id": str(merchant_id), "error": str(e)},
            )
            return False, 0, 0

    async def _get_eligible_merchants(self, db: AsyncSession) -> List[Merchant]:
        """Get merchants eligible for reconciliation"""

        # Query merchants who have verified Meta integrations
        # This assumes we have a meta_integrations table from BE-019
        query = (
            select(Merchant)
            .join(
                text("meta_integrations"),
                text("merchants.id = meta_integrations.merchant_id"),
            )
            .where(text("meta_integrations.status = 'verified'"))
        )

        result = await db.execute(query)
        return result.scalars().all()

    async def trigger_manual_reconciliation(self, merchant_id: UUID) -> UUID:
        """Trigger manual reconciliation for a specific merchant"""

        logger.info(
            "Triggering manual reconciliation", extra={"merchant_id": str(merchant_id)}
        )

        async with AsyncSessionLocal() as db:
            reconciliation_service = MetaReconciliationService(db)

            run = await reconciliation_service.run_reconciliation(
                merchant_id=merchant_id, run_type=ReconciliationRunType.MANUAL
            )

            if run:
                logger.info(
                    "Manual reconciliation completed",
                    extra={
                        "merchant_id": str(merchant_id),
                        "run_id": str(run.id),
                        "status": run.status.value,
                    },
                )
                return run.id
            else:
                raise Exception("Failed to start manual reconciliation")

    def stop(self):
        """Stop the reconciliation worker"""
        if self.scheduler:
            try:
                self.scheduler.remove_job("meta_reconciliation_cron")
                logger.info("Meta reconciliation worker stopped")
            except Exception as e:
                logger.warning(f"Error stopping reconciliation worker: {e}")


# Global worker instance
reconciliation_worker = ReconciliationWorker()


async def trigger_manual_reconciliation_for_merchant(merchant_id: UUID) -> UUID:
    """Public function to trigger manual reconciliation"""
    return await reconciliation_worker.trigger_manual_reconciliation(merchant_id)


def start_reconciliation_worker(scheduler: AsyncIOScheduler):
    """Start the reconciliation worker with the given scheduler"""
    reconciliation_worker.start(scheduler)


def stop_reconciliation_worker():
    """Stop the reconciliation worker"""
    reconciliation_worker.stop()
