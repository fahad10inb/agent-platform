"""The WhatsApp channel: webhook handshake, payload parsing, tenant routing,
and the reply path — all without ever touching Meta."""

import asyncio
import hashlib
import hmac
import json

from app import chat_core, whatsapp
from app.config import get_settings


def _sample_payload(phone_id="111222333", sender="971501234567", text="hi, do you have a 2BR?"):
    """The shape Meta actually POSTs (trimmed to the fields that matter)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_ID",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550001111", "phone_number_id": phone_id},
                    "contacts": [{"profile": {"name": "Rashid"}, "wa_id": sender}],
                    "messages": [{
                        "from": sender, "id": "wamid.X", "timestamp": "1700000000",
                        "type": "text", "text": {"body": text},
                    }],
                },
            }],
        }],
    }


def test_webhook_plays_dead_when_unconfigured(client):
    assert client.get("/whatsapp/webhook?hub.mode=subscribe").status_code == 404
    assert client.post("/whatsapp/webhook", json={}).status_code == 404


def test_verify_handshake_echoes_the_challenge(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "whatsapp_verify_token", "sesame")
    r = client.get(
        "/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=sesame&hub.challenge=42abc"
    )
    assert r.status_code == 200
    assert r.text == "42abc"
    # The wrong token is turned away.
    r = client.get("/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=WRONG&hub.challenge=x")
    assert r.status_code == 403


def test_inbound_parser_takes_texts_and_skips_receipts():
    events = whatsapp._inbound_messages(_sample_payload())
    assert events == [("111222333", "971501234567", "hi, do you have a 2BR?")]
    # A delivery-receipt payload (statuses, no messages) yields nothing.
    receipt = {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "111222333"},
        "statuses": [{"id": "wamid.X", "status": "delivered"}],
    }}]}]}
    assert whatsapp._inbound_messages(receipt) == []
    # Non-text messages (an image) fall through in v1.
    img = _sample_payload()
    img["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": "971501234567", "type": "image", "image": {"id": "MEDIA_ID"},
    }
    assert whatsapp._inbound_messages(img) == []


def test_webhook_accepts_and_acks_fast(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_access_token", "token123")
    monkeypatch.setattr(settings, "whatsapp_app_secret", "shhh")
    body = json.dumps(_sample_payload()).encode()
    sig = "sha256=" + hmac.new(b"shhh", body, hashlib.sha256).hexdigest()
    r = client.post("/whatsapp/webhook", content=body,
                    headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
    assert r.status_code == 200
    assert r.json() == {"status": "received"}


def test_webhook_rejects_bad_signatures_when_secret_set(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "whatsapp_access_token", "token123")
    monkeypatch.setattr(settings, "whatsapp_app_secret", "shhh")
    body = json.dumps(_sample_payload()).encode()
    good = "sha256=" + hmac.new(b"shhh", body, hashlib.sha256).hexdigest()
    r = client.post("/whatsapp/webhook", content=body,
                    headers={"X-Hub-Signature-256": good, "Content-Type": "application/json"})
    assert r.status_code == 200
    r = client.post("/whatsapp/webhook", content=body,
                    headers={"X-Hub-Signature-256": "sha256=forged", "Content-Type": "application/json"})
    assert r.status_code == 403


def test_handle_message_runs_a_turn_and_replies(client, monkeypatch):
    """The full inbound→core→outbound path, with the core and Graph API faked."""
    turns, sent = [], []

    async def _fake_turn(business_id, conversation_id, message, schedule):
        turns.append((business_id, conversation_id, message))
        return "We have two 2BR options in JVC!"

    async def _fake_send(phone_id, to, text):
        sent.append((phone_id, to, text))

    monkeypatch.setattr(chat_core, "run_turn", _fake_turn)
    monkeypatch.setattr(whatsapp, "_send_text", _fake_send)

    asyncio.run(whatsapp._handle_message("skyline-realty", "111222333", "971501234567", "any 2BR?"))

    # The customer's own number IS the conversation — memory rides on it.
    assert turns == [("skyline-realty", "wa-971501234567", "any 2BR?")]
    assert sent == [("111222333", "971501234567", "We have two 2BR options in JVC!")]


def test_handle_message_never_raises(client, monkeypatch):
    """Meta retries webhooks that error — a bad turn must die quietly."""

    async def _boom(*a, **k):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(chat_core, "run_turn", _boom)
    asyncio.run(whatsapp._handle_message("skyline-realty", "111", "9715", "hi"))  # no raise
