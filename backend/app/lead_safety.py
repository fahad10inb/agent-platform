"""Deterministic lead-capture safety net — the real 'never lose a lead' guarantee.

Prompt-level capture (`capture_lead`) is stochastic and intermittently misses: a
model hiccup — an empty reply that trips the recovery path, a skipped tool call —
silently loses a lead, which breaks the whole promise. Live QA proved it happens.

So this runs in the BACKGROUND after every turn: if the caller left a phone number
but no lead (and no booking) exists for it, capture it — deterministically, no
matter what the model did or didn't do. The tool stays the primary path; this only
ever fires when the tool DIDN'T, and never duplicates an existing lead/booking.
"""

import logging
import re

from app import db
from app.phone import to_wa_number

logger = logging.getLogger("agent-platform")

# Only where capturing a lead is the goal. Clinics/salons BOOK (a booking already
# records the caller); real estate (the pilot) and general businesses capture leads.
_LEAD_VERTICALS = ("real_estate", "general")

# A UAE mobile in free text: optional +971/00971/0 prefix, then a 9-digit national
# number starting with 5, with spaces/dashes allowed between digits.
_UAE_MOBILE = re.compile(r"(?:\+?971|00971|0)?[\s\-]?5\d(?:[\s\-]?\d){7}")
_NAME = re.compile(
    r"(?:i'?m|my name is|name'?s|this is|it'?s)\s+([A-Za-z][a-z]+(?:\s[A-Z][a-z]+)?)",
    re.I,
)
_NOT_NAMES = {"interested", "looking", "just", "not", "here", "trying", "keen", "ready"}


def _find_phone(text: str) -> str:
    """The first UAE mobile in the text as E.164 digits (971…), or ''."""
    for cand in _UAE_MOBILE.findall(text or ""):
        wa = to_wa_number(cand)
        if re.fullmatch(r"9715\d{8}", wa):
            return wa
    return ""


def _guess_name(text: str) -> str:
    """Best-effort first/full name from 'I'm X' / 'my name is X' (bonus — the
    phone is what actually matters). '' when we can't tell."""
    m = _NAME.search(text or "")
    if not m:
        return ""
    name = m.group(1).strip()
    return "" if name.lower() in _NOT_NAMES else name.title()


def ensure_lead_captured(business: dict, conversation_id: str) -> bool:
    """If the caller gave a phone but no lead/booking exists for it, capture it.
    Deterministic backstop to the stochastic capture_lead tool. Returns True if it
    captured one. Best-effort — never raises into the caller's request."""
    try:
        if (business.get("vertical") or "") not in _LEAD_VERTICALS:
            return False
        bid = business["id"]
        history = db.get_history(bid, conversation_id, limit=40)
        user_msgs = [m.get("text", "") for m in history if m.get("role") == "user"]
        text = " ".join(user_msgs)
        phone = _find_phone(text)
        if not phone:
            return False
        # Already handled: the tool captured it, or they've booked (also recorded).
        if db.find_recent_lead(bid, phone) or db.phone_has_booking(bid, phone):
            return False
        # '(auto)' in the name lets the owner tell a net-caught lead from a
        # tool-caught one at a glance (the notes field says so too).
        name = _guess_name(text) or "New enquiry (auto)"
        interest = (user_msgs[-1][:200] if user_msgs else "") or "enquiry"
        db.save_lead(bid, name, phone, interest, "auto-captured by the lead safety net")
        logger.info("[lead-safety] auto-captured a lead for business=%s", bid)
        return True
    except Exception:  # noqa: BLE001 — a safety net must never break the turn
        logger.exception("[lead-safety] failed for business=%s", business.get("id"))
        return False
