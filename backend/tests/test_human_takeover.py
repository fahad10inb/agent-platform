"""Human takeover (supervised mode): an owner can reply to a caller by hand
from the inbox. Replying PAUSES the AI for that thread (so it won't also answer);
"Hand back to AI" resumes it. Covers the pause gate in the core, the reply /
resume / status endpoints, WhatsApp delivery, and auth/tenant scoping."""

import asyncio

import pytest

from app import chat_core, whatsapp
from app.config import get_settings

BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
ADMIN = {"X-API-Key": "admin_test_key"}
VELVET = {"X-API-Key": "bizkey_velvet_hair_demo"}


@pytest.fixture
def fake_llm(monkeypatch):
    """Stub Gemini; records every call so we can assert the AI stayed silent."""
    calls = []

    async def _fake(system_prompt, history, tools=None):
        calls.append(history)
        return "AI here, how can I help?"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    return calls


def _thread(client, cid, headers=BRIGHT):
    return client.get(
        f"/manage/bright-smile/conversations/{cid}", headers=headers
    ).json()


def test_owner_reply_takes_over_and_pauses_ai(client):
    cid = "web-take1"
    r = client.post(
        f"/manage/bright-smile/conversations/{cid}/reply",
        headers=BRIGHT,
        json={"text": "Hi, this is Dana from the clinic — happy to help!"},
    )
    assert r.status_code == 200
    assert r.json()["ai_paused"] is True

    # The reply is stored as the business's turn and shows in the transcript.
    thread = _thread(client, cid)
    assert thread[-1]["role"] == "model"
    assert "Dana from the clinic" in thread[-1]["text"]

    # And the status endpoint now reports a human is handling it.
    s = client.get(f"/manage/bright-smile/conversations/{cid}/status", headers=BRIGHT)
    assert s.json()["ai_paused"] is True


def test_ai_stays_silent_on_web_while_paused(client, fake_llm):
    cid = "web-take2"
    client.post(
        f"/manage/bright-smile/conversations/{cid}/reply",
        headers=BRIGHT,
        json={"text": "I've got this one."},
    )
    # The caller writes again on the widget while the human is handling it.
    r = client.post(
        "/chat",
        json={"message": "ok thanks!", "conversation_id": cid, "business_id": "bright-smile"},
    )
    assert r.status_code == 200
    # A brief holding line — NOT an AI-generated answer.
    assert "team" in r.json()["reply"].lower()
    # The model was never called…
    assert fake_llm == []
    # …but the caller's message was still saved for the human to see.
    thread = _thread(client, cid)
    assert thread[-1]["role"] == "user" and thread[-1]["text"] == "ok thanks!"


def test_resume_hands_back_to_ai(client, fake_llm):
    cid = "web-take3"
    client.post(
        f"/manage/bright-smile/conversations/{cid}/reply",
        headers=BRIGHT,
        json={"text": "human here"},
    )
    # Hand it back…
    r = client.post(
        f"/manage/bright-smile/conversations/{cid}/resume", headers=BRIGHT
    )
    assert r.status_code == 200 and r.json()["ai_paused"] is False

    # …now the AI answers the next message again.
    r = client.post(
        "/chat",
        json={"message": "still there?", "conversation_id": cid, "business_id": "bright-smile"},
    )
    assert r.json()["reply"] == "AI here, how can I help?"
    assert len(fake_llm) == 1


def test_whatsapp_reply_is_delivered_and_wa_stays_silent(client, monkeypatch, fake_llm):
    """A wa-* reply goes out over the Graph API, and an inbound message on a
    paused WhatsApp thread produces no outbound send."""
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_access_token", "token123")
    # Point bright-smile at a WhatsApp number so the reply endpoint delivers.
    assert client.post(
        "/manage/bright-smile", headers=BRIGHT, json={"whatsapp_phone_id": "PID999"}
    ).status_code == 200

    sent = []

    async def _fake_send(phone_id, to, text):
        sent.append((phone_id, to, text))

    monkeypatch.setattr(whatsapp, "_send_text", _fake_send)

    cid = "wa-971509998888"
    r = client.post(
        f"/manage/bright-smile/conversations/{cid}/reply",
        headers=BRIGHT,
        json={"text": "Yes, 4pm works — see you then!"},
    )
    assert r.status_code == 200 and r.json()["delivered"] is True
    assert sent == [("PID999", "971509998888", "Yes, 4pm works — see you then!")]

    # An inbound WhatsApp message on this now-paused thread: turn runs, saves the
    # message, but sends nothing (the human is handling it).
    sent.clear()
    asyncio.run(whatsapp._handle_message("bright-smile", "PID999", "971509998888", "great!"))
    assert sent == []
    assert fake_llm == []  # the AI never generated a reply
    thread = _thread(client, cid)
    assert thread[-1]["text"] == "great!" and thread[-1]["role"] == "user"


def test_web_reply_reports_not_delivered(client):
    """A web thread has no channel to push to — it's stored, delivered is False."""
    r = client.post(
        "/manage/bright-smile/conversations/web-noship/reply",
        headers=BRIGHT,
        json={"text": "noted!"},
    )
    assert r.status_code == 200
    assert r.json()["delivered"] is False


def test_reply_resume_status_need_auth_and_are_tenant_scoped(client):
    cid = "web-auth1"
    # No key → 401 on all three.
    assert client.post(f"/manage/bright-smile/conversations/{cid}/reply",
                       json={"text": "hi"}).status_code == 401
    assert client.post(f"/manage/bright-smile/conversations/{cid}/resume").status_code == 401
    assert client.get(f"/manage/bright-smile/conversations/{cid}/status").status_code == 401
    # Another tenant's key → 403 (can't touch bright-smile's threads).
    assert client.post(f"/manage/bright-smile/conversations/{cid}/reply",
                       headers=VELVET, json={"text": "hi"}).status_code == 403
    assert client.post(f"/manage/bright-smile/conversations/{cid}/resume",
                       headers=VELVET).status_code == 403
    # Admin can (it opens any business).
    assert client.post(f"/manage/bright-smile/conversations/{cid}/reply",
                       headers=ADMIN, json={"text": "hi"}).status_code == 200


def test_reply_text_is_bounded(client):
    # Empty text → 422; over the cap → 422.
    assert client.post("/manage/bright-smile/conversations/web-b/reply",
                       headers=BRIGHT, json={"text": ""}).status_code == 422
    assert client.post("/manage/bright-smile/conversations/web-b/reply",
                       headers=BRIGHT, json={"text": "x" * 5000}).status_code == 422
    # Whitespace-only strips to empty — must be rejected, not saved-and-paused.
    r = client.post("/manage/bright-smile/conversations/web-b/reply",
                    headers=BRIGHT, json={"text": "   "})
    assert r.status_code == 422
    # …and the AI must NOT be paused by that rejected reply.
    s = client.get("/manage/bright-smile/conversations/web-b/status", headers=BRIGHT)
    assert s.json()["ai_paused"] is False
