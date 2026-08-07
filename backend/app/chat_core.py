"""
The channel-agnostic heart of a conversation turn.

/chat (the web widget) and /whatsapp/webhook both land here: load the business,
assemble persona + tools + history, ask the model, guard the reply, persist,
meter, and schedule the distiller. Anything channel-specific — rate limits,
HTTP error shapes, WhatsApp send calls — stays in the routes.
"""

import asyncio
import datetime
import inspect
import logging
import re
import zoneinfo
from collections.abc import Callable
from functools import lru_cache

from app import (
    db,
    distill_service,
    lead_safety,
    notify_service,
    postconditions,
    say_do_verifier,
)
from app.llm_service import generate_reply
from app.prompt_service import build_system_prompt
from app.tools.calendar_tools import make_calendar_tools
from app.tools.handoff_tools import make_handoff_tools
from app.tools.leads_tools import make_lead_tools
from app.tools.memory_tools import make_memory_tools

logger = logging.getLogger("agent-platform.core")

_DUBAI_TZ = zoneinfo.ZoneInfo("Asia/Dubai")


@lru_cache(maxsize=8)
def _accepts_activity_sink(fn: Callable) -> bool:
    """Does this generate_reply implementation take the activity_sink kwarg? The
    real one does; a plain 3-arg test double doesn't. Feature-detected (rather than
    always-passing it) so those doubles keep working untouched — see test_demo's
    'normal chat route is untouched by the activity sink'. Cached; the binding
    rarely changes."""
    try:
        return "activity_sink" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


# One lock per (business, conversation) so rapid-fire messages in the SAME thread
# run one-at-a-time — without it, message B reads history before A has saved, so
# B's model never sees A, both run tools (both may book the same caller), and the
# saved turns interleave. Different conversations never contend (different keys),
# so throughput is unaffected. Single instance only; created lazily in the loop.
_conv_locks: dict[tuple[str, str], "asyncio.Lock"] = {}


def _conversation_lock(business_id: str, conversation_id: str) -> "asyncio.Lock":
    key = (business_id, conversation_id)
    lock = _conv_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _conv_locks[key] = lock
    return lock


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


# The model mirrors the caller's language on its own; these DETERMINISTIC lines
# (quota decline, empty-reply catch) can't ask the model to translate, so we keep
# an Arabic copy and pick it when the caller is writing Arabic. Any Arabic letter
# in their message is enough of a signal.
_ARABIC_RE = re.compile(r"[؀-ۿ]")

_EMPTY_REPLY_EN = (
    "Sorry — I lost my words for a second there. Could you say that again? "
    "I'll double-check everything before confirming."
)
_EMPTY_REPLY_AR = (
    "المعذرة، ضاعت مني الكلمات للحظة. ممكن تعيد كلامك؟ سأتأكد من كل التفاصيل "
    "قبل التأكيد."
)


def _is_arabic(text: str) -> bool:
    """Is the caller writing in Arabic? A cheap script check that keeps our
    hardcoded fallback lines in their language."""
    return bool(_ARABIC_RE.search(text or ""))


def _decline_message(business: dict, message: str = "") -> str:
    """What a caller hears when the business is over its monthly quota — never a
    500 or a raw error. Steers to a human where one is on file, and answers in the
    caller's language."""
    transfer = (business.get("transfer_number") or "").strip()
    if _is_arabic(message):
        if transfer:
            return (
                "شكراً لتواصلك معنا! لا أستطيع استقبال رسائل جديدة حالياً، لكن "
                f"يمكنك التواصل مع الفريق مباشرة على {transfer} وسيسعدهم مساعدتك."
            )
        return (
            "شكراً لتواصلك معنا! لا أستطيع استقبال رسائل جديدة حالياً — يرجى "
            "المحاولة بعد قليل، أو التواصل خلال ساعات العمل وسيسعد الفريق بمساعدتك."
        )
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
    business_id: str,
    conversation_id: str,
    message: str,
    schedule: Callable,
    activity: list | None = None,
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

    # Human takeover: if an owner has taken this conversation over from the
    # inbox, the AI stays silent — we still SAVE the caller's message so the
    # human sees it, but generate no reply. The empty return tells the WhatsApp
    # webhook not to send, and the web route to show a brief holding line.
    if db.is_ai_paused(business_id, conversation_id):
        db.save_message(business_id, conversation_id, "user", message)
        logger.info(
            "conversation %s is human-handled — AI staying silent", conversation_id
        )
        return ""

    # Monthly quota = the founding plan's fair-use fuse and the cost cap that
    # stops one abused/viral business_id from draining the shared Gemini bill.
    # Over the cap we DECLINE gracefully (no model call, no 500) and email the
    # owner once; approaching it we just email the nudge and carry on.
    over, reason = _quota_state(business)
    if reason:
        _notify_quota(business, reason, schedule)
    if over:
        logger.info("quota reached for business=%s — declining turn", business_id)
        return _decline_message(business, message)

    system_prompt = build_system_prompt(business)

    # Serialize this conversation's turns: read history → model → persist all run
    # under one lock, so two rapid messages in the same thread can't interleave
    # (see _conversation_lock). Distinct conversations hold distinct locks and
    # still run fully in parallel.
    async with _conversation_lock(business_id, conversation_id):
        # This conversation's DURABLE history (scoped by business_id — the same
        # conversation_id at two businesses can never share context), capped at
        # 40 turns at read time, plus the new message in memory only.
        history = db.get_history(business_id, conversation_id, limit=40)
        history = history + [{"role": "user", "text": message}]

        # Tools are built PER TURN, each scoped to this business via its closure.
        tools = (
            make_calendar_tools(business)
            + make_memory_tools(business_id)
            + make_lead_tools(business_id)
            + make_handoff_tools(business)
        )
        # Real-estate agencies also get structured qualification + scoring +
        # CRM write-back — the core of the real-estate operator.
        if (business.get("vertical") or "").strip().lower() == "real_estate":
            from app.tools.qualify_tools import make_qualify_tools

            tools = tools + make_qualify_tools(business)
        # `activity` (the demo's live "what the AI did" feed) is opt-in: callers
        # like the demo pass a list to fill; everyone else passes nothing. We ALSO
        # keep an internal sink on every turn so the say-do verifier below can
        # reconcile the reply against the tools that actually ran. generate_reply
        # is feature-detected for the sink so a 3-arg test double still works.
        tool_activity = activity if activity is not None else []
        if _accepts_activity_sink(generate_reply):
            reply = await generate_reply(
                system_prompt, history, tools=tools, activity_sink=tool_activity
            )
        else:
            reply = await generate_reply(system_prompt, history, tools=tools)

        # Last-resort guard: llm_service already retries/recovers empty and
        # leaked replies; if EVERYTHING came back blank the caller still gets words.
        if not reply.strip():
            reply = _EMPTY_REPLY_AR if _is_arabic(message) else _EMPTY_REPLY_EN

        # Say-do verifier (observability only): reconcile what the reply CLAIMED it
        # did against the tools that actually fired, and log any gap. This never
        # changes the reply — the deterministic nets below do the recovering; this
        # is the always-on signal for when, and on which action, the model said it
        # acted without acting. Wrapped so a verifier bug can never break a turn.
        claimed_actions: list[str] = []
        try:
            for gap in say_do_verifier.detect(reply, tool_activity):
                logger.warning(
                    "SAY-DO GAP [business=%s conv=%s]: reply claimed '%s' (%r) but "
                    "no backing tool (%s) fired this turn",
                    business_id,
                    conversation_id,
                    gap["action"],
                    gap["claim"],
                    gap["expected_tool"],
                )
                # Persist it (deferred, off the reply path) so the log-only signal
                # becomes a live production reliability metric — see get_metrics.
                schedule(db.record_say_do_gap, business_id, gap["action"])
                claimed_actions.append(gap["action"])
        except Exception:  # noqa: BLE001 — observability must never break a turn
            logger.debug("say-do verifier skipped", exc_info=True)

        # Persist BOTH turns only now that the reply succeeded, and meter the
        # turn against the business's daily usage (the future billing data).
        db.save_message(business_id, conversation_id, "user", message)
        db.save_message(business_id, conversation_id, "model", reply)
        db.bump_usage(business_id)

        # Deterministic lead-capture safety net: capture_lead is stochastic and
        # can miss (an empty-reply turn skips the tool), so a caller who left a
        # number must never be silently lost. Runs in the background; no-ops when
        # the tool already captured them or they've booked.
        schedule(lead_safety.ensure_lead_captured, business, conversation_id)

        # Post-condition ledger: for every action the reply CLAIMED, enforce its
        # required effect — verify it exists, else repair it (lead, handoff) or
        # escalate to a human (booking/reschedule/cancel, which we must not guess
        # at). Generalizes the lead net to every action; deferred + best-effort.
        schedule(
            postconditions.reconcile_claims, business, conversation_id, claimed_actions
        )

        # Every 6th caller message, distill the conversation into durable caller
        # memory — deferred so the caller never waits on it. Count the DURABLE
        # total, not this capped window: a long thread's window saturates at 20
        # user turns forever (21 % 6 != 0), which silently stopped distilling
        # exactly the regulars whose preferences matter most.
        every_n = distill_service.DISTILL_EVERY_N_USER_MESSAGES
        user_turns = db.count_user_messages(business_id, conversation_id)
        if user_turns >= every_n and user_turns % every_n == 0:
            schedule(distill_service.distill_conversation, business_id, conversation_id)
    return reply
