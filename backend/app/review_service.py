"""
Post-visit Google review requests — the reputation flywheel.

After an appointment happens, a single warm message asks the client to leave a
Google review, carrying the business's own review deep link. More reviews is the
most VISIBLE owner ROI (it shows up on Maps), and review-request texts open at
95-98%. Timed per vertical: a salon client is asked a couple of hours later
while the blow-dry still looks great; a clinic patient the next day.

Same zero-infra pattern as reminders/nurture: an in-process periodic sweep,
idempotent via a UNIQUE(booking_id) claim, WhatsApp delivery with a graceful
log fallback. We only ask ONCE per booking, only when the business has set a
review link, and never a client who opted out (PDPL). The datetime parsing is
reused from the reminder sweep so the two agree on what "the appointment time"
means.
"""

import datetime
import logging
import zoneinfo

from app import db
from app.config import get_settings
from app.phone import to_wa_number as _to_wa_number
from app.reminder_service import _booking_datetime

logger = logging.getLogger("agent-platform.reviews")

_DUBAI_TZ = zoneinfo.ZoneInfo("Asia/Dubai")

# Hours to wait AFTER the appointment before asking, by vertical. A salon look is
# freshest within a couple of hours; a clinic visit reads better asked the next
# day (and gives an unhappy patient time to be handled off-Google first).
_SETTLE_HOURS = {"salon": 2, "clinic": 24, "real_estate": 6}
_DEFAULT_SETTLE_HOURS = 6

# Never ask for a review on a visit older than this — a stale "how was it?" is
# odd, and the scan window in recent_past_bookings matches it.
_MAX_AGE_DAYS = 14


def _now() -> datetime.datetime:
    """Dubai now — a seam the tests freeze."""
    return datetime.datetime.now(_DUBAI_TZ)


def _settle_hours(business: dict) -> float:
    """How long after the appointment to wait before asking this business's
    clients for a review — tuned by vertical, with a sensible default."""
    vertical = (business.get("vertical") or "").strip().lower()
    return _SETTLE_HOURS.get(vertical, _DEFAULT_SETTLE_HOURS)


def compose_review_request(business: dict, booking: dict, review_url: str) -> str:
    """The client-facing ask. Warm, brief, grateful — names the business and
    carries the one-tap review link. No incentive (against Google's policy)."""
    name = (booking.get("patient_name") or "there").split()[0]
    biz = business.get("name") or "us"
    return (
        f"Hi {name}! Thanks for choosing {biz} — we hope it went well. "
        "If you have a moment, we'd really appreciate a quick Google review: "
        f"{review_url} It genuinely helps others find us. Thank you!"
    )


def send_due_review_requests() -> int:
    """One sweep: ask each eligible past-visit client for a review, once. Returns
    the number sent. Best-effort — a single bad booking is logged and skipped,
    never sinks the pass."""
    now = _now()
    sent = 0
    for booking in db.recent_past_bookings(_MAX_AGE_DAYS):
        try:
            if (booking.get("status") or "booked") == "cancelled":
                continue
            dt = _booking_datetime(booking.get("date"), booking.get("time"))
            if dt is None:
                continue
            hours_since = (now - dt).total_seconds() / 3600
            if hours_since <= 0:
                continue  # the appointment hasn't happened yet
            business = db.get_business(booking["business_id"])
            if business is None:
                continue
            review_url = (business.get("google_review_url") or "").strip()
            # No link set → skip WITHOUT claiming, so the client still gets asked
            # once the owner pastes their review link later.
            if not review_url:
                continue
            if hours_since < _settle_hours(business):
                continue  # too soon after the visit — let it settle
            if hours_since > _MAX_AGE_DAYS * 24:
                continue  # too old to ask naturally
            if db.is_opted_out(booking["business_id"], booking.get("phone") or ""):
                continue  # PDPL do-not-contact — respect it
            # Claim BEFORE sending: the UNIQUE row is what guarantees once-only.
            if not db.claim_review_request(booking["business_id"], booking["id"]):
                continue
            if _deliver(business, booking, review_url):
                sent += 1
        except Exception:  # noqa: BLE001 — one bad booking must not stop the sweep
            logger.exception("review request failed for booking=%s", booking.get("id"))
    if sent:
        logger.info("[reviews] sent %d review request(s)", sent)
    return sent


def _deliver(business: dict, booking: dict, review_url: str) -> bool:
    """Send one review request. WhatsApp when the business has it connected and
    the client left a mobile; otherwise log it (still claimed, so we don't retry
    forever). Returns True if a real message went out."""
    text = compose_review_request(business, booking, review_url)
    phone_id = (business.get("whatsapp_phone_id") or "").strip()
    to = _to_wa_number(booking.get("phone") or "")
    if phone_id and to and get_settings().whatsapp_access_token:
        # Imported lazily so this module has no hard dependency on the channel.
        from app import whatsapp
        import asyncio

        try:
            asyncio.run(whatsapp._send_text(phone_id, to, text))
            # Seed it into the thread so a reply ("done!"/"how do I?") has context
            # when it flows back through run_turn — same as reminders/nurture.
            db.save_message(business["id"], f"wa-{to}", "model", text)
            logger.info("[reviews] whatsapp review request -> booking %s", booking["id"])
            return True
        except Exception:  # noqa: BLE001 — fall through to the logged path
            logger.exception("[reviews] whatsapp send failed for booking %s", booking["id"])
    logger.info("[reviews] (not delivered — no channel) booking %s: %s", booking["id"], text)
    return False
