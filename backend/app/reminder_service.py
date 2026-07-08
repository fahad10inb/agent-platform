"""
Appointment reminders — the retention feature that attacks no-shows.

A lightweight in-process sweep (no cron, no queue — the same zero-infra pattern
as the weekly digest) wakes periodically, finds bookings coming up in ~24h and
~2h, and messages the caller: "your appointment is tomorrow at 2 PM — reply to
confirm or reschedule." Each (booking, stage) is CLAIMED via a UNIQUE row before
sending, so no caller is ever messaged twice for the same stage.

Delivery reuses the WhatsApp channel when the business has it connected and the
caller left a mobile; otherwise the reminder is logged (the same graceful
degradation as owner notifications without a Resend key), so the feature is
safe to ship before every tenant has WhatsApp live.
"""

import datetime
import logging
import re
import zoneinfo

from app import db
from app.config import get_settings
from app.phone import to_wa_number as _to_wa_number

logger = logging.getLogger("agent-platform.reminders")

_DUBAI_TZ = zoneinfo.ZoneInfo("Asia/Dubai")

# (stage label, the hour threshold at or under which that stage is due). Order
# matters: the nearest threshold wins, so a booking 1 hour out is a "2h", not a
# stale "24h". A booking booked same-day skips straight to whichever stage fits.
_STAGES = (("2h", 2), ("24h", 24))


def _now() -> datetime.datetime:
    """Dubai now — a seam the tests freeze."""
    return datetime.datetime.now(_DUBAI_TZ)


def _time_to_minutes(label: str):
    """'2:00 PM' / '2 PM' / '14:00' -> minutes since midnight, or None."""
    s = (label or "").strip().upper().replace(".", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$", s)
    if not m:
        return None
    h, mins, suffix = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if h > 24 or mins > 59:
        return None
    if suffix == "AM":
        h = 0 if h == 12 else h
    elif suffix == "PM":
        h = h if h == 12 else h + 12
    return h * 60 + mins


def _booking_datetime(date_str: str, time_str: str):
    """Combine an ISO date + a slot label into a Dubai-aware datetime, or None."""
    try:
        d = datetime.date.fromisoformat((date_str or "").strip())
    except ValueError:
        return None
    mins = _time_to_minutes(time_str)
    if mins is None:
        return None
    return datetime.datetime(d.year, d.month, d.day, mins // 60, mins % 60, tzinfo=_DUBAI_TZ)


def _due_stage(hours_until: float):
    """Which reminder stage a booking that many hours away is due for now, or
    None. Past bookings and ones further out than the largest threshold wait."""
    if hours_until <= 0:
        return None
    for stage, threshold in _STAGES:
        if hours_until <= threshold:
            return stage
    return None


def compose_reminder(business: dict, booking: dict, stage: str) -> str:
    """The caller-facing reminder text. Warm, short, and actionable — names the
    business, the service, and when, then invites the two-way reply."""
    name = (booking.get("patient_name") or "there").split()[0]
    biz = business.get("name") or "your appointment"
    when = "tomorrow" if stage == "24h" else "soon"
    reason = (booking.get("reason") or "").strip()
    what = f"your {reason}" if reason else "your appointment"
    return (
        f"Hi {name}! A reminder about {what} at {biz} — {when} at "
        f"{booking.get('time')} on {booking.get('date')}. "
        "Reply CONFIRM to lock it in, or tell me if you'd like to change the time."
    )


def send_due_reminders() -> int:
    """One sweep: message every booking due for a reminder, once. Returns the
    number sent. Best-effort — a single bad booking is logged and skipped, never
    sinks the pass (the loop must outlive one bad row)."""
    now = _now()
    sent = 0
    for booking in db.future_bookings():
        try:
            if (booking.get("status") or "booked") == "cancelled":
                continue
            dt = _booking_datetime(booking.get("date"), booking.get("time"))
            if dt is None:
                continue
            stage = _due_stage((dt - now).total_seconds() / 3600)
            if stage is None:
                continue
            # Claim BEFORE sending: the UNIQUE row is what guarantees once-only.
            if not db.claim_reminder(booking["business_id"], booking["id"], stage):
                continue
            business = db.get_business(booking["business_id"])
            if business is None:
                continue
            if _deliver(business, booking, stage):
                sent += 1
        except Exception:  # noqa: BLE001 — one bad booking must not stop the sweep
            logger.exception("reminder failed for booking=%s", booking.get("id"))
    if sent:
        logger.info("[reminders] sent %d reminder(s)", sent)
    return sent


def _deliver(business: dict, booking: dict, stage: str) -> bool:
    """Send one reminder. WhatsApp when the business has it connected and the
    caller left a mobile; otherwise log it (still counts as handled so we don't
    retry forever). Returns True if a real message went out."""
    text = compose_reminder(business, booking, stage)
    phone_id = (business.get("whatsapp_phone_id") or "").strip()
    to = _to_wa_number(booking.get("phone") or "")
    if phone_id and to and get_settings().whatsapp_access_token:
        # Imported lazily so this module has no hard dependency on the channel.
        from app import whatsapp
        import asyncio

        try:
            asyncio.run(whatsapp._send_text(phone_id, to, text))
            logger.info("[reminders] whatsapp %s reminder -> booking %s", stage, booking["id"])
            return True
        except Exception:  # noqa: BLE001 — fall through to the logged path
            logger.exception("[reminders] whatsapp send failed for booking %s", booking["id"])
    logger.info("[reminders] (not delivered — no channel) %s: %s", stage, text)
    return False
