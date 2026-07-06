"""Conversation distillation + memory consolidation: the background pass that
turns finished chats into durable caller memory and keeps that memory crisp
(ported from the companion's distill_call / consolidation patterns). The LLM is
faked with a monkeypatch on the single _call_llm seam; the db is the conftest
in-memory fake — so these tests exercise the real parsing, dedup, junk-gating
and replace logic without a network."""

import asyncio
import json

import pytest

from app import db, distill_service
from app import main as main_module

BIZ = "bright-smile"
CONV = "distill-conv"


def _seed_conversation(n_user=6, biz=BIZ, conv=CONV):
    for i in range(n_user):
        db.save_message(biz, conv, "user", f"caller line {i}")
        db.save_message(biz, conv, "model", f"receptionist line {i}")


@pytest.fixture
def fake_llm(monkeypatch):
    """Swap the one LLM seam for a canned reply; record every prompt sent."""
    state = {
        "calls": [],
        "reply": json.dumps(
            {"caller_name": "Zara Malik", "facts": ["prefers morning appointments"]}
        ),
        "raise": False,
    }

    async def _fake(prompt):
        state["calls"].append(prompt)
        if state["raise"]:
            raise RuntimeError("gemini down")
        return state["reply"]

    monkeypatch.setattr(distill_service, "_call_llm", _fake)
    return state


# ── distillation ──────────────────────────────────────────────────────────────
def test_distill_extracts_facts_and_saves_them(client, fake_llm):
    _seed_conversation()
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))
    assert db.get_caller_memory(BIZ, "Zara Malik") == ["prefers morning appointments"]
    # The transcript (not just the last message) reached the LLM.
    assert "caller line 0" in fake_llm["calls"][0]


def test_distill_dedups_case_insensitively(client, fake_llm):
    """Same dedup the remember_about_caller tool uses — the distiller must not
    re-add a fact the model already saved mid-chat, whatever the casing."""
    _seed_conversation()
    db.save_caller_memory(BIZ, "Zara Malik", "Prefers Morning Appointments ")
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))
    assert len(db.get_caller_memory(BIZ, "Zara Malik")) == 1


def test_distill_respects_kill_switch(client, fake_llm, monkeypatch):
    _seed_conversation()
    monkeypatch.setattr(distill_service.get_settings(), "distill_enabled", False)
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))
    assert fake_llm["calls"] == []  # not even an LLM call — the flag is a cost switch
    assert db.get_caller_memory(BIZ, "Zara Malik") == []


def test_distill_without_a_name_writes_nothing(client, fake_llm, state):
    """No name = no memory key: facts about an anonymous caller can never be
    recalled, so storing them would just be junk rows."""
    _seed_conversation()
    fake_llm["reply"] = json.dumps({"caller_name": None, "facts": ["likes tea"]})
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))
    assert state["memory"] == []


def test_distill_junk_gates_llm_output(client, fake_llm):
    """Even facts the LLM swears by are gated: empty, essay-length, or
    phone-carrying strings never reach storage."""
    _seed_conversation()
    fake_llm["reply"] = json.dumps(
        {
            "caller_name": "Zara Malik",
            "facts": ["  ", "call her back on 0501234567", "prefers Rana"],
        }
    )
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))
    assert db.get_caller_memory(BIZ, "Zara Malik") == ["prefers Rana"]


def test_distill_survives_llm_garbage(client, fake_llm, state):
    """A non-JSON reply (or any internal error) must vanish quietly — this runs
    as a background task and can never break anything."""
    _seed_conversation()
    fake_llm["reply"] = "sorry, I can't help with that"
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))  # no raise
    assert state["memory"] == []


def test_distill_parses_json_wrapped_in_fences_and_prose(client, fake_llm):
    _seed_conversation()
    fake_llm["reply"] = (
        'Sure! Here you go:\n```json\n{"caller_name": "Zara Malik", '
        '"facts": ["allergic to ammonia dyes"]}\n```'
    )
    asyncio.run(distill_service.distill_conversation(BIZ, CONV))
    assert db.get_caller_memory(BIZ, "Zara Malik") == ["allergic to ammonia dyes"]


# ── consolidation ─────────────────────────────────────────────────────────────
def _seed_notes(n=10, name="Zara Malik"):
    for i in range(n):
        db.save_caller_memory(BIZ, name, f"note number {i}")


def test_consolidation_merges_overgrown_notes(client, fake_llm):
    _seed_notes(10)
    fake_llm["reply"] = json.dumps(
        {"notes": ["usual: blow-dry with Rana", "prefers mornings", "getting married in August"]}
    )
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert db.get_caller_memory(BIZ, "Zara Malik") == [
        "usual: blow-dry with Rana",
        "prefers mornings",
        "getting married in August",
    ]


def test_consolidation_never_exceeds_five_notes(client, fake_llm):
    _seed_notes(10)
    fake_llm["reply"] = json.dumps({"notes": [f"merged {i}" for i in range(8)]})
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert len(db.get_caller_memory(BIZ, "Zara Malik")) == 5


def test_consolidation_filters_junk_notes(client, fake_llm):
    _seed_notes(10)
    fake_llm["reply"] = json.dumps(
        {"notes": ["", "x" * 250, "her number is 050 123 4567", "prefers mornings"]}
    )
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert db.get_caller_memory(BIZ, "Zara Malik") == ["prefers mornings"]


def test_consolidation_failure_keeps_old_notes(client, fake_llm):
    """Losing memory is strictly worse than a messy pile: if the LLM dies (or
    returns garbage), replace is never called and all 10 notes survive."""
    _seed_notes(10)
    fake_llm["raise"] = True
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert len(db.get_caller_memory(BIZ, "Zara Malik")) == 10

    fake_llm["raise"] = False
    fake_llm["reply"] = json.dumps({"notes": []})  # "merged into nothing" = failure too
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert len(db.get_caller_memory(BIZ, "Zara Malik")) == 10


def test_consolidation_skips_small_piles(client, fake_llm):
    """Under the threshold there's nothing to tidy — and no LLM cost."""
    _seed_notes(5)
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert fake_llm["calls"] == []
    assert len(db.get_caller_memory(BIZ, "Zara Malik")) == 5


def test_consolidation_respects_kill_switch(client, fake_llm, monkeypatch):
    _seed_notes(10)
    monkeypatch.setattr(distill_service.get_settings(), "consolidate_enabled", False)
    asyncio.run(distill_service.consolidate_caller_notes(BIZ, "Zara Malik"))
    assert fake_llm["calls"] == []
    assert len(db.get_caller_memory(BIZ, "Zara Malik")) == 10


# ── /chat wiring ──────────────────────────────────────────────────────────────
def test_chat_schedules_distill_every_sixth_user_message(client, monkeypatch):
    """The route schedules distillation as a BACKGROUND task on the 6th, 12th…
    caller message — and never off-cadence (that would be a per-turn LLM tax)."""
    scheduled = []

    async def _spy(business_id, conversation_id):
        scheduled.append((business_id, conversation_id))

    monkeypatch.setattr(main_module.distill_service, "distill_conversation", _spy)

    async def _fake_reply(system_prompt, history, tools=None):
        return "ok"

    monkeypatch.setattr(main_module, "generate_reply", _fake_reply)

    # 5 caller turns already on file; the 6th arrives through /chat.
    for i in range(5):
        db.save_message(BIZ, "c-six", "user", f"m{i}")
        db.save_message(BIZ, "c-six", "model", "r")
    r = client.post("/chat", json={"message": "sixth", "conversation_id": "c-six", "business_id": BIZ})
    assert r.status_code == 200
    assert scheduled == [(BIZ, "c-six")]  # TestClient runs background tasks post-response

    # The 7th message is off-cadence: nothing new is scheduled.
    client.post("/chat", json={"message": "seventh", "conversation_id": "c-six", "business_id": BIZ})
    assert len(scheduled) == 1


def test_chat_does_not_distill_short_conversations(client, monkeypatch):
    scheduled = []

    async def _spy(business_id, conversation_id):
        scheduled.append((business_id, conversation_id))

    monkeypatch.setattr(main_module.distill_service, "distill_conversation", _spy)

    async def _fake_reply(system_prompt, history, tools=None):
        return "ok"

    monkeypatch.setattr(main_module, "generate_reply", _fake_reply)
    client.post("/chat", json={"message": "hi", "conversation_id": "c-one", "business_id": BIZ})
    assert scheduled == []
