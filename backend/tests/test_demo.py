"""The live demo: the same brain as /chat, but it also reports the tools the model
ACTUALLY executed, so a prospect watching a demo sees the work (lead captured,
scored, permit withheld, viewing booked) instead of just a chat bubble."""

import pytest

from app import chat_core, db
from app.demo_events import humanize


# ── the mapping (raw tool calls → the operator-facing feed) ───────────────────
def test_lead_capture_and_a_grade_qualification_read_as_wins():
    events = humanize([
        {"name": "capture_lead",
         "args": {"name": "Ahmed", "phone": "0501234567", "interest": "2BR JVC"},
         "result": {"status": "saved"}},
        {"name": "qualify_lead",
         "args": {"budget": "1.5M", "area": "JVC", "bedrooms": "2", "pay_method": "cash"},
         "result": {"grade": "A"}},
    ])
    assert events[0]["title"] == "Lead captured"
    assert "Ahmed" in events[0]["detail"] and events[0]["tone"] == "ok"
    assert events[1]["title"] == "Qualified & scored"
    assert events[1]["badge"] == "A" and events[1]["tone"] == "hot"   # an A lead is the money moment
    assert "1.5M" in events[1]["detail"] and "cash" in events[1]["detail"]


def test_booking_and_a_refused_double_booking_are_told_apart():
    booked, refused = humanize([
        {"name": "book_appointment",
         "args": {"date": "2026-07-16", "time": "4:00 PM", "patient_name": "Ahmed"},
         "result": {"status": "confirmed"}},
        {"name": "book_appointment",
         "args": {"date": "2026-07-16", "time": "4:00 PM", "patient_name": "Omar"},
         "result": {"status": "unavailable"}},
    ])
    assert booked["title"] == "Viewing booked" and booked["tone"] == "ok"
    assert "no double-booking" in refused["title"] and refused["tone"] == "warn"


def test_compliance_and_escalation_are_surfaced_not_hidden():
    """The moments that reassure a cautious owner must be VISIBLE in the demo."""
    events = humanize([
        {"name": "request_human", "args": {"reason": "wants to negotiate price"}, "result": {}},
        {"name": "stop_contact", "args": {"phone": "0501234567"}, "result": {}},
    ])
    assert events[0]["title"] == "Handed to a human" and events[0]["tone"] == "warn"
    assert events[1]["badge"] == "PDPL" and events[1]["tone"] == "warn"


def test_unmapped_tool_still_shows_rather_than_vanishing():
    (ev,) = humanize([{"name": "some_new_tool", "args": {}, "result": None}])
    assert ev["title"] == "Some new tool"


def test_no_tools_run_means_an_empty_feed():
    assert humanize([]) == []


def test_the_sdk_result_envelope_is_unwrapped():
    """google-genai reports a tool result as {"result": {...}}. Reading the
    envelope instead of the payload silently loses every field — that is exactly
    how the A/B/C grade and the free-slot count vanished from a live demo run.
    qualify_lead returns its grade as `score`."""
    (graded,) = humanize([
        {"name": "qualify_lead", "args": {"budget": "1.5M", "area": "JVC"},
         "result": {"result": {"status": "qualified", "score": "A", "reason": "cash + urgent"}}},
    ])
    assert graded["badge"] == "A" and graded["tone"] == "hot"

    (slots,) = humanize([
        {"name": "check_availability", "args": {"date": "2026-07-16"},
         "result": {"result": {"available_slots": ["9:00 AM", "9:30 AM"]}}},
    ])
    assert "2 slots free" in slots["detail"]

    (refused,) = humanize([
        {"name": "book_appointment", "args": {"date": "2026-07-16", "time": "4:00 PM"},
         "result": {"result": {"status": "unavailable"}}},
    ])
    assert refused["tone"] == "warn" and "no double-booking" in refused["title"]


# ── the endpoints ────────────────────────────────────────────────────────────
def test_demo_page_and_context_are_served(client):
    assert client.get("/demo").status_code == 200

    db.replace_listings("skyline-realty", [
        {"title": "2BR JVC", "area": "JVC", "bedrooms": 2, "price": "1.4M",
         "purpose": "sale", "permit_number": "7112233", "reference": "", "notes": ""},
        {"title": "1BR Marina", "area": "Marina", "bedrooms": 1, "price": "900k",
         "purpose": "sale", "permit_number": "", "reference": "", "notes": ""},
    ])
    r = client.get("/demo/context?business_id=skyline-realty")
    assert r.status_code == 200
    c = r.json()
    # The panel proves the agent is grounded in THEIR inventory — including the
    # unpermitted row, whose price the agent is not allowed to quote.
    assert c["listings"] == 2
    assert c["listings_permitted"] == 1 and c["listings_unpermitted"] == 1
    assert c["vertical"] == "real_estate"

    assert client.get("/demo/context?business_id=nope").status_code == 404


def test_demo_chat_returns_the_reply_and_the_real_tool_activity(client, monkeypatch):
    """The feed must reflect tools the model actually ran — via the activity sink,
    not a script. A turn that runs no tools reports no events."""
    async def _fake(system_prompt, history, tools=None, activity_sink=None):
        if activity_sink is not None:
            activity_sink.append({
                "name": "capture_lead",
                "args": {"name": "Ahmed", "phone": "0501234567"},
                "result": {"status": "saved"},
            })
        return "Got it — I've noted your details."

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    r = client.post("/demo/chat", json={
        "message": "I'm Ahmed, 0501234567 — looking in JVC",
        "conversation_id": "demo-1", "business_id": "skyline-realty",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "Got it — I've noted your details."
    assert len(body["events"]) == 1
    assert body["events"][0]["title"] == "Lead captured"


def test_demo_chat_with_no_tool_calls_reports_an_empty_feed(client, monkeypatch):
    async def _quiet(system_prompt, history, tools=None, activity_sink=None):
        return "We're open 9 to 6."

    monkeypatch.setattr(chat_core, "generate_reply", _quiet)
    r = client.post("/demo/chat", json={
        "message": "what are your hours?", "conversation_id": "demo-2",
        "business_id": "skyline-realty",
    })
    assert r.status_code == 200 and r.json()["events"] == []


def test_demo_chat_unknown_business_is_404(client, monkeypatch):
    async def _fake(system_prompt, history, tools=None, activity_sink=None):
        return "hi"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    r = client.post("/demo/chat", json={
        "message": "hi", "conversation_id": "demo-3", "business_id": "ghost",
    })
    assert r.status_code == 404


def test_the_normal_chat_route_is_untouched_by_the_activity_sink(client, monkeypatch):
    """/chat and WhatsApp must keep working with a plain 3-arg generate_reply —
    the sink is opt-in, so the production path never passes it."""
    calls = []

    async def _fake(system_prompt, history, tools=None):   # NOTE: no activity_sink
        calls.append(1)
        return "Hello!"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    r = client.post("/chat", json={
        "message": "hi", "conversation_id": "web-x", "business_id": "skyline-realty",
    })
    assert r.status_code == 200 and r.json()["reply"] == "Hello!"
    assert calls == [1]
