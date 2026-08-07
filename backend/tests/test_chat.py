"""The chat pipeline: tenant isolation of conversation history (the worst bug
the review found), history capping, rollback on failure, and input bounds."""

import pytest

from app import chat_core
from app import main as main_module


@pytest.fixture
def fake_llm(monkeypatch):
    """Stub Gemini; records the history each call received."""
    calls = []

    async def _fake(system_prompt, history, tools=None):
        calls.append([dict(t) for t in history])
        return "ok"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    return calls


def test_same_conversation_id_never_bleeds_across_businesses(client, fake_llm):
    client.post(
        "/chat",
        json={
            "message": "my dental secret",
            "conversation_id": "shared",
            "business_id": "bright-smile",
        },
    )
    client.post(
        "/chat",
        json={
            "message": "hello salon",
            "conversation_id": "shared",
            "business_id": "velvet-hair",
        },
    )
    # The salon's model call must contain ONLY the salon's message.
    salon_history = fake_llm[1]
    texts = " ".join(t["text"] for t in salon_history)
    assert "dental secret" not in texts
    assert "hello salon" in texts


def test_unknown_business_is_404(client, fake_llm):
    r = client.post("/chat", json={"message": "hi", "business_id": "nope"})
    assert r.status_code == 404


def test_message_bounds(client, fake_llm):
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 5000}).status_code == 422


def test_history_survives_and_is_capped(client, fake_llm):
    from app import db

    # A marathon conversation persisted in the DB (100 turns)...
    for i in range(100):
        db.save_message("bright-smile", "long", "user", f"t{i}")
    r = client.post(
        "/chat",
        json={
            "message": "latest",
            "conversation_id": "long",
            "business_id": "bright-smile",
        },
    )
    assert r.status_code == 200
    # ...reaches the model trimmed to the cap: 40 stored turns + the new message.
    assert len(fake_llm[0]) <= 41
    assert fake_llm[0][-1]["text"] == "latest"
    # And the new exchange was persisted durably (survives a deploy).
    hist = db.get_history("bright-smile", "long", limit=100)
    assert hist[-1] == {"role": "model", "text": "ok"}


def test_failed_turn_is_rolled_back(client, monkeypatch):
    from app import db

    async def _boom(system_prompt, history, tools=None):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(chat_core, "generate_reply", _boom)
    r = client.post(
        "/chat",
        json={"message": "hi", "conversation_id": "c1", "business_id": "bright-smile"},
    )
    assert r.status_code == 500
    # The unanswered user turn must not haunt the next request's context —
    # nothing is persisted unless the reply succeeded.
    assert db.get_history("bright-smile", "c1") == []


def test_usage_is_metered_and_readable(client, fake_llm):
    client.post("/chat", json={"message": "hi", "business_id": "bright-smile"})
    client.post("/chat", json={"message": "hello again", "business_id": "bright-smile"})
    r = client.get(
        "/usage?business_id=bright-smile",
        headers={"X-API-Key": "bizkey_bright_smile_demo"},
    )
    assert r.status_code == 200
    assert r.json()[0]["messages"] == 2
    # And it's tenant-protected like everything else.
    assert client.get("/usage?business_id=bright-smile").status_code == 401


def test_owner_metrics_roll_up(client, fake_llm):
    """The value-proof numbers: chats, questions, and the hours-saved estimate.

    Fair-billing rule: c1 (two caller messages) counts as a conversation; c2's
    single hello is a drive-by and must NOT — the landing page pledges that in
    writing. messages_30d stays raw (it measures workload, not billing)."""
    client.post(
        "/chat",
        json={"message": "hi", "conversation_id": "c1", "business_id": "bright-smile"},
    )
    client.post(
        "/chat",
        json={
            "message": "prices?",
            "conversation_id": "c1",
            "business_id": "bright-smile",
        },
    )
    client.post(
        "/chat",
        json={
            "message": "hello",
            "conversation_id": "c2",
            "business_id": "bright-smile",
        },
    )
    r = client.get(
        "/metrics?business_id=bright-smile",
        headers={"X-API-Key": "bizkey_bright_smile_demo"},
    )
    assert r.status_code == 200
    m = r.json()
    assert m["conversations_30d"] == 1 and m["messages_30d"] == 3
    assert m["hours_saved_30d_estimate"] == round(1 * 4 / 60, 1)
    assert client.get("/metrics?business_id=bright-smile").status_code == 401


def test_after_hours_leads_are_counted(client, state):
    """The ROI number: leads that arrive while the business is CLOSED (outside its
    Dubai-local open->close hours) are counted separately — the 'leads you'd have
    lost' figure the owner renews for."""
    import datetime

    biz = "bright-smile"
    state["businesses"][biz]["open_hour"] = 9
    state["businesses"][biz]["close_hour"] = 17
    utc = datetime.timezone.utc
    # Dubai = UTC+4: 19:00 UTC = 23:00 Dubai (after hours); 08:00 UTC = 12:00 Dubai (open).
    after = datetime.datetime(2026, 8, 1, 19, 0, tzinfo=utc)
    during = datetime.datetime(2026, 8, 1, 8, 0, tzinfo=utc)
    state["leads"].extend(
        {
            "id": i,
            "business_id": biz,
            "name": "x",
            "phone": str(i),
            "interest": "2BR",
            "notes": "",
            "created_at": ca,
        }
        for i, ca in [(9001, after), (9002, after), (9003, during)]
    )
    m = client.get(
        "/metrics?business_id=bright-smile",
        headers={"X-API-Key": "bizkey_bright_smile_demo"},
    ).json()
    assert m["leads_30d"] == 3
    assert m["after_hours_leads_30d"] == 2  # the two that landed at 23:00 Dubai


def test_deterministic_fallbacks_match_the_callers_language(client, monkeypatch):
    """The hardcoded lines (quota decline, empty-reply catch) can't ask the model
    to translate — so an Arabic caller must still get Arabic, never a jarring
    English line mid-conversation."""
    from app.chat_core import _decline_message, _is_arabic

    assert _is_arabic("مرحبا عندكم شقق؟") and not _is_arabic("hi, any flats?")
    assert "شكراً" in _decline_message({"transfer_number": ""}, "مرحبا")
    assert "Thanks" in _decline_message({"transfer_number": ""}, "hello")

    # The empty-reply catch, end to end: a blank model reply to an Arabic caller
    # comes back in Arabic.
    async def _blank(system_prompt, history, tools=None):
        return ""

    monkeypatch.setattr(chat_core, "generate_reply", _blank)
    r = client.post(
        "/chat",
        json={
            "message": "مرحبا، عندكم شقق غرفتين؟",
            "conversation_id": "ar-fallback",
            "business_id": "skyline-realty",
        },
    )
    assert r.status_code == 200
    assert "المعذرة" in r.json()["reply"]  # Arabic fallback, not the English one


def test_say_do_gap_is_recorded_as_a_live_metric(client, monkeypatch):
    """When a reply CLAIMS it captured the lead but no tool fired, the gap is
    persisted — turning the log-only signal into a live production reliability
    number, not just an offline eval figure."""

    async def _claims(system_prompt, history, tools=None):
        return "Got it — I've saved your details, an agent will call you."

    monkeypatch.setattr(chat_core, "generate_reply", _claims)
    client.post(
        "/chat",
        json={
            "message": "I'm Sara, 0501234567",
            "conversation_id": "gap-1",
            "business_id": "bright-smile",
        },
    )
    m = client.get(
        "/metrics?business_id=bright-smile",
        headers={"X-API-Key": "bizkey_bright_smile_demo"},
    ).json()
    assert m["say_do_gaps_30d"] >= 1  # the claim-without-tool was recorded
    assert "leads_recovered_30d" in m  # the net's rescue count is exposed too


def test_drive_by_conversations_never_count(client, fake_llm):
    """Pledge #1 as behavior: any number of one-message threads roll up to ZERO
    conversations, and a thread starts counting the moment its second caller
    message lands."""
    for i in range(3):
        client.post(
            "/chat",
            json={
                "message": "spam",
                "conversation_id": f"drive-{i}",
                "business_id": "bright-smile",
            },
        )
    headers = {"X-API-Key": "bizkey_bright_smile_demo"}
    m = client.get("/metrics?business_id=bright-smile", headers=headers).json()
    assert m["conversations_30d"] == 0 and m["conversations_today"] == 0
    assert m["messages_30d"] == 3  # the workload number stays honest too — raw

    client.post(
        "/chat",
        json={
            "message": "actually, a question",
            "conversation_id": "drive-0",
            "business_id": "bright-smile",
        },
    )
    m = client.get("/metrics?business_id=bright-smile", headers=headers).json()
    assert m["conversations_30d"] == 1  # drive-0 graduated; the other two never count


def test_bookings_pagination(client):
    from app import db

    for i in range(7):
        db.save_booking(
            "bright-smile", "2026-08-01", f"{i + 1}:00 PM", f"P{i}", "050", "x"
        )
    page = client.get(
        "/bookings?business_id=bright-smile&limit=3&offset=3",
        headers={"X-API-Key": "bizkey_bright_smile_demo"},
    )
    assert page.status_code == 200
    assert len(page.json()) == 3
    assert (
        client.get(
            "/bookings?business_id=bright-smile&limit=9999",
            headers={"X-API-Key": "bizkey_bright_smile_demo"},
        ).status_code
        == 422
    )  # limit is bounded


def test_production_errors_hide_internals(client, monkeypatch):
    async def _boom(system_prompt, history, tools=None):
        raise RuntimeError("SECRET_DB_PASSWORD in traceback")

    monkeypatch.setattr(chat_core, "generate_reply", _boom)
    monkeypatch.setattr(main_module.settings, "environment", "production")
    r = client.post("/chat", json={"message": "hi", "business_id": "bright-smile"})
    assert r.status_code == 500
    assert "SECRET_DB_PASSWORD" not in r.text
