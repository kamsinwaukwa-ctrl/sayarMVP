"""
Outbox worker implementation using APScheduler with leader election
Processes outbox jobs reliably with FOR UPDATE SKIP LOCKED and exponential backoff
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..models.outbox import OutboxEvent, JobType, WorkerConfig
from ..utils.outbox import (
    fetch_due_jobs,
    mark_job_done,
    mark_job_error,
    move_to_dlq,
    acquire_leader_lock,
    release_leader_lock,
    record_heartbeat,
)
from ..utils.logger import log
from ..utils.metrics import (
    outbox_jobs_processed_total,
    outbox_jobs_failed_total,
    dlq_jobs_total,
    worker_heartbeats_total,
    outbox_fetch_batch_seconds,
    job_handle_seconds,
)
from .job_handlers import get_job_handler
from .reconciliation_worker import start_reconciliation_worker, stop_reconciliation_worker

logger = logging.getLogger(__name__)


class OutboxWorker:
    """
    Outbox worker that processes jobs using APScheduler with leader election
    """
    
    def __init__(self, config: WorkerConfig = None):
        self.config = config or WorkerConfig()
        self.scheduler = AsyncIOScheduler()
        self.instance_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.is_leader = False
        self.is_running = False
        
    async def start(self):
        """Start the outbox worker scheduler"""
        if not self.config.enabled:
            log.info(
                "Outbox worker disabled via configuration",
                extra={
                    "event_type": "worker_disabled",
                    "instance_id": self.instance_id
                }
            )
            return
            
        log.info(
            "Starting outbox worker",
            extra={
                "event_type": "worker_starting",
                "instance_id": self.instance_id,
                "config": self.config.dict()
            }
        )
        
        # Add the polling job to the scheduler
        self.scheduler.add_job(
            self._poll_and_process_jobs,
            trigger=IntervalTrigger(seconds=self.config.poll_interval),
            id="outbox_polling",
            replace_existing=True,
        )
        
        # Start the reconciliation worker with shared scheduler
        start_reconciliation_worker(self.scheduler)

        self.scheduler.start()
        self.is_running = True

        log.info(
            "Outbox worker started successfully",
            extra={
                "event_type": "worker_started",
                "instance_id": self.instance_id,
                "poll_interval": self.config.poll_interval
            }
        )
    
    async def stop(self):
        """Stop the outbox worker scheduler"""
        if self.is_running:
            log.info(
                "Stopping outbox worker",
                extra={
                    "event_type": "worker_stopping",
                    "instance_id": self.instance_id
                }
            )
            
            # Release leader lock if we have it
            if self.is_leader:
                await self._release_leader()

            # Stop the reconciliation worker
            stop_reconciliation_worker()

            self.scheduler.shutdown()
            self.is_running = False
            
            log.info(
                "Outbox worker stopped",
                extra={
                    "event_type": "worker_stopped",
                    "instance_id": self.instance_id
                }
            )
    
    async def _poll_and_process_jobs(self):
        """
        Main polling method that acquires leader lock and processes jobs
        """
        try:
            # Try to acquire leader lock
            if not self.is_leader:
                acquired = await acquire_leader_lock(
                    self.config.lock_key, 
                    self.instance_id
                )
                if acquired:
                    self.is_leader = True
                    log.info(
                        "Acquired leader lock",
                        extra={
                            "event_type": "worker_leader_acquired",
                            "instance_id": self.instance_id,
                            "lock_key": self.config.lock_key
                        }
                    )
                else:
                    # Not the leader, skip processing
                    return
            
            # Record heartbeat to show we're alive
            await self._record_heartbeat()
            
            # Process due jobs
            await self._process_due_jobs()
            
        except Exception as e:
            log.error(
                "Error in polling loop",
                extra={
                    "event_type": "worker_poll_error",
                    "instance_id": self.instance_id,
                    "error": str(e)
                }
            )
            
            # If we encounter an error, release leader lock to allow another instance to take over
            if self.is_leader:
                await self._release_leader()
    
    async def _record_heartbeat(self):
        """Record worker heartbeat for monitoring"""
        heartbeat_details = {
            "is_leader": self.is_leader,
            "poll_interval": self.config.poll_interval,
            "batch_size": self.config.batch_size,
            "max_concurrent": self.config.max_concurrent,
            "status": "running"
        }
        
        success = await record_heartbeat(self.instance_id, heartbeat_details)
        if success:
            worker_heartbeats_total.inc()
            
            if self.is_leader:
                log.debug(
                    "Leader heartbeat recorded",
                    extra={
                        "event_type": "worker_heartbeat",
                        "instance_id": self.instance_id,
                        "is_leader": True
                    }
                )
    
    async def _release_leader(self):
        """Release leader lock"""
        released = await release_leader_lock(self.config.lock_key, self.instance_id)
        if released:
            self.is_leader = False
            log.info(
                "Released leader lock",
                extra={
                    "event_type": "worker_leader_released",
                    "instance_id": self.instance_id,
                    "lock_key": self.config.lock_key
                }
            )
    
    async def _process_due_jobs(self):
        """Fetch and process due jobs with concurrency control"""
        start_time = datetime.now()
        
        try:
            # Fetch due jobs using FOR UPDATE SKIP LOCKED
            jobs = await fetch_due_jobs(self.config.batch_size)
            
            fetch_duration = (datetime.now() - start_time).total_seconds()
            outbox_fetch_batch_seconds.observe(fetch_duration)
            
            if not jobs:
                log.debug(
                    "No due jobs found",
                    extra={
                        "event_type": "outbox_no_jobs",
                        "instance_id": self.instance_id
                    }
                )
                return
            
            log.info(
                "Fetched jobs for processing",
                extra={
                    "event_type": "outbox_jobs_fetched",
                    "instance_id": self.instance_id,
                    "count": len(jobs),
                    "fetch_duration_seconds": fetch_duration,
                    "job_types": [job.job_type.value for job in jobs]
                }
            )
            
            # Process jobs with concurrency control
            semaphore = asyncio.Semaphore(self.config.max_concurrent)
            
            # Create processing tasks for all jobs
            processing_tasks = []
            for job in jobs:
                task = asyncio.create_task(
                    self._process_job_with_semaphore(job, semaphore)
                )
                processing_tasks.append(task)
            
            # Wait for all processing to complete
            await asyncio.gather(*processing_tasks, return_exceptions=True)
            
            log.info(
                "Batch processing completed",
                extra={
                    "event_type": "outbox_batch_complete",
                    "instance_id": self.instance_id,
                    "total_jobs": len(jobs),
                    "batch_duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            )
            
        except Exception as e:
            log.error(
                "Failed to process due jobs",
                extra={
                    "event_type": "outbox_batch_failed",
                    "instance_id": self.instance_id,
                    "error": str(e)
                }
            )
    
    async def _process_job_with_semaphore(self, job: OutboxEvent, semaphore: asyncio.Semaphore):
        """Process a job with concurrency control"""
        async with semaphore:
            await self._process_job(job)
    
    async def _process_job(self, job: OutboxEvent):
        """Process an individual outbox job"""
        job_start_time = datetime.now()
        
        try:
            log.info(
                "Processing job",
                extra={
                    "event_type": "outbox_job_start",
                    "job_id": str(job.id),
                    "job_type": job.job_type.value,
                    "merchant_id": str(job.merchant_id),
                    "attempt": job.attempts + 1,
                    "max_attempts": job.max_attempts
                }
            )
            
            # Get the appropriate handler for this job type
            handler = get_job_handler(job.job_type)
            
            # Execute the job handler
            result = await handler(job)
            
            job_duration = (datetime.now() - job_start_time).total_seconds()
            job_handle_seconds.labels(job_type=job.job_type.value).observe(job_duration)
            
            if result.success:
                # Mark job as successfully completed
                await mark_job_done(job.id)
                outbox_jobs_processed_total.labels(job_type=job.job_type.value).inc()
                
                log.info(
                    "Job completed successfully",
                    extra={
                        "event_type": "outbox_job_end",
                        "job_id": str(job.id),
                        "job_type": job.job_type.value,
                        "merchant_id": str(job.merchant_id),
                        "duration_seconds": job_duration
                    }
                )
                
            else:
                # Handle job failure with retry logic
                await self._handle_job_failure(job, result, job_duration)
                
        except Exception as e:
            # Handle unexpected errors during job processing
            error_msg = f"Unexpected error processing job: {str(e)}"
            log.error(
                "Unexpected job processing error",
                extra={
                    "event_type": "outbox_job_error",
                    "job_id": str(job.id),
                    "job_type": job.job_type.value,
                    "merchant_id": str(job.merchant_id),
                    "error": error_msg
                }
            )
            
            # Mark as error with retry
            await mark_job_error(job.id, error_msg)
            outbox_jobs_failed_total.labels(job_type=job.job_type.value).inc()
    
    async def _handle_job_failure(self, job: OutboxEvent, result: Any, duration: float):
        """Handle job failure with appropriate retry or DLQ logic"""
        
        if result.should_retry and job.attempts < job.max_attempts - 1:
            # Calculate exponential backoff with jitter
            base_delay = 1.0  # Base delay in seconds
            max_delay = 300.0  # Maximum delay in seconds (5 minutes)
            
            # Exponential backoff: base * 2^attempts
            delay = min(base_delay * (2 ** job.attempts), max_delay)
            
            # Add jitter: ± base_delay seconds
            import random
            jitter = random.uniform(-base_delay, base_delay)
            delay = max(1.0, delay + jitter)  # Ensure at least 1 second
            
            next_run_at = datetime.now() + timedelta(seconds=delay)
            
            # Reschedule the job
            await mark_job_error(job.id, result.error, next_run_at)
            
            log.warning(
                "Job failed, will retry",
                extra={
                    "event_type": "outbox_job_retry",
                    "job_id": str(job.id),
                    "job_type": job.job_type.value,
                    "merchant_id": str(job.merchant_id),
                    "attempt": job.attempts + 1,
                    "max_attempts": job.max_attempts,
                    "next_run_at": next_run_at.isoformat(),
                    "delay_seconds": delay,
                    "error": result.error,
                    "duration_seconds": duration
                }
            )
            
        else:
            # Max attempts reached or fatal error - move to DLQ
            await move_to_dlq(
                job.id,
                source="outbox_worker",
                reason=f"Max attempts reached: {job.attempts + 1}/{job.max_attempts}. Error: {result.error}"
            )
            
            dlq_jobs_total.labels(source="outbox_worker").inc()
            outbox_jobs_failed_total.labels(job_type=job.job_type.value).inc()
            
            log.error(
                "Job moved to DLQ",
                extra={
                    "event_type": "dlq_job_moved",
                    "job_id": str(job.id),
                    "job_type": job.job_type.value,
                    "merchant_id": str(job.merchant_id),
                    "attempts": job.attempts + 1,
                    "max_attempts": job.max_attempts,
                    "reason": "Max attempts reached",
                    "error": result.error,
                    "duration_seconds": duration
                }
            )


# Global worker instance
_worker_instance = None


def get_worker() -> OutboxWorker:
    """Get or create the global outbox worker instance"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = OutboxWorker()
    return _worker_instance


async def start_worker():
    """Start the outbox worker (to be called from FastAPI lifespan)"""
    worker = get_worker()
    await worker.start()


async def stop_worker():
    """Stop the outbox worker (to be called from FastAPI lifespan)"""
    worker = get_worker()
    await worker.stop()