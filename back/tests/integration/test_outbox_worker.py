"""
Integration tests for outbox worker functionality
Tests job processing, leader election, retry logic, and DLQ behavior
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch

from src.models.outbox import JobType, CreateOutboxEvent
from src.utils.outbox import enqueue_job
from src.workers.outbox_worker import OutboxWorker
from src.database.connection import get_db_session


@pytest.mark.asyncio
class TestOutboxWorkerIntegration:
    """Integration tests for outbox worker functionality"""
    
    async def test_worker_enqueue_and_process_job(self, test_db):
        """Test that a job can be enqueued and processed successfully"""
        # Create a test job
        merchant_id = uuid4()
        job_payload = {
            "to": "+2348012345678",
            "type": "text",
            "content": {"text": "Test message"}
        }
        
        # Enqueue the job
        job_id = await enqueue_job(
            merchant_id=merchant_id,
            job_type=JobType.WA_SEND,
            payload=job_payload,
            max_attempts=3
        )
        
        # Create and start worker
        worker = OutboxWorker()
        worker.config.batch_size = 10
        worker.config.max_concurrent = 5
        worker.config.poll_interval = 1
        
        # Mock leader election to always succeed
        with patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=True)):
            
            # Process jobs
            await worker._process_due_jobs()
            
            # Verify job was processed
            async with get_db_session() as db:
                # Set service role for RLS
                await db.execute("SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)")
                
                # Check job status
                result = await db.execute(
                    "SELECT status, attempts FROM outbox_events WHERE id = :job_id",
                    {"job_id": str(job_id)}
                )
                job = result.fetchone()
                
                assert job is not None
                assert job.status == "done"  # Should be marked as done
                assert job.attempts == 1     # Should have 1 attempt (successful)
    
    async def test_worker_retry_logic(self, test_db):
        """Test that failed jobs are retried with exponential backoff"""
        merchant_id = uuid4()
        
        # Enqueue a job
        job_id = await enqueue_job(
            merchant_id=merchant_id,
            job_type=JobType.WA_SEND,
            payload={"to": "+2348012345678"},
            max_attempts=3
        )
        
        worker = OutboxWorker()
        
        # Mock the handler to fail
        with patch('src.workers.job_handlers.handle_wa_send', 
                  AsyncMock(return_value={
                      "success": False, 
                      "error": "Simulated failure", 
                      "should_retry": True
                  })), \
             patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=True)):
            
            await worker._process_due_jobs()
            
            # Verify job was marked for retry
            async with get_db_session() as db:
                await db.execute("SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)")
                
                result = await db.execute(
                    "SELECT status, attempts, next_run_at FROM outbox_events WHERE id = :job_id",
                    {"job_id": str(job_id)}
                )
                job = result.fetchone()
                
                assert job.status == "pending"  # Should be pending for retry
                assert job.attempts == 1        # Should have 1 attempt
                assert job.next_run_at > datetime.now()  # Should be scheduled for future
    
    async def test_worker_dlq_behavior(self, test_db):
        """Test that jobs exceeding max attempts are moved to DLQ"""
        merchant_id = uuid4()
        
        # Enqueue a job with only 1 max attempt
        job_id = await enqueue_job(
            merchant_id=merchant_id,
            job_type=JobType.WA_SEND,
            payload={"to": "+2348012345678"},
            max_attempts=1  # Only 1 attempt allowed
        )
        
        worker = OutboxWorker()
        
        # Mock the handler to fail (should go directly to DLQ)
        with patch('src.workers.job_handlers.handle_wa_send', 
                  AsyncMock(return_value={
                      "success": False, 
                      "error": "Fatal error", 
                      "should_retry": False  # Fatal error, no retry
                  })), \
             patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=True)):
            
            await worker._process_due_jobs()
            
            # Verify job was moved to DLQ
            async with get_db_session() as db:
                await db.execute("SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)")
                
                # Check DLQ
                dlq_result = await db.execute(
                    "SELECT COUNT(*) FROM dlq_events WHERE key = :job_id",
                    {"job_id": str(job_id)}
                )
                dlq_count = dlq_result.scalar()
                
                # Check outbox status
                outbox_result = await db.execute(
                    "SELECT status FROM outbox_events WHERE id = :job_id",
                    {"job_id": str(job_id)}
                )
                outbox_status = outbox_result.scalar()
                
                assert dlq_count == 1           # Should be in DLQ
                assert outbox_status == "error"  # Should be marked as error
    
    async def test_worker_leader_election(self, test_db):
        """Test leader election behavior"""
        worker = OutboxWorker()
        
        # Test acquiring leader lock
        with patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=True)):
            
            await worker._poll_and_process_jobs()
            assert worker.is_leader == True
        
        # Test failing to acquire leader lock
        worker.is_leader = False
        with patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=False)):
            
            await worker._poll_and_process_jobs()
            assert worker.is_leader == False
    
    async def test_worker_concurrent_processing(self, test_db):
        """Test that worker respects max_concurrent setting"""
        merchant_id = uuid4()
        
        # Enqueue multiple jobs
        job_ids = []
        for i in range(5):
            job_id = await enqueue_job(
                merchant_id=merchant_id,
                job_type=JobType.WA_SEND,
                payload={"to": f"+234801234567{i}"},
                max_attempts=3
            )
            job_ids.append(job_id)
        
        worker = OutboxWorker()
        worker.config.max_concurrent = 2  # Limit to 2 concurrent jobs
        
        processing_semaphore = None
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        
        original_process = worker._process_job_with_semaphore
        
        async def mock_process_with_semaphore(job, semaphore):
            nonlocal concurrent_count, max_concurrent
            async with semaphore:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                # Simulate processing time
                await asyncio.sleep(0.1)
                await worker._process_job(job)
                concurrent_count -= 1
        
        with patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=True)), \
             patch.object(worker, '_process_job_with_semaphore', mock_process_with_semaphore):
            
            await worker._process_due_jobs()
            
            # Verify that max concurrent never exceeded the limit
            assert max_concurrent <= worker.config.max_concurrent
    
    async def test_job_handler_registry(self):
        """Test that all job types have registered handlers"""
        from src.workers.job_handlers import get_job_handler, JOB_HANDLERS
        
        # Test that all job types have handlers
        for job_type in JobType:
            handler = get_job_handler(job_type)
            assert handler is not None
            assert callable(handler)
            assert job_type in JOB_HANDLERS
    
    async def test_worker_metrics(self, test_db):
        """Test that metrics are properly recorded"""
        from src.utils.metrics import outbox_jobs_processed_total
        
        merchant_id = uuid4()
        
        # Enqueue a job
        job_id = await enqueue_job(
            merchant_id=merchant_id,
            job_type=JobType.WA_SEND,
            payload={"to": "+2348012345678"},
            max_attempts=3
        )
        
        worker = OutboxWorker()
        
        # Get initial metric value
        initial_count = outbox_jobs_processed_total.labels(job_type="wa_send")._value.get()
        
        with patch('src.workers.outbox_worker.acquire_leader_lock', 
                  AsyncMock(return_value=True)):
            
            await worker._process_due_jobs()
            
            # Verify metric was incremented
            final_count = outbox_jobs_processed_total.labels(job_type="wa_send")._value.get()
            assert final_count == initial_count + 1


@pytest.mark.asyncio
class TestOutboxUtilsIntegration:
    """Integration tests for outbox utility functions"""
    
    async def test_enqueue_job(self, test_db):
        """Test job enqueueing functionality"""
        merchant_id = uuid4()
        
        job_id = await enqueue_job(
            merchant_id=merchant_id,
            job_type=JobType.CATALOG_SYNC,
            payload={"product_ids": ["prod1", "prod2"]},
            max_attempts=5
        )
        
        assert isinstance(job_id, UUID)
        
        # Verify job was created in database
        async with get_db_session() as db:
            await db.execute("SELECT set_config('request.jwt.claims', '{\"role\":\"service\"}', true)")
            
            result = await db.execute(
                "SELECT merchant_id, job_type, status, max_attempts FROM outbox_events WHERE id = :job_id",
                {"job_id": str(job_id)}
            )
            job = result.fetchone()
            
            assert job is not None
            assert str(job.merchant_id) == str(merchant_id)
            assert job.job_type == "catalog_sync"
            assert job.status == "pending"
            assert job.max_attempts == 5
    
    async def test_fetch_due_jobs(self, test_db):
        """Test fetching due jobs with SKIP LOCKED"""
        merchant_id = uuid4()
        
        # Enqueue a job
        await enqueue_job(
            merchant_id=merchant_id,
            job_type=JobType.RELEASE_RESERVATION,
            payload={"reservation_id": "res123", "quantity": 2},
            max_attempts=3
        )
        
        # Fetch due jobs
        jobs = await fetch_due_jobs(batch_size=10)
        
        assert len(jobs) >= 1
        job = jobs[0]
        assert job.job_type == JobType.RELEASE_RESERVATION
        assert job.status.name == "PROCESSING"  # Should be marked as processing
        assert job.merchant_id == merchant_id