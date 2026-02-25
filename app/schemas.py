"""Pydantic models for Respond.io webhook payloads."""

from typing import Annotated, Optional, Union
from pydantic import BaseModel, BeforeValidator, Field


def _coerce_to_str(v):
    """Coerce int/float IDs to str so Pydantic doesn't reject them."""
    return str(v) if v is not None else v


CoercedStr = Annotated[str, BeforeValidator(_coerce_to_str)]


class RespondioContact(BaseModel):
    """Core contact fields from Respond.io."""

    id: CoercedStr = Field(..., description="Respond.io contact ID")
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phoneNumber: Optional[str] = None
    phone: Optional[str] = None  # Added: Respond.io sometimes uses 'phone' instead of 'phoneNumber'
    email: Optional[str] = None
    tags: Optional[list[str]] = None

    def get_phone(self) -> Optional[str]:
        """Return phoneNumber if present, otherwise phone."""
        return self.phoneNumber or self.phone


class WebhookData(BaseModel):
    """Nested data wrapper — Respond.io sometimes sends {data: {contact: ...}}."""

    contact: Optional[RespondioContact] = None


class WebhookPayload(BaseModel):
    """
    Flexible payload model that handles multiple Respond.io webhook shapes:
      - Flat:   {"id": "...", "firstName": "...", ...}
      - Nested: {"data": {"contact": {"id": "...", ...}}}
      - Root:   {"contact": {"id": "...", ...}} (from Respond.io sample)
      - Tag:    {"contact": {..., "tags": [...]}, "tag": "...", "action": "...", "event_type": "contact.tag.updated"}
    """

    # Flat fields
    id: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phoneNumber: Optional[str] = None
    phone: Optional[str] = None

    # Nested wrappers
    data: Optional[WebhookData] = None
    contact: Optional[RespondioContact] = None  # handle sample structure

    # Tag-update event fields
    tag: Optional[str] = None
    action: Optional[str] = None
    event_type: Optional[str] = None

    def extract_contact(self) -> RespondioContact:
        """Resolve the actual contact regardless of payload shape."""
        # 1. Prefer root-level contact object (from user sample)
        if self.contact:
            return self.contact

        # 2. Check nested data.contact
        if self.data and self.data.contact:
            return self.data.contact

        # 3. Fall back to flat fields
        if self.id:
            return RespondioContact(
                id=str(self.id), # Force string
                firstName=self.firstName,
                lastName=self.lastName,
                phoneNumber=self.phoneNumber,
                phone=self.phone
            )

        raise ValueError("Payload contains no valid contact data")


class WebhookResponse(BaseModel):
    """Standardized API response."""

    status: str
    respondio_id: Optional[str] = None
    message: Optional[str] = None
