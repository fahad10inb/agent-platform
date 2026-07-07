"""
Human handoff — the escape hatch every real receptionist has. An AI that traps
a frustrated caller in a bot loop loses the customer AND the owner's trust;
this tool always gives the model a graceful exit.

Same closure-factory pattern as the other tools: bound to one business, so the
transfer number and the owner alert can never cross tenants.
"""

from app import notify_service


def make_handoff_tools(business: dict) -> list:
    """Return [request_human] bound to this business."""
    business_id = business["id"]
    transfer_number = (business.get("transfer_number") or "").strip()

    def request_human(reason: str) -> dict:
        """Hand the caller to a real person when you can't (or shouldn't) help.

        Use this when the caller is frustrated, explicitly asks for a human, or
        needs something beyond your tools. It tells you what to offer next and
        alerts the team either way.

        Args:
            reason: One short line on why the caller needs a human.

        Returns:
            The phone number to share with the caller — or, if no transfer
            number is configured, instructions to take a message instead.
        """
        # The owner hears about EVERY escalation, transfer number or not — a
        # frustrated caller is exactly who they want to ring back first. The
        # reason is model-written (no caller PII by instruction), so it may go
        # in the subject; capped so a rambling reason can't bloat it.
        notify_service.notify_owner(
            business_id,
            f"Caller asked for a human: {(reason or '').strip()[:120]}",
            f"A caller asked to speak to a real person.\nReason: {reason}\n\n"
            "Flagged automatically by your AI receptionist — a quick callback "
            "usually saves these.",
        )
        # No caller PII in server logs — Render keeps them.
        print(f"  TOOL -> request_human [biz={business_id}] transfer={'yes' if transfer_number else 'no'}")
        if transfer_number:
            return {
                "status": "transfer",
                "transfer_number": transfer_number,
                "message": f"Give the caller this number so they can reach a person: {transfer_number}",
            }
        return {
            "status": "no_transfer_available",
            "message": (
                "No transfer number is set up. Take their name, mobile number and "
                "question as a message instead (save it with capture_lead) and say "
                "the team will call them back."
            ),
        }

    return [request_human]
