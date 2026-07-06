"""
Memory tools — built per request, BOUND to one business (same closure trick as
the calendar tools). This is what keeps caller memory isolated: "Sarah Lee" at
the dental clinic and "Sarah Lee" at the salon are completely separate people,
because every lookup/save is scoped to the business_id baked into the tool.
"""

from app import db


def make_memory_tools(business_id: str) -> list:
    """Return [recall_caller, remember_about_caller] bound to this business."""

    def recall_caller(name: str, phone_last4: str = "") -> dict:
        """Look up a caller's full profile: what we remember about them AND their
        appointments (past + upcoming).

        Call this as soon as you learn who you're speaking with, so you can greet
        a returning caller warmly and personally — referencing a past concern or
        an upcoming appointment — instead of treating them as new.

        Args:
            name: The caller's name.

        Returns:
            A dict with the name, remembered notes, and their appointments
            (both empty if they're new).
        """
        notes = db.get_caller_memory(business_id, name)
        appts = db.find_bookings(business_id, name)
        # Identity gate (anti-IDOR): anyone can TYPE a name into the public
        # widget, so appointment dates/times are only revealed after the caller
        # proves the mobile number on file (last 4 digits, matched HERE — the
        # model never sees the stored number). Warm recognition (notes, visit
        # count) stays available so a regular still feels remembered.
        on_file = [(r.get("phone") or "") for r in appts if r.get("phone")]
        verified = bool(phone_last4) and any(p.endswith(phone_last4[-4:]) for p in on_file)
        shown = [
            {"date": r["date"], "time": r["time"]} for r in appts
        ] if (verified or not on_file) else "hidden — verify with phone_last4 first"
        print(f"  TOOL -> recall_caller [biz={business_id}] notes={len(notes)} appts={len(appts)} verified={verified}")
        return {
            "name": name,
            "known_notes": notes,
            "appointments": shown,
            "identity_verified": verified or not on_file,
            # A tiny profile so you can greet like a human who remembers them:
            # "welcome back!" beats "how can I help you today?" every time.
            "returning_caller": bool(notes or appts),
            "visit_count": len(appts),
        }

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
        # Skip exact repeats — an append-only log of "prefers Rana" x5 reads as
        # junk when recalled. (Same lesson as the companion's memory dedup.)
        existing = {n.strip().lower() for n in db.get_caller_memory(business_id, name)}
        if (note or "").strip().lower() in existing:
            print(f"  TOOL -> remember_about_caller SKIPPED (duplicate) [biz={business_id}]")
            return {"status": "already_known", "name": name}
        print(f"  TOOL -> remember_about_caller [biz={business_id}]")
        db.save_caller_memory(business_id, name, note)
        return {"status": "saved", "name": name, "note": note}

    return [recall_caller, remember_about_caller]
