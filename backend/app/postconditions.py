"""
postconditions.py — the domain post-condition ledger.

For each action the AI can CLAIM in a reply, this declares the effect that MUST
exist in the datastore, how to VERIFY it, and how to either REPAIR it (re-perform
it deterministically) or ESCALATE it (alert a human) when it isn't there.

This is the piece a horizontal agent framework structurally can't ship: it encodes
*this business's required effects per intent* — not merely "a tool was called". It
generalizes the lead-capture net from ONE action to every action the agent claims.

Design rule — auto-REPAIR only what is safe to re-perform deterministically;
ESCALATE anything ambiguous rather than guess:

  - lead / follow-up  -> REPAIR   : the caller's number is in the chat; saving the
                                    lead ourselves is safe and idempotent.
  - human handoff     -> REPAIR   : alerting the owner *is* the handoff — safe to do.
  - booking / reschedule / cancel -> ESCALATE : we must NOT auto-book or auto-cancel
                                    — we can't know which slot the caller agreed to,
                                    and acting on the wrong one is worse than a
                                    prompt to a human. So we alert the owner to
                                    confirm, fast.

Runs in the background (deferred by chat_core) and is best-effort throughout — a
reconciliation failure must never surface to the caller.
"""

import logging

from app import db, lead_safety, notify_service

logger = logging.getLogger("agent-platform")


def _phone_in(business: dict, conversation_id: str) -> str:
    """The caller's phone from the conversation, via the lead net's extractor."""
    try:
        history = db.get_history(business["id"], conversation_id, limit=40)
        text = " ".join(m.get("text", "") for m in history if m.get("role") == "user")
        return lead_safety._find_phone(text)
    except Exception:  # noqa: BLE001 — verification must never raise
        return ""


def _has_lead(business: dict, conversation_id: str) -> bool:
    phone = _phone_in(business, conversation_id)
    return bool(phone and db.find_recent_lead(business["id"], phone))


def _has_booking(business: dict, conversation_id: str) -> bool:
    phone = _phone_in(business, conversation_id)
    return bool(phone and db.phone_has_booking(business["id"], phone))


def _repair_lead(business: dict, conversation_id: str) -> None:
    lead_safety.ensure_lead_captured(business, conversation_id)


def _repair_handoff(business: dict, conversation_id: str) -> None:
    notify_service.notify_owner(
        business["id"],
        "A caller asked for a human (auto-flagged)",
        "Your AI told a caller it would connect them to a real person, but the "
        "handoff wasn't logged. A quick callback usually saves these.",
    )


class _Post:
    """One ledger entry: how to check the effect, and how to make it right."""

    __slots__ = ("verify", "repair", "escalate")

    def __init__(self, verify, repair=None, escalate=None):
        self.verify = verify  # (business, conversation_id) -> bool
        self.repair = repair  # (business, conversation_id) -> None  | None
        self.escalate = escalate  # (subject, body) to alert the owner | None


# The ledger. `verify` returns True when the required effect already exists (so we
# never raise a false alarm); otherwise we `repair` it or `escalate` to a human.
_LEDGER: dict[str, _Post] = {
    "lead / follow-up": _Post(verify=_has_lead, repair=_repair_lead),
    "human handoff": _Post(verify=lambda b, c: False, repair=_repair_handoff),
    "appointment booked": _Post(
        verify=_has_booking,
        escalate=(
            "Please confirm a viewing your AI said was booked",
            "Your AI told a caller their viewing was booked, but no booking is on "
            "record. Please check the conversation and confirm with them.",
        ),
    ),
    "appointment rescheduled": _Post(
        verify=_has_booking,
        escalate=(
            "Please confirm a reschedule your AI mentioned",
            "Your AI told a caller their viewing was moved, but the change isn't on "
            "record. Please check and confirm.",
        ),
    ),
    "appointment cancelled": _Post(
        verify=lambda b, c: False,
        escalate=(
            "Please confirm a cancellation your AI mentioned",
            "Your AI told a caller their viewing was cancelled, but the change isn't "
            "on record — the slot may still be held. Please check.",
        ),
    ),
}


def reconcile_claims(
    business: dict, conversation_id: str, claimed_actions: list[str]
) -> None:
    """Enforce the post-condition of every action the reply CLAIMED: verify the
    effect exists; else repair it, or escalate to a human when it can't be
    re-performed safely. Best-effort — one action's failure never stops the rest,
    and nothing here can reach the caller."""
    bid = business.get("id")
    for action in claimed_actions:
        spec = _LEDGER.get(action)
        if spec is None:
            continue
        try:
            if spec.verify(business, conversation_id):
                continue  # the effect actually exists — no gap to close
            if spec.repair is not None:
                spec.repair(business, conversation_id)
                logger.info("[postcond] repaired %r for %s", action, bid)
            elif spec.escalate is not None:
                subject, body = spec.escalate
                notify_service.notify_owner(bid, subject, body)
                logger.info("[postcond] escalated %r for %s", action, bid)
        except Exception:  # noqa: BLE001 — one action's failure must not stop the rest
            logger.exception("[postcond] %r reconciliation failed for %s", action, bid)
