"""FastAPI entry point — webhook receiver."""

import logging

from fastapi import FastAPI, Request

from app.schemas import WebhookPayload, WebhookResponse
from app.tasks import sync_contact_to_odoo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Respond.io → Odoo Bridge",
    version="2.0.0",
    description="Lean webhook bridge that syncs Respond.io contacts into Odoo.",
)


@app.get("/health")
async def health():
    """Liveness / readiness probe for Docker."""
    return {"status": "ok"}


@app.api_route("/webhook", methods=["GET", "POST", "HEAD"])
async def handle_webhook(request: Request):
    """
    Receive webhook, log raw data for debugging, and process.
    Supports GET/HEAD for verification and POST for data.
    """
    if request.method in ["GET", "HEAD"]:
        logger.info(f"Verification ping received: {request.method}")
        return {"status": "ok", "message": "Webhook endpoint is active"}

    try:
        # 1. Capture Raw Body
        body = await request.json()
        logger.info(f"RAW WEBHOOK RECEIVED: {body}")

        # 2. Manual Validation via Schema
        try:
            payload = WebhookPayload(**body)
            contact = payload.extract_contact()
        except Exception as exc:
            logger.warning(f"Validation failed for body below. Error: {exc}")
            # We return 200 anyway to prevent Respond.io from retrying 
            # while we debug, but we don't queue the task.
            return {"status": "invalid_payload", "error": str(exc)}

        logger.info(f"Webhook validated — queueing contact {contact.id}")

        # Dispatch to Celery (async)
        sync_contact_to_odoo.delay(contact.model_dump())

        return WebhookResponse(status="queued", respondio_id=contact.id)

    except Exception as e:
        logger.error(f"Error in handle_webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
