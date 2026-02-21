"""Data transformation utilities."""

import logging
from typing import Optional

import phonenumbers

logger = logging.getLogger(__name__)


def format_phone_e164(phone_str: Optional[str], default_region: str = "ID") -> Optional[str]:
    """
    Format a phone string to E.164.

    Args:
        phone_str: Raw phone number (e.g. "08123456789", "+628123456789").
        default_region: ISO 3166-1 alpha-2 fallback when no country code is
                        present.  Defaults to Indonesia ("ID").

    Returns:
        E.164 formatted string (e.g. "+628123456789") or None on failure.
    """
    if not phone_str:
        return None

    try:
        parsed = phonenumbers.parse(phone_str, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        logger.warning("Invalid phone number after parsing: %s", phone_str)
    except phonenumbers.NumberParseException as exc:
        logger.warning("Cannot parse phone number '%s': %s", phone_str, exc)

    return None
