"""
Memory tools — built per request, BOUND to one business (same closure trick as
the calendar tools). This is what keeps caller memory isolated: "Sarah Lee" at
the dental clinic and "Sarah Lee" at the salon are completely separate people,
because every lookup/save is scoped to the business_id baked into the tool.
"""

from app import db


def make_memory_tools(business_id: str) -> list:
    """Return [recall_caller, remember_about_caller] bound to this business."""

    def recall_caller(name: str) -> dict:
        """Look up what we already know about a caller (past visits, preferences, worries).

        Call this as soon as you learn who you're speaking with, so you can greet
        a returning caller warmly instead of treating them as new.

        Args:
            name: The caller's name.

        Returns:
            A dict with the name and a list of remembered notes (empty if new).
        """
        print(f"  TOOL -> recall_caller({name!r}) [biz={business_id}]")
        return {"name": name, "known_notes": db.get_caller_memory(business_id, name)}

    def remember_about_caller(name: str, note: str) -> dict:
        """Save a useful fact about a caller so you remember it on their next call.

        Use this for a preference, a concern, what they came in for — anything
        that makes the next call feel personal. Keep each note short and factual.

        Args:
            name: The caller's name.
            note: The single fact to remember.

        Returns:
            A confirmation dict.
        """
        print(f"  TOOL -> remember_about_caller({name!r}, {note!r}) [biz={business_id}]")
        db.save_caller_memory(business_id, name, note)
        return {"status": "saved", "name": name, "note": note}

    return [recall_caller, remember_about_caller]
