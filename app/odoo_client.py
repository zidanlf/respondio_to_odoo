"""Class-based Odoo XML-RPC client with idempotent upsert."""

import logging
import xmlrpc.client
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class OdooAuthError(Exception):
    """Raised when Odoo authentication fails."""


class OdooClient:
    """Thin wrapper around Odoo's XML-RPC API."""

    RESPONDIO_FIELD = "x_studio_respondio_id"
    FUNNEL_STAGE_FIELD = "x_studio_conversion_funnel_stage_1"
    LEAD_CHANNEL_MODEL = "x_lead_channel"

    def __init__(self) -> None:
        settings = get_settings()
        self._url = settings.ODOO_URL
        self._db = settings.ODOO_DB
        self._username = settings.ODOO_USERNAME
        self._api_key = settings.ODOO_API_KEY
        self._uid: Optional[int] = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def _authenticate(self) -> int:
        """Authenticate and cache the UID. Raises OdooAuthError on failure."""
        if self._uid:
            return self._uid

        try:
            common = xmlrpc.client.ServerProxy(
                f"{self._url}/xmlrpc/2/common"
            )
            uid = common.authenticate(
                self._db, self._username, self._api_key, {}
            )
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.error("Cannot reach Odoo at %s: %s", self._url, exc)
            raise OdooAuthError(f"Connection to Odoo failed: {exc}") from exc

        if not uid:
            logger.error(
                "Odoo authentication failed for user %s", self._username
            )
            raise OdooAuthError("Invalid Odoo credentials")

        self._uid = uid
        logger.info("Odoo authenticated — UID %s", uid)
        return uid

    def _models(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")

    # ------------------------------------------------------------------
    # Core CRUD helpers (generic — accept any model)
    # ------------------------------------------------------------------
    def _search(self, model: str, domain: list) -> list[int]:
        uid = self._authenticate()
        return self._models().execute_kw(
            self._db, uid, self._api_key,
            model, "search", [domain],
        )

    def _create(self, model: str, vals: dict) -> int:
        uid = self._authenticate()
        return self._models().execute_kw(
            self._db, uid, self._api_key,
            model, "create", [vals],
        )

    def _write(self, model: str, record_id: int, vals: dict) -> bool:
        uid = self._authenticate()
        return self._models().execute_kw(
            self._db, uid, self._api_key,
            model, "write", [[record_id], vals],
        )

    # ------------------------------------------------------------------
    # Many2one helpers
    # ------------------------------------------------------------------
    def _resolve_many2one(
        self, model: str, value: str, name_field: str = "name",
    ) -> Optional[int]:
        """
        Search for a record by its name/label field in the given model.
        Returns the record ID if found, otherwise None.
        """
        try:
            ids = self._search(model, [[name_field, "=", value]])
            if ids:
                logger.info(
                    "Resolved '%s' in %s.%s → ID %s",
                    value, model, name_field, ids[0],
                )
                return ids[0]
            logger.warning(
                "No record with %s='%s' found in %s",
                name_field, value, model,
            )
        except xmlrpc.client.Fault as exc:
            logger.error(
                "Failed to search %s for %s='%s': %s",
                model, name_field, value, exc,
            )
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upsert_contact(
        self,
        respondio_id: str,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        funnel_stage: Optional[str] = None,
    ) -> int:
        """
        Idempotent upsert: search by x_studio_respondio_id, then update or
        create.  Returns the Odoo partner ID.
        """
        domain = [[self.RESPONDIO_FIELD, "=", respondio_id]]

        try:
            partner_ids = self._search("res.partner", domain)
        except xmlrpc.client.Fault as exc:
            logger.error(
                "Odoo search failed (field '%s' may not exist): %s",
                self.RESPONDIO_FIELD, exc,
            )
            raise

        vals: dict = {
            "name": name,
            self.RESPONDIO_FIELD: respondio_id,
        }
        if phone:
            vals["phone"] = phone
        if email:
            vals["email"] = email

        # Resolve Many2one: look up Lead Channel ID by x_name
        if funnel_stage:
            channel_id = self._resolve_many2one(
                self.LEAD_CHANNEL_MODEL, funnel_stage,
                name_field="x_name",
            )
            if channel_id:
                vals[self.FUNNEL_STAGE_FIELD] = channel_id
            else:
                logger.warning(
                    "Skipping funnel_stage '%s' — not found in %s",
                    funnel_stage, self.LEAD_CHANNEL_MODEL,
                )

        if partner_ids:
            partner_id = partner_ids[0]
            try:
                self._write("res.partner", partner_id, vals)
                logger.info(
                    "Updated Partner %s for Respond.io ID %s",
                    partner_id, respondio_id,
                )
            except xmlrpc.client.Fault as exc:
                logger.error("Odoo write failed: %s", exc)
                raise
            return partner_id

        # Create new
        try:
            partner_id = self._create("res.partner", vals)
            logger.info(
                "Created Partner %s for Respond.io ID %s",
                partner_id, respondio_id,
            )
        except xmlrpc.client.Fault as exc:
            logger.error("Odoo create failed: %s", exc)
            raise

        return partner_id


