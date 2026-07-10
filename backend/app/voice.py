"""
Inbound voice channel — a thin adapter between Twilio ConversationRelay and the
SAME chat brain the widget and WhatsApp use (chat_core.run_turn).

Flow (Arabic-first, after-hours pilot): the business's e&/du line is forwarded
to a Twilio number whose Voice webhook points at POST /voice/incoming. We answer
with TwiML that opens a <ConversationRelay> — Twilio then does ALL the hard
real-time audio (Arabic STT via Deepgram, TTS via ElevenLabs, barge-in, μ-law
transport) and connects a WebSocket to /voice/relay. On each final transcript we
pump the text through run_turn (persona, booking, memory, lead capture, handoff
all execute inside it exactly as in chat) and stream the reply back as text for
Twilio to speak. The caller's number IS the conversation id, so voice shares the
same caller memory as their WhatsApp/web threads.

Status: SCAFFOLD. Plays dead (404 / immediate close) unless settings.voice_enabled
is true. The message shapes below follow Twilio's documented ConversationRelay
protocol, but this has NOT been exercised against a live call — finishing the
channel needs a Twilio number/relay + Deepgram + ElevenLabs and a real call to
verify audio, latency and Gulf-Arabic quality. See VOICE-PLAN-2026-07.md.
"""

import base64
import hashlib
import hmac
import logging
import urllib.parse

from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect

from app import chat_core, db
from app.config import get_settings
from app.phone import to_wa_number as _to_wa_number
from app.whatsapp import _schedule_background  # same async defer hook as the webhook

logger = logging.getLogger("agent-platform.voice")

router = APIRouter()


def _xml_escape(s: str) -> str:
    """Escape a value for inclusion in a TwiML attribute."""
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _greeting(business: dict) -> str:
    """The line ConversationRelay speaks (via TTS) before the first turn.
    Arabic-first with an English tail — the caller replies in either and the
    brain mirrors them from there. Tunable per business later."""
    name = business.get("name") or "our team"
    return (
        f"مرحباً، لقد وصلت إلى {name}. كيف يمكنني مساعدتك اليوم؟ "
        f"Hello, you've reached {name} — how can I help?"
    )


def build_incoming_twiml(business: dict, relay_url: str) -> str:
    """The TwiML that hands the call to ConversationRelay. business_id rides
    along as a <Parameter> so the relay's `setup` message can resolve the tenant.
    STT/TTS providers + language come from settings (env-tunable for the pilot)."""
    s = get_settings()
    greeting = _xml_escape(_greeting(business))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect>"
        f'<ConversationRelay url="{_xml_escape(relay_url)}"'
        f' transcriptionProvider="{_xml_escape(s.voice_stt_provider)}"'
        f' ttsProvider="{_xml_escape(s.voice_tts_provider)}"'
        f' language="{_xml_escape(s.voice_language)}"'
        f' ttsLanguage="{_xml_escape(s.voice_language)}"'
        f' interruptible="any" welcomeGreeting="{greeting}">'
        f'<Parameter name="business_id" value="{_xml_escape(business["id"])}"/>'
        "</ConversationRelay>"
        "</Connect></Response>"
    )


def _twilio_signature(auth_token: str, url: str, params: dict) -> str:
    """Twilio's request signature: base64(HMAC-SHA1(token, url + sorted k+v)).
    Used to prove a webhook really came from Twilio."""
    data = url + "".join(k + str(params[k]) for k in sorted(params))
    digest = hmac.new(auth_token.encode(), data.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


@router.post("/voice/incoming")
async def voice_incoming(request: Request):
    """Twilio hits this when a forwarded call lands. Answer with ConversationRelay
    TwiML for the resolved business. The tenant is chosen by ?business_id= on the
    webhook URL (each client configures their own number's webhook), so no shared
    number-to-tenant table is needed for the pilot. 404 when the channel is off or
    the business is unknown (an unknown id answers identically — no enumeration)."""
    settings = get_settings()
    if not settings.voice_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    # Twilio POSTs application/x-www-form-urlencoded — parse the raw body
    # ourselves (no python-multipart dependency; we only need it to sign).
    raw = await request.body()
    form = dict(urllib.parse.parse_qsl(raw.decode("utf-8"))) if raw else {}
    # Verify the call really came from Twilio when an auth token is configured.
    # (Fail-open with no token = dev only; set TWILIO_AUTH_TOKEN in production.
    # NOTE: behind Render's TLS proxy, sign against the external https URL — the
    # X-Forwarded-Proto caveat to confirm on the first live call.)
    if settings.twilio_auth_token:
        expected = _twilio_signature(settings.twilio_auth_token, str(request.url), form)
        given = request.headers.get("X-Twilio-Signature", "")
        if not hmac.compare_digest(expected, given):
            logger.warning("voice webhook rejected: bad Twilio signature")
            raise HTTPException(status_code=403, detail="Bad signature.")

    business_id = request.query_params.get("business_id", "")
    business = db.get_business(business_id) if business_id else None
    if business is None:
        raise HTTPException(status_code=404, detail="Not found")

    relay_url = f"wss://{request.url.hostname}/voice/relay"
    return Response(content=build_incoming_twiml(business, relay_url), media_type="application/xml")


async def _speak(ws: WebSocket, text: str) -> None:
    """Send one reply for ConversationRelay to speak (a single final token)."""
    await ws.send_json({"type": "text", "token": text, "last": True})


@router.websocket("/voice/relay")
async def voice_relay(ws: WebSocket):
    """The ConversationRelay socket. `setup` gives us the tenant + caller; each
    `prompt` is a final transcript we answer via run_turn; `interrupt`/`dtmf` are
    logged. Best-effort — any error is logged and the socket closed, never raised
    (a dropped call must not surface a stack trace)."""
    await ws.accept()
    if not get_settings().voice_enabled:
        await ws.close(code=1008)
        return

    business_id = ""
    conversation_id = ""
    try:
        while True:
            try:
                msg = await ws.receive_json()
            except WebSocketDisconnect:
                break
            kind = msg.get("type")

            if kind == "setup":
                params = msg.get("customParameters") or {}
                business_id = params.get("business_id") or ""
                caller = _to_wa_number(msg.get("from") or "") or "unknown"
                # The caller's number IS the conversation — same memory as their
                # WhatsApp/web threads (call- keeps voice turns visibly distinct).
                conversation_id = f"call-{caller}"
                if db.get_business(business_id) is None:
                    logger.warning("voice setup for unknown business=%s — ending", business_id)
                    await ws.send_json({"type": "end"})
                    break

            elif kind == "prompt":
                text = (msg.get("voicePrompt") or "").strip()
                if not text or not business_id:
                    continue
                try:
                    reply = await chat_core.run_turn(
                        business_id, conversation_id, text, _schedule_background
                    )
                except Exception:  # noqa: BLE001 — speak a graceful line, keep the call up
                    logger.exception("voice turn failed for business=%s", business_id)
                    reply = "Sorry, I didn't catch that — could you say it again?"
                # Empty = a human took this thread over from the inbox; on a live
                # call we can't stay silent, so give a brief holding line.
                if not (reply and reply.strip()):
                    reply = "One moment — I'm connecting you with the team."
                await _speak(ws, reply)

            elif kind in ("interrupt", "dtmf", "error"):
                # Barge-in / keypad / provider error — logged for the pilot; CR
                # already handles the audio side of an interrupt on its own.
                logger.info("voice %s event on business=%s", kind, business_id)
    except Exception:  # noqa: BLE001 — never let the relay loop raise
        logger.exception("voice relay loop failed for business=%s", business_id)
    finally:
        try:
            await ws.close()
        except Exception:  # noqa: BLE001 — already closed / disconnected
            pass
