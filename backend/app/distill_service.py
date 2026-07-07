"""
Conversation distillation + memory consolidation — the background "what did we
learn?" pass, ported from the companion app's distill_call / consolidation
patterns (much smaller here: a receptionist needs preferences, not a psyche).

Two jobs, both strictly AFTER the reply has gone out (FastAPI BackgroundTasks),
so /chat latency never pays for them, and both best-effort — any failure logs
one line and vanishes:

  1. distill_conversation: re-read a conversation every few caller turns and
     ask the LLM for the caller's name + up to 3 DURABLE preference facts
     ("prefers Rana", "getting married in August"). This catches what the
     in-chat remember_about_caller tool misses — the model doesn't always
     think to save mid-conversation, but the distiller always looks.

  2. consolidate_caller_notes: once a caller's pile of notes grows past 8,
     merge them into <= 5 crisp ones and atomically replace the old set —
     so recall stays sharp instead of drowning in near-duplicates.

Junk gates (the companion's junk-free-memory bar): a note that is empty,
essay-length, or carries a phone-number-looking string never reaches storage.
"""

import asyncio
import json
import logging
import re

from google.genai import types

from app import db
from app.config import get_settings
from app.llm_service import _get_client

logger = logging.getLogger("agent-platform.distill")

# How often the /chat route schedules a distill pass: every Nth caller message.
# Frequent enough that a long booking chat gets distilled before it ends,
# rare enough that a normal 3-turn exchange costs zero extra LLM calls.
DISTILL_EVERY_N_USER_MESSAGES = 6

# A caller's notes are consolidated once they outgrow this. 8 ≈ where a
# recalled profile stops reading as "knows me" and starts reading as a log.
CONSOLIDATE_ABOVE_NOTES = 8

_DISTILL_PROMPT = (
    "You read a chat between a business's receptionist and a caller, and pull "
    "out what is worth remembering about the CALLER for their NEXT visit.\n"
    "Reply with JSON ONLY, exactly this shape:\n"
    '{"caller_name": "their name, or null if they never gave one", '
    '"facts": ["up to 3 short, durable, third-person facts"]}\n'
    "Rules: only things the caller actually said. Good facts are preferences, "
    "constraints, or life details relevant to this business ('prefers Rana as "
    "her stylist', 'getting married in August', 'allergic to ammonia dyes'). "
    "NEVER one-off logistics like a specific date or time slot — bookings "
    "already record those. NEVER anything already obvious from a booking "
    "(that they booked, when, the service name alone). NEVER phone numbers. "
    "Use an empty facts list if nothing durable came up.\n\n"
    "CONVERSATION:\n"
)

_CONSOLIDATE_PROMPT = (
    "You tidy a business's memory notes about one caller. Merge the notes "
    "below into AT MOST 5 crisp, non-redundant, third-person notes. Keep real "
    "information — usual service, preferences, allergies, meaningful visit "
    "history — and drop repetition and filler. Never invent anything.\n"
    'Reply with JSON ONLY: {"notes": ["..."]}\n\n'
    "NOTES:\n"
)

# 9+ digits, separators allowed — catches UAE mobiles (05xxxxxxxx, +9715...)
# while letting dates like 2026-07-07 (8 digits) through: booking-history notes
# legitimately carry dates, but a phone number in free-text memory is exactly
# the junk (and PII leak) the gate exists to stop.
_PHONE_LIKE = re.compile(r"\+?\d(?:[\s\-()]*\d){8,}")


def _is_junk(note: str) -> bool:
    """The storage gate: empty, essay-length, or phone-carrying notes never
    reach caller memory, no matter what the LLM produced."""
    note = (note or "").strip()
    return not note or len(note) > 200 or bool(_PHONE_LIKE.search(note))


async def _call_llm(prompt: str) -> str:
    """One low-temperature, tightly-capped Gemini call for extraction work.

    Same client/timeout discipline as llm_service.generate_reply, but tuned for
    structured output: temperature 0.2 (we want consistency, not personality)
    and ~300 tokens (a JSON blob, not a conversation). Kept as a module-level
    seam so tests can swap in a fake LLM with one monkeypatch.
    """
    settings = get_settings()
    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=300,
    )
    response = await asyncio.wait_for(
        _get_client().aio.models.generate_content(
            # The BACKGROUND model, not the chat model: pulling 3 facts into a
            # JSON blob doesn't need conversational quality, and every distill/
            # consolidate pass is pure overhead on the LLM bill.
            model=settings.gemini_background_model,
            contents=prompt,
            config=config,
        ),
        timeout=settings.llm_timeout_seconds,
    )
    return (response.text or "").strip()


def _parse_json(raw: str) -> dict | None:
    """Best-effort JSON from an LLM reply (companion's robust-parse pattern):
    strip a ``` fence if present, then decode from the first '{' that yields a
    valid object — models love to wrap JSON in prose."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    dec = json.JSONDecoder()
    for i, ch in enumerate(raw):
        if ch == "{":
            try:
                data, _ = dec.raw_decode(raw[i:])
                return data if isinstance(data, dict) else None
            except ValueError:
                continue
    return None


async def distill_conversation(business_id: str, conversation_id: str) -> None:
    """Distill one conversation into durable caller-memory facts.

    Scheduled from /chat as a background task; it must NEVER raise into the
    route, so the whole body is one try/except that logs a single line.
    """
    settings = get_settings()
    if not settings.distill_enabled:
        return
    try:
        history = db.get_history(business_id, conversation_id, limit=40)
        if not history:
            return
        # Per-turn cap so one pasted essay can't blow up the prompt (cost guard).
        transcript = "\n".join(
            f"{'caller' if t['role'] == 'user' else 'receptionist'}: {t['text'][:400]}"
            for t in history
        )
        data = _parse_json(await _call_llm(_DISTILL_PROMPT + transcript))
        if data is None:
            logger.warning("distill parse failed for business=%s conv=%s", business_id, conversation_id)
            return

        # `or ""` also swallows JSON null; models sometimes write the literal
        # word instead, so treat those as no-name too. No name = no memory key
        # = nothing to save (facts about an anonymous caller are unrecallable).
        name = str(data.get("caller_name") or "").strip()
        if not name or name.lower() in {"null", "none", "unknown", "caller"}:
            logger.info("distill found no caller name for business=%s conv=%s", business_id, conversation_id)
            return

        facts = [str(f).strip() for f in (data.get("facts") or [])][:3]
        # Same case-insensitive dedup the remember_about_caller tool uses — the
        # distiller and the tool write into one store and must not fight.
        existing = {n.strip().lower() for n in db.get_caller_memory(business_id, name)}
        saved = 0
        for fact in facts:
            if _is_junk(fact) or fact.lower() in existing:
                continue
            db.save_caller_memory(business_id, name, fact)
            existing.add(fact.lower())
            saved += 1
        logger.info(
            "distilled business=%s conv=%s caller_known facts=%d saved=%d",
            business_id, conversation_id, len(facts), saved,
        )
        # The distiller is also the consolidation trigger: it's the only writer
        # that knows the pile just grew (checks its own flag + threshold inside).
        await consolidate_caller_notes(business_id, name)
    except Exception as exc:  # noqa: BLE001 — background work must never propagate
        logger.warning(
            "distill failed for business=%s conv=%s: %s",
            business_id, conversation_id, str(exc)[:200],
        )


async def consolidate_caller_notes(business_id: str, name: str) -> None:
    """Merge an overgrown caller-notes pile into <= 5 crisp notes and replace
    the old set atomically. On ANY failure — LLM error, garbage JSON, all notes
    junk-gated — the old notes stay untouched: losing memory is strictly worse
    than keeping a slightly messy pile.
    """
    settings = get_settings()
    if not settings.consolidate_enabled:
        return
    try:
        notes = db.get_caller_memory(business_id, name)
        if len(notes) <= CONSOLIDATE_ABOVE_NOTES:
            return
        listing = "\n".join(f"- {n}" for n in notes)
        data = _parse_json(await _call_llm(_CONSOLIDATE_PROMPT + listing))
        if data is None:
            logger.warning("consolidate parse failed for business=%s", business_id)
            return
        merged = [str(n).strip() for n in (data.get("notes") or [])]
        merged = [n for n in merged if not _is_junk(n)][:5]
        if not merged:
            # Replacing a real history with nothing would be data loss, not tidying.
            logger.warning("consolidate produced no usable notes for business=%s — keeping old", business_id)
            return
        db.replace_caller_memory(business_id, name, merged)
        logger.info("consolidated business=%s notes %d -> %d", business_id, len(notes), len(merged))
    except Exception as exc:  # noqa: BLE001 — background work must never propagate
        logger.warning("consolidate failed for business=%s: %s", business_id, str(exc)[:200])
