"""
Portal lead-intake — the speed-to-lead pipe.

A Bayut / Property Finder / Dubizzle lead lands in the agency's inbox as an
email. The agency forwards those emails to a per-business ingest address; the
email provider POSTs the parsed message to /leads/ingest; this module turns it
into a captured lead AND fires the instant first response — an outreach to the
lead within seconds, which is the single highest-ROI act in the funnel (portals
deliver, humans answer ~42h later, ~23% never).

Parsing is deliberately forgiving: portal templates change, so we detect the
source, pull the labelled fields when present, and fall back to regex for the
phone/email/name. Reaching the lead reuses the WhatsApp channel with the same
graceful log fallback as reminders (real business-initiated delivery needs an
approved template — see whatsapp.py).
"""

import logging
import re

from app import db, notify_service
from app.config import get_settings
from app.phone import to_wa_number

logger = logging.getLogger("agent-platform.leadintake")

_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Labelled fields portals commonly use ("Name: ...", "Mobile: ...").
_LABELS = {
    "name": ("name", "client name", "customer name", "lead name", "full name"),
    "phone": ("phone", "mobile", "mobile number", "contact number", "tel", "telephone"),
    "email": ("email", "e-mail", "email address"),
    "property_ref": ("reference", "ref", "ref no", "property reference", "listing",
                     "listing reference", "permit", "permit number"),
    "message": ("message", "comment", "comments", "enquiry", "inquiry", "note"),
}


def detect_source(text: str) -> str:
    """Which portal an email came from, from its content. 'unknown' otherwise."""
    low = (text or "").lower()
    if "propertyfinder" in low or "property finder" in low:
        return "Property Finder"
    if "bayut" in low:
        return "Bayut"
    if "dubizzle" in low:
        return "Dubizzle"
    return "unknown"


def _labelled(body: str) -> dict:
    """Pull 'Label: value' lines (portal emails are mostly these)."""
    found: dict[str, str] = {}
    for raw in (body or "").splitlines():
        if ":" not in raw:
            continue
        label, _, value = raw.partition(":")
        key = label.strip().lower()
        value = value.strip()
        if not value:
            continue
        for field, aliases in _LABELS.items():
            if key in aliases and field not in found:
                found[field] = value
    return found


def parse_portal_lead(subject: str, body: str, from_hint: str = "") -> dict | None:
    """Portal email → {source, name, phone, email, property_ref, message}, or
    None when there's no usable contact at all (not a lead)."""
    blob = "\n".join(x for x in (subject, from_hint, body) if x)
    fields = _labelled(body)

    phone = fields.get("phone") or ""
    if not phone:
        m = _PHONE_RE.search(body or "")
        phone = m.group(1).strip() if m else ""
    email = fields.get("email") or ""
    if not email:
        # Skip a portal's own no-reply sender; take the first human-looking one.
        for cand in _EMAIL_RE.findall(body or ""):
            if "noreply" not in cand.lower() and "no-reply" not in cand.lower():
                email = cand
                break
    if not phone and not email:
        return None

    name = fields.get("name") or ""
    if not name:
        m = re.search(r"(?:from|lead from|enquiry from)\s+([A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+)?)",
                      subject or "", re.IGNORECASE)
        name = m.group(1).strip() if m else ""

    return {
        "source": detect_source(blob),
        "name": name,
        "phone": phone,
        "email": email,
        "property_ref": fields.get("property_ref", ""),
        "message": fields.get("message", ""),
    }


def _compose_outreach(business: dict, lead: dict) -> str:
    """The instant first message to a portal lead — warm, fast, and already
    asking the first qualifying question so momentum starts immediately."""
    first = (lead.get("name") or "there").split()[0] if lead.get("name") else "there"
    biz = business.get("name") or "our team"
    ref = (lead.get("property_ref") or "").strip()
    about = f" about {ref}" if ref else ""
    src = lead.get("source")
    via = f" through {src}" if src and src != "unknown" else ""
    return (
        f"Hi {first}! Thanks for your enquiry{about}{via} — this is the assistant "
        f"at {biz}. I can get you details and set up a viewing fast. To point you "
        "to the right options, what's your budget range and which area are you "
        "focused on?"
    )


def ingest_lead(business: dict, parsed: dict) -> dict:
    """Turn a parsed portal lead into a captured lead + instant owner alert +
    instant outreach to the lead. Dedupes on the phone (a portal re-notifying
    the same enquiry must not make two leads or two owner emails)."""
    business_id = business["id"]
    interest_bits = [x for x in (parsed.get("property_ref"), parsed.get("message")) if x]
    interest = " — ".join(interest_bits) or "Property enquiry"
    src = parsed.get("source") or "unknown"
    notes = f"via {src}" + (f"; email {parsed['email']}" if parsed.get("email") else "")
    phone = parsed.get("phone") or ""

    existing = db.find_recent_lead(business_id, phone) if phone else None
    if existing:
        merged = "; ".join(x for x in (existing.get("notes"), notes) if x)
        db.update_lead(existing["id"], interest, merged)
        outcome = "updated"
        lead_id = existing["id"]
    else:
        lead_id = db.save_lead(business_id, parsed.get("name") or "Portal lead", phone, interest, notes)
        # A portal lead is money on the clock — tell the owner instantly.
        notify_service.notify_owner(
            business_id,
            f"New {src} lead: {parsed.get('name') or 'enquiry'}",
            f"{parsed.get('name') or 'A lead'} ({phone or parsed.get('email') or '—'}) enquired: "
            f"{interest}\n\nThe assistant is reaching out to them now.",
        )
        outcome = "captured"

    reached = _reach_out(business, parsed) if phone else False
    logger.info("[leadintake] %s %s lead for business=%s (reached=%s)", outcome, src, business_id, reached)
    return {"status": outcome, "lead_id": lead_id, "reached_out": reached}


def _reach_out(business: dict, parsed: dict) -> bool:
    """Send the instant first message to the lead and seed the conversation so
    their reply flows through the normal WhatsApp → run_turn qualification. Real
    business-initiated delivery needs an approved template (see whatsapp.py);
    without a live channel it's logged, and the seeded opener still lets the
    thread continue when they message in."""
    to = to_wa_number(parsed.get("phone") or "")
    if not to:
        return False
    text = _compose_outreach(business, parsed)
    conversation_id = f"wa-{to}"
    phone_id = (business.get("whatsapp_phone_id") or "").strip()
    delivered = False
    if phone_id and get_settings().whatsapp_access_token:
        from app import whatsapp
        import asyncio

        try:
            asyncio.run(whatsapp.send_business_message(
                phone_id, to, kind="outreach", params=[text], fallback_text=text))
            delivered = True
        except Exception:  # noqa: BLE001 — fall through to the seeded/logged path
            logger.exception("[leadintake] whatsapp outreach failed for business=%s", business["id"])
    # Record the opener as the model's turn so the lead's reply has context and
    # is scored/qualified normally by run_turn.
    db.save_message(business["id"], conversation_id, "model", text)
    if not delivered:
        logger.info("[leadintake] (not delivered — no live channel) outreach: %s", text)
    return delivered
