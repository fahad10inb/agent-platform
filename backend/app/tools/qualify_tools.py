"""
Lead qualification tool (real estate) — turns the chat into a structured, scored,
logged, CRM-written lead. The AI calls qualify_lead once it has gathered the
BANT/CHAMP fields; a deterministic score (A/B/C) decides priority, the record is
stored, the owner's Leads tab is enriched so they see it, and it's pushed to the
agency's CRM.
"""

from app import crm_service, db

# What "urgent" and "ready to pay" look like in a caller's own words.
_URGENT = ("asap", "urgent", "immediately", "this week", "this month", "ready to",
           "right away", "soon", "now", "next week", "moving")
_PAY_READY = ("cash", "pre-approved", "preapproved", "pre approved", "approved",
              "prequalified", "pre-qualified", "secured", "mortgage approved")


def score_lead(fields: dict) -> tuple[str, str]:
    """Deterministic A/B/C priority from the qualification fields (Bayut's own
    benchmark: A hot ~5% conv, B early ~2% but the volume, C nurture). Points:
    budget +1, area +1, an urgent timeline +2, a ready payment method +2 —
    A at 4+, B at 2-3, C below. Returns (score, one-line reason)."""
    budget = bool((fields.get("budget") or "").strip())
    area = bool((fields.get("area") or "").strip())
    timeline = (fields.get("timeline") or "").lower()
    pay = (str(fields.get("pay_method") or "") + " " + str(fields.get("pre_approval") or "")).lower()
    urgent = any(k in timeline for k in _URGENT)
    pay_ready = any(k in pay for k in _PAY_READY)

    points = (1 if budget else 0) + (1 if area else 0) + (2 if urgent else 0) + (2 if pay_ready else 0)
    if points >= 4:
        return "A", "clear budget/area with urgency or ready financing"
    if points >= 2:
        return "B", "real interest, but early on timeline or financing"
    return "C", "early browser — nurture until budget/intent firms up"


def summarize(fields: dict, score: str) -> str:
    """A compact one-line summary for the owner's Leads tab, e.g.
    '[A] AED 1.5-2M · Dubai Marina · 2BR · buy · cash · this month'."""
    order = ["budget", "area", "bedrooms", "purpose", "property_type", "pay_method",
             "pre_approval", "timeline"]
    bits = [str(fields[k]).strip() for k in order if (fields.get(k) or "").strip()]
    return f"[{score}] " + " · ".join(bits) if bits else f"[{score}] enquiry"


def make_qualify_tools(business: dict) -> list:
    """Return [qualify_lead] bound to this business (real-estate vertical)."""
    business_id = business["id"]

    def qualify_lead(
        name: str,
        phone: str,
        budget: str = "",
        area: str = "",
        bedrooms: str = "",
        purpose: str = "",
        timeline: str = "",
        pay_method: str = "",
        pre_approval: str = "",
        property_type: str = "",
    ) -> dict:
        """Record a real-estate lead's qualification and priority. Call this once
        you've learned enough from the caller — you don't need every field, save
        what you have and update it later as you learn more (calling again with
        the same phone updates the same record, never duplicates).

        Args:
            name: The caller's name.
            phone: The caller's mobile number (the record key).
            budget: Their budget or range, in their words (e.g. "1.5-2M", "up to 90k/yr").
            area: Target area(s) (e.g. "Dubai Marina, JVC").
            bedrooms: Bedrooms wanted (e.g. "2", "studio").
            purpose: end-use / investment / holiday home, if said.
            timeline: How soon they want to act (e.g. "this month", "just browsing").
            pay_method: cash or mortgage, if known.
            pre_approval: mortgage pre-approval status (none / prequalified / secured).
            property_type: apartment / villa / townhouse, ready or off-plan, if said.

        Returns:
            A dict with the assigned priority score (A/B/C).
        """
        fields = {
            "budget": budget, "area": area, "bedrooms": bedrooms, "purpose": purpose,
            "timeline": timeline, "pay_method": pay_method, "pre_approval": pre_approval,
            "property_type": property_type,
        }
        score, reason = score_lead(fields)
        summary = summarize(fields, score)
        print(f"  TOOL -> qualify_lead score={score} [biz={business_id}]")
        db.upsert_qualification(business_id, phone, name, fields, score)

        # Enrich the owner's Leads tab: update the caller's lead (or create one)
        # so the scored summary shows up where they already look. Dedup-safe.
        existing = db.find_recent_lead(business_id, phone) if phone else None
        if existing:
            db.update_lead(existing["id"], summary, existing.get("notes") or "")
        else:
            db.save_lead(business_id, name or "Lead", phone, summary, "")

        # Push to the agency's CRM (best-effort; no-op if they haven't set one).
        crm_service.push_lead(business, {
            "name": name, "phone": phone, "score": score, "summary": summary, "source": "AI qualified",
            **fields,
        })
        return {"status": "qualified", "score": score, "reason": reason}

    def stop_contact(phone: str) -> dict:
        """Record a caller's request to stop being contacted (PDPL do-not-contact).
        Call this whenever a caller asks to stop messages, unsubscribe, opt out,
        or be removed — after this, no reminders or follow-ups go to that number.

        Args:
            phone: The caller's mobile number.

        Returns:
            A confirmation dict.
        """
        print(f"  TOOL -> stop_contact [biz={business_id}]")
        db.set_opt_out(business_id, phone)
        return {"status": "opted_out"}

    return [qualify_lead, stop_contact]
