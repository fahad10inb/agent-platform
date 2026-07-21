"""
Lead nurture cadence — the B-lead volume converter.

Most enquiries don't book on day one; the deals hide in relentless, gentle
follow-up (Bayut: B-leads ~2% each but they out-produce A-leads by sheer
volume). This sweep re-engages a lead that captured but went quiet, at a few
cadence steps, once each — and STOPS the moment they book (a converted lead
must never get a 'still looking?' nudge).

Same zero-infra pattern as reminders: an in-process periodic sweep, idempotent
via a UNIQUE (business, phone, stage) claim, WhatsApp delivery with a graceful
log fallback. Marketing-style outbound is TDRA/PDPL-sensitive — these are
service follow-ups to a lead who contacted the business first, kept light, and
the whole cadence is one flag away from off.
"""

import datetime
import logging
import zoneinfo

from app import db
from app.config import get_settings
from app.phone import to_wa_number

logger = logging.getLogger("agent-platform.nurture")

_DUBAI_TZ = zoneinfo.ZoneInfo("Asia/Dubai")

# (stage, age-in-days at/after which it's due). We send the LATEST stage a lead
# has aged past that hasn't been sent — so a lead touched at day 2, 7 and 30 as
# it naturally ages, and a lead already older than 30 gets only the last touch,
# never a burst. After the final stage the cadence is done (bounded).
_STAGES = (("day2", 2), ("day7", 7), ("day30", 30))


def _now() -> datetime.datetime:
    return datetime.datetime.now(_DUBAI_TZ)


def _age_days(created_at) -> float | None:
    """Whole+fractional days since a lead was captured, or None if unknown."""
    if not isinstance(created_at, datetime.datetime):
        return None
    now = _now()
    created = created_at if created_at.tzinfo else created_at.replace(tzinfo=datetime.timezone.utc)
    return (now - created).total_seconds() / 86400


def _due_stage(age_days: float):
    """The most advanced cadence stage this lead has aged past, or None."""
    due = None
    for stage, threshold in _STAGES:
        if age_days >= threshold:
            due = stage
    return due


def compose_nurture(business: dict, lead: dict, stage: str) -> str:
    """The follow-up text for a stage. Warm, no pressure, no discount-baiting
    (that trains people to wait) — just a helpful reopening of the conversation."""
    first = (lead.get("name") or "there").split()[0] if lead.get("name") else "there"
    biz = business.get("name") or "our team"
    if stage == "day2":
        return (f"Hi {first}, it's {biz} — just following up on your enquiry. "
                "Still looking? I can line up a couple of options or a viewing whenever suits you.")
    if stage == "day7":
        return (f"Hi {first}, checking in from {biz}. If you're still in the market, "
                "tell me your budget and area and I'll send you what fits — no rush.")
    return (f"Hi {first}, {biz} here with a quick market check-in. New options come up "
            "often — happy to share a fresh shortlist whenever you'd like one.")


def send_due_nurtures() -> int:
    """One sweep: send each silent lead its due nurture touch, once. Skips leads
    that already booked. Best-effort — one bad lead never sinks the pass."""
    sent = 0
    for lead in db.leads_for_nurture():
        try:
            age = _age_days(lead.get("created_at"))
            if age is None:
                continue
            stage = _due_stage(age)
            if stage is None:
                continue
            business_id, phone = lead["business_id"], lead.get("phone") or ""
            if not phone or db.phone_has_booking(business_id, phone):
                continue  # converted (or unreachable) — don't nurture
            if db.is_opted_out(business_id, phone):
                continue  # PDPL do-not-contact — respect it
            if not db.claim_nurture(business_id, phone, stage):
                continue
            business = db.get_business(business_id)
            if business is None:
                continue
            if _deliver(business, lead, stage):
                sent += 1
        except Exception:  # noqa: BLE001 — one bad lead must not stop the sweep
            logger.exception("nurture failed for lead phone-hash=%s", hash(lead.get("phone")))
    if sent:
        logger.info("[nurture] sent %d nurture touch(es)", sent)
    return sent


def _deliver(business: dict, lead: dict, stage: str) -> bool:
    """Send one nurture touch. WhatsApp when connected + the caller left a
    mobile; otherwise logged (still claimed, so we don't retry forever)."""
    text = compose_nurture(business, lead, stage)
    phone_id = (business.get("whatsapp_phone_id") or "").strip()
    to = to_wa_number(lead.get("phone") or "")
    conversation_id = f"wa-{to}" if to else ""
    if phone_id and to and get_settings().whatsapp_access_token:
        from app import whatsapp
        import asyncio

        try:
            asyncio.run(whatsapp.send_business_message(
                phone_id, to, kind="nurture", params=[text], fallback_text=text))
            if conversation_id:
                db.save_message(business["id"], conversation_id, "model", text)
            logger.info("[nurture] whatsapp %s -> business=%s", stage, business["id"])
            return True
        except Exception:  # noqa: BLE001 — fall through to the logged path
            logger.exception("[nurture] whatsapp send failed for business=%s", business["id"])
    logger.info("[nurture] (not delivered — no channel) %s: %s", stage, text)
    return False
