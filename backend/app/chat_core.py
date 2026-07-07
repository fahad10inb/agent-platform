"""
The channel-agnostic heart of a conversation turn.

/chat (the web widget) and /whatsapp/webhook both land here: load the business,
assemble persona + tools + history, ask the model, guard the reply, persist,
meter, and schedule the distiller. Anything channel-specific — rate limits,
HTTP error shapes, WhatsApp send calls — stays in the routes.
"""

import logging
from collections.abc import Callable

from app import db, distill_service
from app.llm_service import generate_reply
from app.prompt_service import build_system_prompt
from app.tools.calendar_tools import make_calendar_tools
from app.tools.handoff_tools import make_handoff_tools
from app.tools.leads_tools import make_lead_tools
from app.tools.memory_tools import make_memory_tools

logger = logging.getLogger("agent-platform.core")


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
