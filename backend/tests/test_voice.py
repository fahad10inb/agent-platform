"""Inbound voice channel (Twilio ConversationRelay → chat_core.run_turn).

SCAFFOLD tests: they lock in the flag-gating, the TwiML we answer with, the
Twilio-signature check, and the relay message handling (setup → prompt → spoken
reply, reusing the same brain as chat/WhatsApp). They do NOT prove a live call
works — that needs a real Twilio number + Deepgram/ElevenLabs + an actual call."""

import pytest
from starlette.websockets import WebSocketDisconnect

from app import chat_core
from app.config import get_settings
from app.voice import _twilio_signature


@pytest.fixture
def voice_on(monkeypatch):
    """Turn the channel on for a test (default is OFF)."""
    monkeypatch.setattr(get_settings(), "voice_enabled", True)


@pytest.fixture
def fake_turn(monkeypatch):
    """Stub the brain; record every (business_id, conversation_id, text)."""
    calls = []

    async def _fake(business_id, conversation_id, message, schedule):
        calls.append((business_id, conversation_id, message))
        return "أهلاً! كيف أقدر أساعدك؟"

    monkeypatch.setattr(chat_core, "run_turn", _fake)
    return calls


# ── flag gating ──────────────────────────────────────────────────────────────
def test_incoming_plays_dead_when_disabled(client):
    # Default OFF → the webhook 404s (no channel exposed).
    r = client.post("/voice/incoming?business_id=bright-smile")
    assert r.status_code == 404


def test_relay_closes_immediately_when_disabled(client):
    with client.websocket_connect("/voice/relay") as ws:
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


# ── the incoming webhook / TwiML ─────────────────────────────────────────────
def test_incoming_returns_conversationrelay_twiml(client, voice_on):
    r = client.post("/voice/incoming?business_id=bright-smile")
    assert r.status_code == 200
    body = r.text
    assert "<ConversationRelay" in body
    # The relay socket, the tenant parameter, the STT/TTS providers and language.
    assert 'url="wss://testserver/voice/relay"' in body
    assert 'name="business_id" value="bright-smile"' in body
    assert 'language="ar-AE"' in body
    assert 'transcriptionProvider="Deepgram"' in body and 'ttsProvider="ElevenLabs"' in body
    # The business name is spoken in the greeting.
    assert "Bright Smile" in body


def test_incoming_unknown_or_missing_business_is_404(client, voice_on):
    assert client.post("/voice/incoming?business_id=nope").status_code == 404
    assert client.post("/voice/incoming").status_code == 404


# ── Twilio signature ─────────────────────────────────────────────────────────
def test_incoming_checks_twilio_signature_when_token_set(client, voice_on, monkeypatch):
    monkeypatch.setattr(get_settings(), "twilio_auth_token", "tok_secret")
    url = "http://testserver/voice/incoming?business_id=bright-smile"
    form = {"CallSid": "CA1", "From": "+971501234567", "To": "+97144000000"}
    good = _twilio_signature("tok_secret", url, form)

    # Correct signature → 200.
    r = client.post(
        "/voice/incoming?business_id=bright-smile",
        data=form, headers={"X-Twilio-Signature": good},
    )
    assert r.status_code == 200
    # Forged / missing signature → 403.
    bad = client.post(
        "/voice/incoming?business_id=bright-smile",
        data=form, headers={"X-Twilio-Signature": "nope"},
    )
    assert bad.status_code == 403


# ── the relay socket ─────────────────────────────────────────────────────────
def test_relay_setup_then_prompt_runs_the_turn(client, voice_on, fake_turn):
    with client.websocket_connect("/voice/relay") as ws:
        ws.send_json({
            "type": "setup", "callSid": "CA1", "from": "+971501234567",
            "to": "+97144000000", "customParameters": {"business_id": "bright-smile"},
        })
        ws.send_json({"type": "prompt", "voicePrompt": "مرحبا، عندكم موعد اليوم؟", "last": True})
        reply = ws.receive_json()

    assert reply["type"] == "text" and reply["last"] is True
    assert reply["token"] == "أهلاً! كيف أقدر أساعدك؟"
    # The caller's number IS the conversation (call-<e164>), same memory as WA/web.
    assert fake_turn == [("bright-smile", "call-971501234567", "مرحبا، عندكم موعد اليوم؟")]


def test_relay_unknown_business_ends_the_call(client, voice_on, fake_turn):
    with client.websocket_connect("/voice/relay") as ws:
        ws.send_json({
            "type": "setup", "from": "+971501234567",
            "customParameters": {"business_id": "ghost-biz"},
        })
        end = ws.receive_json()
    assert end["type"] == "end"
    assert fake_turn == []  # the brain is never invoked for an unknown tenant


def test_relay_paused_thread_gets_a_holding_line(client, voice_on, monkeypatch):
    """When a human has taken the thread over, run_turn returns '' — on a live
    call we can't go silent, so the caller hears a brief holding line."""
    async def _paused(business_id, conversation_id, message, schedule):
        return ""

    monkeypatch.setattr(chat_core, "run_turn", _paused)
    with client.websocket_connect("/voice/relay") as ws:
        ws.send_json({
            "type": "setup", "from": "+971501234567",
            "customParameters": {"business_id": "bright-smile"},
        })
        ws.send_json({"type": "prompt", "voicePrompt": "hello?"})
        reply = ws.receive_json()
    assert reply["type"] == "text" and "team" in reply["token"].lower()


def test_relay_blank_and_unknown_events_are_ignored(client, voice_on, fake_turn):
    """A blank transcript and an interrupt/dtmf event don't crash or reply."""
    with client.websocket_connect("/voice/relay") as ws:
        ws.send_json({
            "type": "setup", "from": "+971501234567",
            "customParameters": {"business_id": "bright-smile"},
        })
        ws.send_json({"type": "interrupt", "utteranceUntilInterrupt": "hel"})
        ws.send_json({"type": "prompt", "voicePrompt": "   "})   # blank → skipped
        ws.send_json({"type": "prompt", "voicePrompt": "real question"})
        reply = ws.receive_json()
    # Only the real prompt produced a spoken reply.
    assert reply["token"] == "أهلاً! كيف أقدر أساعدك؟"
    assert len(fake_turn) == 1 and fake_turn[0][2] == "real question"
