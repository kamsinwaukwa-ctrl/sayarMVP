"""
WhatsApp webhook endpoints for receiving messages and status updates
SQL-first approach with PGP encryption and database-managed security
"""

import json
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, HTTPException, Depends, Query, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database.connection import get_db
from ..utils.logger import get_logger
from ..utils.outbox import enqueue_job, JobType
from ..utils.db_session import DatabaseSessionHelper

logger = get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


async def get_webhook_with_merchant(app_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get webhook configuration with merchant_id by app_id"""
    result = await db.execute(
        text("""
            SELECT
                id,
                merchant_id,
                provider,
                active,
                phone_number_id,
                waba_id
            FROM webhook_endpoints
            WHERE app_id = :app_id
            LIMIT 1
        """),
        {"app_id": app_id}
    )
    row = result.fetchone()
    return dict(row._mapping) if row else None


def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Verify WhatsApp webhook signature (X-Hub-Signature-256)"""
    try:
        # WhatsApp signature format: sha256=<signature>
        if signature.startswith("sha256="):
            signature = signature[7:]

        # Calculate expected signature
        expected_sig = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected_sig, signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False


@router.get("/whatsapp/app/{app_id}")
async def handle_webhook_verification(
    app_id: str,
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle WhatsApp webhook verification (hub.challenge)
    Called by Meta when setting up webhook URL
    Uses SQL crypt() function to verify token without storing plaintext
    """
    logger.info(
        "Webhook verification request",
        extra={
            "app_id": app_id,
            "hub_mode": hub_mode,
            "event": "webhook_verification_request",
        }
    )

    # Verify mode is 'subscribe'
    if hub_mode != "subscribe":
        logger.warning(
            "Invalid hub.mode",
            extra={
                "app_id": app_id,
                "hub_mode": hub_mode,
                "event": "webhook_verification_failed",
            }
        )
        raise HTTPException(status_code=403, detail="Invalid hub.mode")

    # SQL-based token verification using crypt() - no Python bcrypt needed
    result = await db.execute(
        text("""
            SELECT
                verify_token_hash = crypt(:token, verify_token_hash) as matches,
                active,
                merchant_id
            FROM webhook_endpoints
            WHERE app_id = :app_id
        """),
        {"token": hub_verify_token, "app_id": app_id}
    )

    row = result.fetchone()

    if not row:
        logger.warning(
            "Webhook configuration not found",
            extra={
                "app_id": app_id,
                "event": "webhook_verification_failed",
            }
        )
        raise HTTPException(status_code=404, detail="Webhook not configured")

    if not row.matches:
        logger.warning(
            "Invalid verify token",
            extra={
                "app_id": app_id,
                "merchant_id": str(row.merchant_id),
                "event": "webhook_verification_failed",
            }
        )
        raise HTTPException(status_code=401, detail="Invalid verify token")

    if not row.active:
        logger.warning(
            "Webhook disabled",
            extra={
                "app_id": app_id,
                "merchant_id": str(row.merchant_id),
                "event": "webhook_verification_failed",
            }
        )
        raise HTTPException(status_code=403, detail="Webhook disabled")

    logger.info(
        "Webhook verification successful",
        extra={
            "app_id": app_id,
            "merchant_id": str(row.merchant_id),
            "event": "webhook_verification_success",
        }
    )

    # Return the challenge to verify the webhook
    return PlainTextResponse(content=hub_challenge, status_code=200)


@router.post("/whatsapp/app/{app_id}")
async def handle_webhook_notification(
    app_id: str,
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="x-hub-signature-256"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle WhatsApp webhook notifications (messages, status updates)
    Called by Meta when events occur
    Uses SQL PGP decryption for app_secret and proper raw body handling
    """
    # CRITICAL: Read raw body ONCE before any parsing for signature verification
    raw_body = await request.body()

    # Get webhook configuration with merchant info
    webhook = await get_webhook_with_merchant(app_id, db)
    if not webhook:
        logger.warning(
            "Webhook configuration not found",
            extra={
                "app_id": app_id,
                "event": "webhook_notification_rejected",
            }
        )
        # Return 200 to prevent retries, but log the issue
        return Response(status_code=200)

    # Check if webhook is active
    if not webhook["active"]:
        logger.warning(
            "Webhook disabled",
            extra={
                "app_id": app_id,
                "merchant_id": str(webhook["merchant_id"]),
                "event": "webhook_notification_rejected_disabled",
            }
        )
        return Response(status_code=403)  # Webhook disabled

    # Verify signature if provided
    if x_hub_signature_256:
        # Set encryption key for this session
        await DatabaseSessionHelper.set_encryption_key(db)

        # Decrypt app_secret using SQL PGP function
        secret_result = await db.execute(
            text("""
                SELECT pgp_sym_decrypt(
                    app_secret_encrypted::bytea,
                    current_setting('app.encryption_key')
                ) as secret
                FROM webhook_endpoints
                WHERE app_id = :app_id AND active = true
            """),
            {"app_id": app_id}
        )

        app_secret = secret_result.scalar()
        if not app_secret:
            logger.error(
                "Failed to decrypt app secret",
                extra={
                    "app_id": app_id,
                    "event": "webhook_secret_decrypt_failed",
                }
            )
            return Response(status_code=200)  # Silent fail

        # NEVER log the decrypted secret!

        if not verify_signature(raw_body, x_hub_signature_256, app_secret):
            # Increment failure count
            await db.execute(
                text("""
                    UPDATE webhook_endpoints
                    SET signature_fail_count = signature_fail_count + 1,
                        updated_at = NOW()
                    WHERE app_id = :app_id
                """),
                {"app_id": app_id}
            )
            await db.commit()

            logger.warning(
                "Invalid webhook signature",
                extra={
                    "app_id": app_id,
                    "merchant_id": str(webhook["merchant_id"]),
                    "event": "webhook_signature_failed",
                }
            )
            return Response(status_code=401)  # Bad signature

    # Parse the webhook payload from raw body
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in webhook payload",
            extra={
                "app_id": app_id,
                "merchant_id": str(webhook["merchant_id"]),
                "error": str(e),
                "event": "webhook_parse_failed",
            }
        )
        return Response(status_code=200)

    # Update last webhook timestamp
    await db.execute(
        text("""
            UPDATE webhook_endpoints
            SET last_webhook_at = NOW(),
                updated_at = NOW()
            WHERE app_id = :app_id
        """),
        {"app_id": app_id}
    )

    # Log webhook received
    logger.info(
        "Webhook notification received",
        extra={
            "app_id": app_id,
            "merchant_id": str(webhook["merchant_id"]),
            "phone_number_id": webhook["phone_number_id"],
            "waba_id": webhook["waba_id"],
            "event": "webhook_notification_received",
        }
    )

    # Process webhook entries
    for entry in payload.get("entry", []):
        # Extract WhatsApp Business Account ID from entry
        waba_id = entry.get("id")

        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            # Determine job type based on field
            if field == "messages":
                # Handle incoming messages
                messages = value.get("messages", [])
                for message in messages:
                    await enqueue_job(
                        db,
                        JobType.PROCESS_WHATSAPP_MESSAGE,
                        {
                            "merchant_id": str(webhook["merchant_id"]),
                            "phone_number_id": webhook["phone_number_id"],
                            "waba_id": waba_id,
                            "message": message,
                            "metadata": value.get("metadata", {}),
                            "contacts": value.get("contacts", []),
                        }
                    )

            elif field == "message_template_status_update":
                # Handle template status updates
                await enqueue_job(
                    db,
                    JobType.PROCESS_WHATSAPP_TEMPLATE_UPDATE,
                    {
                        "merchant_id": str(webhook["merchant_id"]),
                        "phone_number_id": webhook["phone_number_id"],
                        "waba_id": waba_id,
                        "template_update": value,
                    }
                )

            elif field == "messages_status":
                # Handle message status updates (delivered, read, failed)
                statuses = value.get("statuses", [])
                for status_update in statuses:
                    await enqueue_job(
                        db,
                        JobType.PROCESS_WHATSAPP_STATUS,
                        {
                            "merchant_id": str(webhook["merchant_id"]),
                            "phone_number_id": webhook["phone_number_id"],
                            "waba_id": waba_id,
                            "status": status_update,
                        }
                    )

    await db.commit()

    # Always return 200 to acknowledge receipt
    return Response(status_code=200)


@router.get("/whatsapp/health")
async def webhook_health():
    """Health check endpoint for webhook service"""
    return {
        "status": "healthy",
        "service": "whatsapp_webhooks",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }