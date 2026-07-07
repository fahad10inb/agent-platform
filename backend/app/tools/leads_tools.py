"""
Lead-capture tool — for verticals that sell rather than (only) schedule, like
real estate and general small businesses. Same closure pattern as the others:
bound to one business so a captured lead lands in the right tenant.
"""

from app import db, notify_service


def make_lead_tools(business_id: str) -> list:
    """Return [capture_lead] bound to this business."""

    def capture_lead(name: str, phone: str, interest: str, notes: str = "") -> dict:
        """Save an enquiry/lead so the team can follow up.

        Use this when a caller is interested but isn't booking a fixed slot — e.g.
        a property enquiry. Save AS SOON AS you have their name, mobile number and
        a rough idea of what they want — a partial lead saved beats a perfect one
        lost. Do NOT keep asking qualifying questions before saving; capture first,
        keep chatting after. If more detail emerges later (buy vs rent, bedrooms,
        timeline), add it with remember_about_caller — do not call this again, it
        would duplicate the lead.

        Args:
            name: The caller's name.
            phone: The caller's mobile number.
            interest: What they're looking for, in their words.
            notes: Any extra useful detail.

        Returns:
            A confirmation dict.
        """
        # No PII (name/phone) in server logs — Render retains them.
        print(f"  TOOL -> capture_lead [biz={business_id}]")
        lead_id = db.save_lead(business_id, name, phone, interest, notes)
        # A lead is money waiting for a call back — tell the owner NOW.
        notify_service.notify_owner(
            business_id,
            f"New lead: {name}",
            f"{name} ({phone}) is interested in: {interest}\n{notes}\n\n"
            "Captured automatically by your AI receptionist — a quick callback wins these.",
        )
        return {"status": "captured", "lead_id": lead_id, "name": name}

    return [capture_lead]
