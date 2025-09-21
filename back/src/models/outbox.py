"""
Outbox pattern models for Sayar WhatsApp Commerce Platform
Pydantic models for outbox events, DLQ events, and job handlers
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Awaitable, Callable, Union
from uuid import UUID
from datetime import datetime
from enum import Enum


class JobType(str, Enum):
    """Supported job types for outbox processing"""

    WA_SEND = "wa_send"
    CATALOG_SYNC = "catalog_sync"
    RELEASE_RESERVATION = "release_reservation"
    PAYMENT_FOLLOWUP = "payment_followup"


class JobStatus(str, Enum):
    """Job processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class OutboxEvent(BaseModel):
    """Outbox event model for job processing"""

    id: UUID
    merchant_id: UUID
    job_type: JobType
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    max_attempts: int = 8
    next_run_at: datetime
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateOutboxEvent(BaseModel):
    """Create outbox event request model"""

    merchant_id: UUID
    job_type: JobType
    payload: Dict[str, Any]
    max_attempts: int = Field(default=8, ge=1, le=20)
    run_at: Optional[datetime] = None


class DLQEvent(BaseModel):
    """Dead Letter Queue event model"""

    id: UUID
    merchant_id: Optional[UUID] = None
    source: str
    key: str
    reason: str
    payload: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat model for leader election and monitoring"""

    instance_id: str
    seen_at: datetime
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class JobResult(BaseModel):
    """Job execution result"""

    success: bool
    error: Optional[str] = None
    should_retry: bool = True
    next_run_at: Optional[datetime] = None


class RetryableError(Exception):
    """Exception that should trigger a retry"""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class FatalError(Exception):
    """Exception that should move job to DLQ immediately"""

    pass


# Type alias for job handler functions
JobFunc = Callable[[OutboxEvent], Awaitable[JobResult]]


class JobHandler(BaseModel):
    """Job handler configuration"""

    job_type: JobType
    handler_func: JobFunc
    max_attempts: int = 8
    base_delay: float = 1.0
    max_delay: float = 300.0

    class Config:
        arbitrary_types_allowed = True


class WorkerConfig(BaseModel):
    """Worker configuration"""

    enabled: bool = True
    heartbeat_interval: int = 10  # seconds
    batch_size: int = 50
    max_concurrent: int = 10
    lock_key: int = 7543219876543210
    poll_interval: int = 5  # seconds


class WorkerStats(BaseModel):
    """Worker statistics"""

    instance_id: str
    is_leader: bool
    jobs_processed: int = 0
    jobs_failed: int = 0
    last_heartbeat: Optional[datetime] = None
    uptime_seconds: Optional[float] = None
    current_batch_size: int = 0
