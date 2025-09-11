"""
Job handlers for outbox worker.
"""
from typing import Any, Dict, Callable, Optional
from datetime import datetime

from src.models.outbox import JobType
from src.models.errors import RetryableError, RateLimitedError
from src.utils.wa_rate_limiter import check_wa_rate_limit
from src.utils.logger import get_logger
from src.integrations.whatsapp import send_whatsapp_message

logger = get_logger(__name__)

async def handle_wa_send(
    merchant_id: str,
    payload: Dict[str, Any],
    wa_rate_limit_per_hour: int = 1000
) -> None:
    """Handle WhatsApp message sending with rate limiting."""
    # Check rate limit before sending
    try:
        await check_wa_rate_limit(merchant_id, wa_rate_limit_per_hour)
    except RateLimitedError as e:
        # If rate limited, reschedule the job
        logger.info(
            "wa_send_rescheduled",
            extra={
                "merchant_id": merchant_id,
                "next_run_at": e.details["reset_time"]
            }
        )
        # Re-raise as RetryableError to trigger job rescheduling
        raise RetryableError(
            message=e.message,
            next_run_at=datetime.fromisoformat(e.details["reset_time"])
        )
    
    # Rate limit passed, send the message
    await send_whatsapp_message(
        to=payload["to"],
        message_type=payload["type"],
        content=payload["content"]
    )

# Map job types to their handlers
JOB_HANDLERS = {
    JobType.WA_SEND: handle_wa_send,
    # Add other job handlers here
}

def get_job_handler(job_type: JobType) -> Optional[Callable]:
    """
    Get handler function for job type
    
    Args:
        job_type: Type of job to handle
        
    Returns:
        Handler function if available, None if no handler found
    """
    return JOB_HANDLERS.get(job_type)