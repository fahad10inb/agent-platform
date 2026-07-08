"""Batch-2 reliability: the double-booking class — retry-safety on tool turns,
per-conversation serialization, WhatsApp duplicate-delivery dedup, and the
reschedule overlap check. Plus the distiller-cadence fix on long threads."""

import asyncio
import datetime
import zoneinfo

import pytest

from app import chat_core, db, llm_service, whatsapp
from app.tools import calendar_tools as ct
from app.tools.calendar_tools import make_calendar_tools


# ── llm_service: a tool turn must not blind-retry on timeout ─────────────────
def test_tool_turn_does_not_retry_on_timeout(monkeypatch):
    """A retry could re-run a booking that already committed before the timeout
    — so with tools present, a timeout fails the turn (one attempt), never two."""
    attempts = {"n": 0}

    async def _always_timeout(*a, **k):
        attempts["n"] += 1
        raise asyncio.TimeoutError()

    client = type("C", (), {"aio": type("A", (), {"models": type("M", (), {
        "generate_content": staticmethod(_always_timeout)})()})()})()
    monkeypatch.setattr(llm_service, "_get_client", lambda: client)

    def a_tool():
        pass

    try:
        asyncio.run(llm_service.generate_reply("p", [{"role": "user", "text": "book me"}], tools=[a_tool]))
        assert False, "should have raised"
    except asyncio.TimeoutError:
        pass
    assert attempts["n"] == 1  # NO second attempt with tools present


def test_toolless_turn_still_retries_once(monkeypatch):
    """A tool-less call has no side effects, so its one transient-blip retry
    survives."""
    attempts = {"n": 0}

    async def _fail_then_ok(*a, **k):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("blip")
        return type("R", (), {"text": "recovered", "automatic_function_calling_history": None})()

    client = type("C", (), {"aio": type("A", (), {"models": type("M", (), {
        "generate_content": staticmethod(_fail_then_ok)})()})()})()
    monkeypatch.setattr(llm_service, "_get_client", lambda: client)

    reply = asyncio.run(llm_service.generate_reply("p", [{"role": "user", "text": "hi"}]))
    assert reply == "recovered"
    assert attempts["n"] == 2


# ── chat_core: same conversation serializes; different ones don't ────────────
def test_same_conversation_turns_run_one_at_a_time(client, monkeypatch):
    """Two concurrent turns in one thread must not interleave: the second must
    see the first's saved messages in its history."""
    seen_history_lengths = []

    async def _fake_reply(system_prompt, history, tools=None):
        seen_history_lengths.append(len([t for t in history if t["role"] == "user"]))
        await asyncio.sleep(0.02)  # hold the lock so a race would interleave
        return "ok"

    monkeypatch.setattr(chat_core, "generate_reply", _fake_reply)

    async def _drive():
        await asyncio.gather(
            chat_core.run_turn("bright-smile", "web-serial01", "first", lambda *a: None),
            chat_core.run_turn("bright-smile", "web-serial01", "second", lambda *a: None),
        )

    asyncio.run(_drive())
    # Whichever ran first saw 1 user turn; the second, serialized, saw 2.
    assert sorted(seen_history_lengths) == [1, 2]


# ── whatsapp: duplicate delivery (same wamid) is processed once ──────────────
def test_duplicate_wamid_is_dropped(monkeypatch):
    whatsapp._SEEN_WAMIDS.clear()
    assert whatsapp._already_processed("wamid.ABC") is False  # first sighting
    assert whatsapp._already_processed("wamid.ABC") is True   # redelivery
    assert whatsapp._already_processed("wamid.XYZ") is False  # a different one


# ── calendar: reschedule respects duration overlap ───────────────────────────
@pytest.fixture
def frozen_clock(monkeypatch):
    """Pin 'now' so the test dates stay inside the 60-day advance window."""
    frozen = datetime.datetime(2026, 7, 8, 8, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))
    monkeypatch.setattr(ct, "_now", lambda: frozen)


def _cal():
    db.replace_services("velvet-hair", [
        {"name": "colour", "duration_min": 90, "price": "250"},
        {"name": "trim", "duration_min": 30, "price": "60"},
    ])
    biz = {"id": "velvet-hair", "open_hour": 9, "close_hour": 18, "slot_minutes": 30}
    return {f.__name__: f for f in make_calendar_tools(biz)}


def test_reschedule_is_blocked_by_a_duration_overlap(client, frozen_clock):
    cal = _cal()
    # A 90-min colour at 2:00 PM, and a trim at 5:00 PM we'll try to move.
    assert cal["book_appointment"]("2026-07-20", "2:00 PM", "Mona", "0501111111", "colour")["status"] == "confirmed"
    assert cal["book_appointment"]("2026-07-20", "5:00 PM", "Sara", "0502222222", "trim")["status"] == "confirmed"
    # Moving the trim to 2:30 PM lands inside the colour (2:00-3:30) — must fail,
    # even though 2:30 PM isn't an exact existing start.
    out = cal["reschedule_appointment"]("Sara", "2026-07-20", "5:00 PM",
                                        "2026-07-20", "2:30 PM", phone_last4="2222")
    assert out["status"] == "unavailable"


def test_reschedule_within_free_time_succeeds(client, frozen_clock):
    cal = _cal()
    assert cal["book_appointment"]("2026-07-20", "2:00 PM", "Mona", "0501111111", "colour")["status"] == "confirmed"
    assert cal["book_appointment"]("2026-07-20", "5:00 PM", "Sara", "0502222222", "trim")["status"] == "confirmed"
    # Moving the trim to 4:00 PM (clear of the colour) works — and it must not
    # collide with its own old slot on the same day.
    out = cal["reschedule_appointment"]("Sara", "2026-07-20", "5:00 PM",
                                        "2026-07-20", "4:00 PM", phone_last4="2222")
    assert out["status"] == "rescheduled"


# ── distiller keeps firing past a saturated 40-message window ─────────────────
def test_distiller_fires_on_the_durable_count_not_the_window(client, monkeypatch):
    scheduled = []

    async def _fake_reply(system_prompt, history, tools=None):
        return "ok"

    monkeypatch.setattr(chat_core, "generate_reply", _fake_reply)

    # Pre-load 100 prior user messages (far past the 40-turn history-window cap).
    for i in range(100):
        db.save_message("bright-smile", "web-long01", "user", f"m{i}")
        db.save_message("bright-smile", "web-long01", "model", "r")

    def _schedule(fn, *a):
        scheduled.append(a)

    # The 102nd user message: 102 % 6 == 0 → the distiller must be scheduled.
    # The old window-based count saturated at 21 and would have missed it.
    asyncio.run(chat_core.run_turn("bright-smile", "web-long01", "the 101st", _schedule))
    asyncio.run(chat_core.run_turn("bright-smile", "web-long01", "the 102nd", _schedule))
    assert scheduled  # fired on the true durable count
