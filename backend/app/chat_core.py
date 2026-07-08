"""
The channel-agnostic heart of a conversation turn.

/chat (the web widget) and /whatsapp/webhook both land here: load the business,
assemble persona + tools + history, ask the model, guard the reply, persist,
meter, and schedule the distiller. Anything channel-specific — rate limits,
HTTP error shapes, WhatsApp send calls — stays in the routes.
"""

import datetime
import logging
import zoneinfo
from collections.abc import Callable

from app import db, distill_service, notify_service
from app.llm_service import generate_reply
from app.prompt_service import build_system_prompt
from app.tools.calendar_tools import make_calendar_tools
from app.tools.handoff_tools import make_handoff_tools
from app.tools.leads_tools import make_lead_tools
from app.tools.memory_tools import make_memory_tools

logger = logging.getLogger("agent-platform.core")

_DUBAI_TZ = zoneinfo.ZoneInfo("Asia/Dubai")


def _quota_state(business: dict) -> tuple[bool, str]:
    """(over_quota, reason). A NULL quota means uncapped — the founding default.
    Reason is 'over' or 'approaching' (>=80%) or '' when there's headroom."""
    quota = business.get("monthly_msg_quota")
    if not quota:
        return (False, "")
    used = db.get_month_usage(business["id"])
    if used >= quota:
        return (True, "over")
    if used >= quota * 0.8:
        return (False, "approaching")
    return (False, "")


def _decline_message(business: dict) -> str:
    """What a caller hears when the business is over its monthly quota — never a
    500 or a raw error. Steers to a human where one is on file."""
    transfer = (business.get("transfer_number") or "").strip()
    if transfer:
        return (
            "Thanks for reaching out! I can't take new messages at the moment, "
            f"but you can reach the team directly on {transfer} and they'll be "
            "glad to help."
        )
    return (
        "Thanks for reaching out! I can't take new messages right now — please "
        "try again a little later, or get in touch during opening hours and the "
        "team will be glad to help."
    )


def _notify_quota(business: dict, reason: str, schedule: Callable) -> None:
    """Email the owner once per month when they hit 80% / go over — claimed
    atomically so concurrent turns can't send twice."""
    month = datetime.datetime.now(_DUBAI_TZ).strftime("%Y-%m")
    if not db.claim_quota_notice(business["id"], month):
        return
    quota = business.get("monthly_msg_quota")
    if reason == "over":
        subject = "You've reached this month's message limit"
        body = (
            f"Your AI receptionist has handled its {quota} messages for this month, "
            "so new messages are being politely paused until next month. Reply to "
            "upgrade your plan and keep it answering."
        )
    else:
        subject = "You're close to this month's message limit"
        body = (
            f"Your AI receptionist has used over 80% of its {quota} messages this "
            "month. Reply to upgrade if you'd like to avoid any pause."
        )
    schedule(notify_service.notify_owner, business["id"], subject, body)


async def run_turn(
    business_id: str, conversation_id: str, message: str, schedule: Callable
) -> str:
    """One full conversation turn; returns the reply text.

    Raises LookupError for an unknown business (each route maps that to its own
    404-shape) and lets model errors propagate — nothing is persisted on
    failure, so a failed turn can't haunt the next request (rollback by
    construction). `schedule(fn, *args)` defers background work: FastAPI's
    BackgroundTasks.add_task in the web route, an asyncio task in the webhook.
    """
    business = db.get_business(business_id)
    if business is None:
        raise LookupError(f"Unknown business_id: {business_id}")

    # Monthly quota = the founding plan's fair-use fuse and the cost cap that
    # stops one abused/viral business_id from draining the shared Gemini bill.
    # Over the cap we DECLINE gracefully (no model call, no 500) and email the
    # owner once; approaching it we just email the nudge and carry on.
    over, reason = _quota_state(business)
    if reason:
        _notify_quota(business, reason, schedule)
    if over:
        logger.info("quota reached for business=%s — declining turn", business_id)
        return _decline_message(business)

    system_prompt = build_system_prompt(business)

    # This conversation's DURABLE history (scoped by business_id — the same
    # conversation_id at two businesses can never share context), capped at 40
    # turns at read time, plus the new message in memory only.
    history = db.get_history(business_id, conversation_id, limit=40)
    history = history + [{"role": "user", "text": message}]

    # Tools are built PER TURN, each scoped to this business via its closure.
    tools = (
        make_calendar_tools(business)
        + make_memory_tools(business_id)
        + make_lead_tools(business_id)
        + make_handoff_tools(business)
    )
    reply = await generate_reply(system_prompt, history, tools=tools)

    # Last-resort guard: llm_service already retries/recovers empty and leaked
    # replies; if EVERYTHING came back blank the caller still gets words.
    if not reply.strip():
        reply = (
            "Sorry — I lost my words for a second there. Could you say that "
            "again? I'll double-check everything before confirming."
        )

    # Persist BOTH turns only now that the reply succeeded, and meter the turn
    # against the business's daily usage (the future billing/quota data).
    db.save_message(business_id, conversation_id, "user", message)
    db.save_message(business_id, conversation_id, "model", reply)
    db.bump_usage(business_id)

    # Every 6th caller message, distill the conversation into durable caller
    # memory — deferred so the caller never waits on it. `history` already
    # includes this turn's message, so counting it counts the conversation as
    # it now stands. Flag-gated (DISTILL_ENABLED) and swallows its own errors.
    every_n = distill_service.DISTILL_EVERY_N_USER_MESSAGES
    user_turns = sum(1 for t in history if t["role"] == "user")
    if user_turns >= every_n and user_turns % every_n == 0:
        schedule(distill_service.distill_conversation, business_id, conversation_id)
    return reply
