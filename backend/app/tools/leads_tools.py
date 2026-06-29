"""
Lead-capture tool — for verticals that sell rather than (only) schedule, like
real estate and general small businesses. Same closure pattern as the others:
bound to one business so a captured lead lands in the right tenant.
"""

from app import db


def make_lead_tools(business_id: str) -> list:
    """Return [capture_lead] bound to this business."""

    def capture_lead(name: str, phone: str, interest: str, notes: str = "") -> dict:
        """Save an enquiry/lead so the team can follow up.

        Use this when a caller is interested but isn't booking a fixed slot — e.g.
        a property enquiry. Collect their name, mobile number, and what they're
        after (for real estate: buy or rent, area, budget, bedrooms; for general
        businesses: what they need). Ask for whatever's missing before saving.

        Args:
            name: The caller's name.
            phone: The caller's mobile number.
            interest: What they're looking for, in their words.
            notes: Any extra useful detail.

        Returns:
            A confirmation dict.
        """
        print(f"  TOOL -> capture_lead(name={name!r}, phone={phone!r}, interest={interest!r}) [biz={business_id}]")
        lead_id = db.save_lead(business_id, name, phone, interest, notes)
        return {"status": "captured", "lead_id": lead_id, "name": name}

    return [capture_lead]
