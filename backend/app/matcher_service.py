"""Requirement-match alerts — the "we found you something" follow-up.

When a live listing matches what a lead TOLD us they wanted (area, bedrooms,
budget, sale/rent), message that lead once about it — the proactive re-engagement
a good agent does by hand. Same zero-infra sweep pattern as reminders / nurture /
review: `_sweep_scheduler` wakes periodically, this finds new (lead, listing)
matches and sends them.

Guardrails, because a bad proactive message to a real customer is worse than none:
  • PERMIT-GATED — an unpermitted listing is never advertised (compliance).
  • CONSERVATIVE match — needs a real area match on both sides, plus matching
    bedrooms / purpose / budget when the lead specified them. No blind blasts.
  • ONCE PER PROPERTY — `db.claim_match_alert` keys on the permit number, so a
    lead hears about a given property at most once (even across re-imports).
  • THROTTLED — at most one match alert per lead per ~20h (`_MIN_HOURS`).
  • Skips leads who already booked or opted out.
Outside WhatsApp's 24h window it delivers via the approved template
(`whatsapp_template_match`); otherwise it logs, like the other sweeps.
"""

import logging
import re

from app import db
from app.config import get_settings
from app.phone import to_wa_number

logger = logging.getLogger("agent-platform")

_LEAD_WINDOW_DAYS = 60   # only re-engage reasonably recent leads
_MIN_HOURS = 20          # at most one match alert per lead per ~day


def _digits(value) -> str:
    """The first run of digits in a value ('2 beds' -> '2', 'studio' -> '')."""
    m = re.search(r"\d+", str(value or ""))
    return m.group(0) if m else ""


def _price_num(value):
    """A rough number from a messy price/budget string, or None.
    '1.5M' -> 1_500_000, '95k/yr' -> 95_000, '1,200,000' -> 1_200_000."""
    text = str(value or "").lower().replace(",", "").replace(" ", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([mk])?", text)
    if not m:
        return None
    number = float(m.group(1))
    suffix = m.group(2)
    if suffix == "m":
        number *= 1_000_000
    elif suffix == "k":
        number *= 1_000
    return number


def _purpose(value) -> str:
    """Normalise a purpose to 'rent' / 'sale' / '' so a lead and a listing agree."""
    text = str(value or "").lower()
    if any(w in text for w in ("rent", "lease", "tenant")):
        return "rent"
    if any(w in text for w in ("buy", "sale", "sell", "purchase", "invest")):
        return "sale"
    return ""


def matches(fields: dict, listing: dict) -> bool:
    """Does this listing fit the lead's stated requirements? Conservative on
    purpose — a wrong proactive message costs more than a missed one."""
    if not (listing.get("permit_number") or "").strip():
        return False  # never advertise an unpermitted listing
    want_area = (fields.get("area") or "").lower().strip()
    listing_area = (listing.get("area") or "").lower().strip()
    if not want_area or not listing_area:
        return False  # need a real area on both sides — no blind matches
    if want_area not in listing_area and listing_area not in want_area:
        return False
    # bedrooms: if the lead said a number, the listing's must agree
    want_beds = _digits(fields.get("bedrooms"))
    if want_beds and _digits(listing.get("bedrooms")) != want_beds:
        return False
    # purpose: if both stated, rent vs sale must line up
    want_purpose, listing_purpose = _purpose(fields.get("purpose")), _purpose(listing.get("purpose"))
    if want_purpose and listing_purpose and want_purpose != listing_purpose:
        return False
    # budget: if both parse, the price must be within ~10% of the lead's budget
    budget, price = _price_num(fields.get("budget")), _price_num(listing.get("price"))
    if budget and price and price > budget * 1.1:
        return False
    return True


def compose_match(business: dict, name: str, listing: dict) -> str:
    """The lead-facing alert. Warm, specific, and it only ever names a permitted
    listing (so quoting the price is compliant)."""
    who = (name or "there").split()[0] if name else "there"
    biz = business.get("name") or "our team"
    title = (listing.get("title") or "a property").strip()
    area = (listing.get("area") or "").strip()
    beds = _digits(listing.get("bedrooms"))
    price = (listing.get("price") or "").strip()
    what = " ".join(x for x in [f"{beds}BR" if beds else "", f"in {area}" if area else ""] if x) or "property"
    msg = f"Hi {who}! A new {what} matching what you were after just came up at {biz} — {title}"
    if price:
        msg += f", {price}"
    return msg + ". Want me to arrange a viewing?"


def _deliver(business: dict, name: str, phone: str, listing: dict) -> None:
    text = compose_match(business, name, listing)
    bid = business["id"]
    phone_id = (business.get("whatsapp_phone_id") or "").strip()
    if phone_id and get_settings().whatsapp_access_token:
        from app import whatsapp
        import asyncio

        try:
            asyncio.run(whatsapp.send_business_message(
                phone_id, phone, kind="match", params=[text], fallback_text=text))
        except Exception:  # noqa: BLE001 — a bad send must never kill the sweep
            logger.exception("[match] whatsapp send failed for business=%s", bid)
    # Seed the alert as the model's turn so the lead's reply flows through run_turn
    # and re-qualifies normally (same pattern as reminders / nurture / outreach).
    db.save_message(bid, f"wa-{phone}", "model", text)
    logger.info("[match] alerted a lead in business=%s", bid)


def send_due_matches() -> int:
    """One sweep across every real-estate business. Returns how many were sent."""
    sent = 0
    for business in db.real_estate_businesses():
        bid = business["id"]
        listings = [row for row in db.list_listings(bid) if (row.get("permit_number") or "").strip()]
        if not listings:
            continue
        for lead in db.list_qualifications(bid, within_days=_LEAD_WINDOW_DAYS):
            phone = to_wa_number(lead.get("phone") or "")
            if not phone or db.phone_has_booking(bid, phone) or db.is_opted_out(bid, phone):
                continue
            if db.recent_match_alert(bid, phone, within_hours=_MIN_HOURS):
                continue  # already pinged this lead recently — don't pile on
            fields = lead.get("fields") or {}
            for listing in listings:
                if not matches(fields, listing):
                    continue
                key = (listing.get("permit_number") or "").strip()
                if not db.claim_match_alert(bid, phone, key):
                    continue  # already told them about this exact property
                _deliver(business, lead.get("name"), phone, listing)
                sent += 1
                break  # one best NEW match per lead per sweep — never a burst
    return sent
