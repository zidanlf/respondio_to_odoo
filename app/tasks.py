"""Celery tasks for async Odoo synchronization."""

import logging

from celery import Celery

from app.config import get_settings
from app.odoo_client import OdooClient, OdooAuthError
from app.schemas import RespondioContact
from app.transform import format_phone_e164

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Celery app ────────────────────────────────────────────────────────
celery_app = Celery(
    "respondio_odoo",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    task_track_started=True,
    task_acks_late=True,                     # re-deliver if worker dies
    worker_prefetch_multiplier=1,            # one task at a time per worker
)


# ── Tasks ─────────────────────────────────────────────────────────────
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,                   # seconds, grows with backoff
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=60,
)
def sync_contact_to_odoo(self, contact_dict: dict) -> dict:
    """
    Receive a validated contact dict, transform it, and upsert into Odoo.

    Retries automatically on transient network / timeout errors.
    """
    # Pop extra fields injected by the webhook handler
    funnel_stage = contact_dict.pop("funnel_stage", None)

    try:
        contact = RespondioContact(**contact_dict)
    except Exception as exc:
        logger.error("Invalid contact payload: %s — %s", contact_dict, exc)
        return {"status": "error", "detail": str(exc)}

    # ── Build name ────────────────────────────────────────────────
    first = contact.firstName or ""
    last = contact.lastName or ""
    name = f"{first} {last}".strip() or "Respond.io User"

    # ── Transform phone ───────────────────────────────────────────
    phone = format_phone_e164(contact.get_phone())

    # ── Upsert ────────────────────────────────────────────────────
    logger.info("Syncing contact %s (%s) to Odoo…", contact.id, name)
    try:
        client = OdooClient()
        partner_id = client.upsert_contact(
            respondio_id=contact.id,
            name=name,
            phone=phone,
            email=contact.email,
            funnel_stage=funnel_stage,
        )
        return {"status": "ok", "partner_id": partner_id}

    except OdooAuthError as exc:
        logger.error("Auth error — will not retry: %s", exc)
        return {"status": "auth_error", "detail": str(exc)}

