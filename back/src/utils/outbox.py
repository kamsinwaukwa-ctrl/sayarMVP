"""
Outbox utilities for Sayar WhatsApp Commerce Platform
Provides functions to enqueue, update, and manage outbox jobs
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy import text, select, update, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.outbox import (
    OutboxEvent,
    DLQEvent,
    CreateOutboxEvent,
    JobType,
    JobStatus,
    WorkerHeartbeat,
)
from ..utils.logger import log
from ..database.connection import AsyncSessionLocal, WorkerSessionLocal


async def enqueue_job(
    merchant_id: UUID,
    job_type: JobType,
    payload: Dict[str, Any],
    max_attempts: int = 8,
    run_at: Optional[datetime] = None,
    db: Optional[AsyncSession] = None,
) -> UUID:
    """
    Enqueue a job to the outbox for processing

    Args:
        merchant_id: Merchant that owns this job
        job_type: Type of job to process
        payload: Job data (must be JSON serializable)
        max_attempts: Maximum retry attempts
        run_at: When to run the job (default: now)
        db: Database session (optional, creates one if not provided)

    Returns:
        UUID of the created job
    """
    if run_at is None:
        run_at = datetime.now(timezone.utc)

    # Validate payload is serializable
    try:
        json.dumps(payload)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Job payload must be JSON serializable: {e}")

    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"admin\"}', true)"
            )
        )

        query = text(
            """
            INSERT INTO outbox_events (merchant_id, job_type, payload, max_attempts, next_run_at)
            VALUES (:merchant_id, :job_type, :payload, :max_attempts, :next_run_at)
            RETURNING id
        """
        )

        result = await db.execute(
            query,
            {
                "merchant_id": str(merchant_id),
                "job_type": job_type.value,
                "payload": json.dumps(payload),
                "max_attempts": max_attempts,
                "next_run_at": run_at,
            },
        )

        job_id = result.scalar_one()
        await db.commit()

        log.info(
            "Job enqueued successfully",
            extra={
                "event_type": "outbox_job_enqueued",
                "job_id": str(job_id),
                "merchant_id": str(merchant_id),
                "job_type": job_type.value,
                "max_attempts": max_attempts,
                "scheduled_at": run_at.isoformat(),
            },
        )

        return UUID(job_id)

    except Exception as e:
        await db.rollback()
        log.error(
            "Failed to enqueue job",
            extra={
                "event_type": "outbox_job_enqueue_failed",
                "merchant_id": str(merchant_id),
                "job_type": job_type.value,
                "error": str(e),
            },
        )
        raise
    finally:
        if close_db:
            await db.close()


async def fetch_due_jobs(
    batch_size: int = 50, db: Optional[AsyncSession] = None
) -> List[OutboxEvent]:
    """
    Fetch due jobs using FOR UPDATE SKIP LOCKED to prevent race conditions

    Args:
        batch_size: Maximum number of jobs to fetch
        db: Database session (optional)

    Returns:
        List of OutboxEvent objects ready for processing
    """
    close_db = False
    if db is None:
        db = WorkerSessionLocal()  # Use worker session with connection pooling
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)"
            )
        )

        # Fetch and lock jobs atomically
        query = text(
            """
            UPDATE outbox_events 
            SET status = 'processing', updated_at = now()
            WHERE id IN (
                SELECT id FROM outbox_events
                WHERE status = 'pending' 
                  AND next_run_at <= now()
                ORDER BY next_run_at
                LIMIT :batch_size
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, merchant_id, job_type, payload, status, attempts, 
                      max_attempts, next_run_at, last_error, created_at, updated_at
        """
        )

        result = await db.execute(query, {"batch_size": batch_size})
        rows = result.fetchall()
        await db.commit()

        jobs = []
        for row in rows:
            jobs.append(
                OutboxEvent(
                    id=UUID(row.id),
                    merchant_id=UUID(row.merchant_id),
                    job_type=JobType(row.job_type),
                    payload=(
                        json.loads(row.payload)
                        if isinstance(row.payload, str)
                        else row.payload
                    ),
                    status=JobStatus(row.status),
                    attempts=row.attempts,
                    max_attempts=row.max_attempts,
                    next_run_at=row.next_run_at,
                    last_error=row.last_error,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )

        if jobs:
            log.info(
                "Fetched jobs for processing",
                extra={
                    "event_type": "outbox_jobs_fetched",
                    "count": len(jobs),
                    "job_types": [job.job_type.value for job in jobs],
                },
            )

        return jobs

    except Exception as e:
        await db.rollback()
        log.error(
            "Failed to fetch due jobs",
            extra={"event_type": "outbox_fetch_failed", "error": str(e)},
        )
        raise
    finally:
        if close_db:
            await db.close()


async def mark_job_done(job_id: UUID, db: Optional[AsyncSession] = None) -> bool:
    """
    Mark a job as successfully completed

    Args:
        job_id: ID of the job to mark as done
        db: Database session (optional)

    Returns:
        True if job was updated, False if not found
    """
    close_db = False
    if db is None:
        db = WorkerSessionLocal()  # Use worker session with connection pooling
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)"
            )
        )

        query = text(
            """
            UPDATE outbox_events 
            SET status = 'done', updated_at = now()
            WHERE id = :job_id
        """
        )

        result = await db.execute(query, {"job_id": str(job_id)})
        await db.commit()

        updated = result.rowcount > 0

        if updated:
            log.info(
                "Job marked as done",
                extra={"event_type": "outbox_job_done", "job_id": str(job_id)},
            )

        return updated

    except Exception as e:
        await db.rollback()
        log.error(
            "Failed to mark job as done",
            extra={
                "event_type": "outbox_job_done_failed",
                "job_id": str(job_id),
                "error": str(e),
            },
        )
        raise
    finally:
        if close_db:
            await db.close()


async def mark_job_error(
    job_id: UUID,
    error_message: str,
    next_run_at: Optional[datetime] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """
    Mark a job as failed and optionally reschedule it

    Args:
        job_id: ID of the job to mark as failed
        error_message: Error description
        next_run_at: When to retry (None = no retry)
        db: Database session (optional)

    Returns:
        True if job was updated, False if not found
    """
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)"
            )
        )

        if next_run_at:
            # Reschedule for retry
            query = text(
                """
                UPDATE outbox_events 
                SET status = 'pending', 
                    attempts = attempts + 1, 
                    last_error = :error_message,
                    next_run_at = :next_run_at,
                    updated_at = now()
                WHERE id = :job_id
            """
            )
            params = {
                "job_id": str(job_id),
                "error_message": error_message,
                "next_run_at": next_run_at,
            }
        else:
            # Mark as failed without retry
            query = text(
                """
                UPDATE outbox_events 
                SET status = 'error', 
                    attempts = attempts + 1, 
                    last_error = :error_message,
                    updated_at = now()
                WHERE id = :job_id
            """
            )
            params = {"job_id": str(job_id), "error_message": error_message}

        result = await db.execute(query, params)
        await db.commit()

        updated = result.rowcount > 0

        if updated:
            log.warning(
                "Job marked as failed",
                extra={
                    "event_type": "outbox_job_failed",
                    "job_id": str(job_id),
                    "error": error_message,
                    "will_retry": next_run_at is not None,
                    "next_run_at": next_run_at.isoformat() if next_run_at else None,
                },
            )

        return updated

    except Exception as e:
        await db.rollback()
        log.error(
            "Failed to mark job as error",
            extra={
                "event_type": "outbox_job_error_failed",
                "job_id": str(job_id),
                "error": str(e),
            },
        )
        raise
    finally:
        if close_db:
            await db.close()


async def move_to_dlq(
    job_id: UUID, source: str, reason: str, db: Optional[AsyncSession] = None
) -> bool:
    """
    Move a job to the Dead Letter Queue

    Args:
        job_id: ID of the job to move to DLQ
        source: Source system/component
        reason: Reason for DLQ placement
        db: Database session (optional)

    Returns:
        True if job was moved to DLQ, False if not found
    """
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)"
            )
        )

        # First, get the job details
        job_query = text(
            """
            SELECT merchant_id, job_type, payload, attempts, last_error
            FROM outbox_events
            WHERE id = :job_id
        """
        )

        job_result = await db.execute(job_query, {"job_id": str(job_id)})
        job_row = job_result.fetchone()

        if not job_row:
            return False

        # Insert into DLQ
        dlq_payload = {
            "original_job_id": str(job_id),
            "job_type": job_row.job_type,
            "attempts": job_row.attempts,
            "last_error": job_row.last_error,
            "original_payload": (
                json.loads(job_row.payload)
                if isinstance(job_row.payload, str)
                else job_row.payload
            ),
        }

        dlq_query = text(
            """
            INSERT INTO dlq_events (merchant_id, source, key, reason, payload)
            VALUES (:merchant_id, :source, :key, :reason, :payload)
        """
        )

        await db.execute(
            dlq_query,
            {
                "merchant_id": str(job_row.merchant_id),
                "source": source,
                "key": str(job_id),
                "reason": reason,
                "payload": json.dumps(dlq_payload),
            },
        )

        # Mark original job as error
        update_query = text(
            """
            UPDATE outbox_events
            SET status = 'error', updated_at = now()
            WHERE id = :job_id
        """
        )

        await db.execute(update_query, {"job_id": str(job_id)})
        await db.commit()

        log.warning(
            "Job moved to DLQ",
            extra={
                "event_type": "dlq_job_moved",
                "job_id": str(job_id),
                "merchant_id": str(job_row.merchant_id),
                "source": source,
                "reason": reason,
                "attempts": job_row.attempts,
            },
        )

        return True

    except Exception as e:
        await db.rollback()
        log.error(
            "Failed to move job to DLQ",
            extra={
                "event_type": "dlq_move_failed",
                "job_id": str(job_id),
                "error": str(e),
            },
        )
        raise
    finally:
        if close_db:
            await db.close()


async def record_heartbeat(
    instance_id: str, details: Dict[str, Any], db: Optional[AsyncSession] = None
) -> bool:
    """
    Record worker heartbeat for leader election and monitoring

    Args:
        instance_id: Unique worker instance identifier
        details: Additional worker information
        db: Database session (optional)

    Returns:
        True if heartbeat was recorded successfully
    """
    close_db = False
    if db is None:
        db = WorkerSessionLocal()  # Use worker session with connection pooling
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)"
            )
        )

        query = text(
            """
            INSERT INTO worker_heartbeats (instance_id, seen_at, details)
            VALUES (:instance_id, now(), :details)
            ON CONFLICT (instance_id)
            DO UPDATE SET seen_at = now(), details = EXCLUDED.details
        """
        )

        await db.execute(
            query, {"instance_id": instance_id, "details": json.dumps(details)}
        )

        await db.commit()
        return True

    except Exception as e:
        await db.rollback()
        log.error(
            "Failed to record heartbeat",
            extra={
                "event_type": "worker_heartbeat_failed",
                "instance_id": instance_id,
                "error": str(e),
            },
        )
        return False
    finally:
        if close_db:
            await db.close()


async def acquire_leader_lock(
    lock_key: int, instance_id: str, db: Optional[AsyncSession] = None
) -> bool:
    """
    Try to acquire leader lock using PostgreSQL advisory locks

    Args:
        lock_key: Unique lock identifier
        instance_id: Worker instance ID
        db: Database session (optional)

    Returns:
        True if lock was acquired, False otherwise
    """
    close_db = False
    if db is None:
        db = WorkerSessionLocal()  # Use worker session with connection pooling
        close_db = True

    try:
        query = text("SELECT pg_try_advisory_lock(:lock_key)")
        result = await db.execute(query, {"lock_key": lock_key})
        acquired = result.scalar()

        if acquired:
            log.info(
                "Leader lock acquired",
                extra={
                    "event_type": "worker_leader_acquired",
                    "instance_id": instance_id,
                    "lock_key": lock_key,
                },
            )

        return bool(acquired)

    except asyncio.CancelledError:
        # Task was cancelled, don't log as error
        log.debug(
            "Leader lock acquisition cancelled",
            extra={
                "event_type": "worker_leader_acquire_cancelled",
                "instance_id": instance_id,
                "lock_key": lock_key,
            },
        )
        return False
    except Exception as e:
        log.error(
            "Failed to acquire leader lock",
            extra={
                "event_type": "worker_leader_acquire_failed",
                "instance_id": instance_id,
                "lock_key": lock_key,
                "error": str(e),
            },
        )
        return False
    finally:
        if close_db:
            await db.close()


async def release_leader_lock(
    lock_key: int, instance_id: str, db: Optional[AsyncSession] = None
) -> bool:
    """
    Release leader lock

    Args:
        lock_key: Lock identifier to release
        instance_id: Worker instance ID
        db: Database session (optional)

    Returns:
        True if lock was released successfully
    """
    close_db = False
    if db is None:
        db = WorkerSessionLocal()  # Use worker session with connection pooling
        close_db = True

    try:
        query = text("SELECT pg_advisory_unlock(:lock_key)")
        result = await db.execute(query, {"lock_key": lock_key})
        released = result.scalar()

        if released:
            log.info(
                "Leader lock released",
                extra={
                    "event_type": "worker_leader_released",
                    "instance_id": instance_id,
                    "lock_key": lock_key,
                },
            )

        return bool(released)

    except Exception as e:
        log.error(
            "Failed to release leader lock",
            extra={
                "event_type": "worker_leader_release_failed",
                "instance_id": instance_id,
                "lock_key": lock_key,
                "error": str(e),
            },
        )
        return False
    finally:
        if close_db:
            await db.close()


async def get_job_stats(
    merchant_id: Optional[UUID] = None,
    job_type: Optional[JobType] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Get outbox job statistics

    Args:
        merchant_id: Filter by merchant (optional)
        job_type: Filter by job type (optional)
        db: Database session (optional)

    Returns:
        Dictionary with job statistics
    """
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True

    try:
        # Set service role for RLS
        await db.execute(
            text(
                "SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)"
            )
        )

        where_clauses = []
        params = {}

        if merchant_id:
            where_clauses.append("merchant_id = :merchant_id")
            params["merchant_id"] = str(merchant_id)

        if job_type:
            where_clauses.append("job_type = :job_type")
            params["job_type"] = job_type.value

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = text(
            f"""
            SELECT 
                status,
                COUNT(*) as count,
                MIN(created_at) as oldest,
                MAX(created_at) as newest
            FROM outbox_events
            {where_sql}
            GROUP BY status
        """
        )

        result = await db.execute(query, params)
        rows = result.fetchall()

        stats = {
            "total": sum(row.count for row in rows),
            "by_status": {
                row.status: {
                    "count": row.count,
                    "oldest": row.oldest.isoformat() if row.oldest else None,
                    "newest": row.newest.isoformat() if row.newest else None,
                }
                for row in rows
            },
        }

        return stats

    except Exception as e:
        log.error(
            "Failed to get job stats",
            extra={"event_type": "outbox_stats_failed", "error": str(e)},
        )
        return {"total": 0, "by_status": {}}
    finally:
        if close_db:
            await db.close()
