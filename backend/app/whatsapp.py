"""
WhatsApp channel — a thin adapter between Meta's Cloud API webhooks and the
same chat core the web widget uses.

Flow: a customer WhatsApps the business's number → Meta POSTs us the message →
we look up which tenant owns that number (businesses.whatsapp_phone_id) → the
shared chat core produces the reply → we POST it back through the Graph API.
The conversation_id is the customer's own WhatsApp number, so memory and
history work exactly like the widget — and better: the number IS the identity.

Setup (one time, ~15 min, no business verification needed for the TEST number):
  1. developers.facebook.com → create app (type: Business) → add WhatsApp.
  2. The app gives you a FREE test number + temp access token + its
     phone_number_id (test numbers can message up to 5 opted-in recipients).
  3. On Render set WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN (any string
     you invent), and optionally WHATSAPP_APP_SECRET (the app's App Secret).
  4. In the app's WhatsApp → Configuration, set the webhook URL to
     https://<host>/whatsapp/webhook with your verify token; subscribe to
     the "messages" field.
  5. Point the number at a tenant: POST /manage/{id} with
     {"whatsapp_phone_id": "<phone_number_id>"}.
"""

import asyncio
import hashlib
import hmac
import logging
import time

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app import chat_core, db
from app.config import get_settings

logger = logging.getLogger("agent-platform.whatsapp")

router = APIRouter()

_GRAPH_URL = "https://graph.facebook.com/v20.0"

# Meta redelivers a webhook when our ACK is slow or errors, and occasionally
# duplicates even after a 200 — so the same message id (wamid) can arrive twice.
# Without dedup that means two full Gemini turns, two replies to the customer,
# and double tool execution. A short-TTL seen-set makes processing idempotent.
# Single instance only (in-process); a redeliver after a deploy is dropped, not
# double-run — acceptable for a best-effort channel.
_SEEN_WAMIDS: dict[str, float] = {}
_WAMID_TTL_SECONDS = 3600


def _already_processed(wamid: str) -> bool:
    """True if this wamid was seen recently; records it and prunes stale ids."""
    now = time.monotonic()
    if _SEEN_WAMIDS:
        for k, seen_at in list(_SEEN_WAMIDS.items()):
            if now - seen_at > _WAMID_TTL_SECONDS:
                del _SEEN_WAMIDS[k]
    if wamid in _SEEN_WAMIDS:
        return True
    _SEEN_WAMIDS[wamid] = now
    return False


@router.get("/whatsapp/webhook")
def verify_webhook(request: Request):
    """Meta's one-time subscription handshake: echo hub.challenge back if the
    verify token matches. 404 when the channel isn't configured at all."""
    settings = get_settings()
    if not settings.whatsapp_verify_token:
        raise HTTPException(status_code=404, detail="Not found")
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.whatsapp_verify_token
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed.")


@router.post("/whatsapp/webhook")
async def receive_webhook(request: Request):
    """Inbound WhatsApp traffic. Always answer 200 FAST (Meta retries slow or
    failing webhooks aggressively) and do the model work in a background task."""
    settings = get_settings()
    if not settings.whatsapp_access_token:
        raise HTTPException(status_code=404, detail="Not found")

    raw = await request.body()
    # Signature verification (fail closed): a live channel with no app secret
    # would accept ANY forged POST — an attacker who learns the phone_number_id
    # could inject fake customer messages (burning Gemini tokens, poisoning
    # caller memory, relaying through the tenant's number). WHATSAPP_SKIP_SIGNATURE
    # is a DEBUG escape hatch (default off) for isolating a mis-pasted app secret
    # during setup — turn it back off once the secret is confirmed correct.
    if settings.whatsapp_skip_signature:
        logger.warning("WHATSAPP_SKIP_SIGNATURE is ON — signature check bypassed (debug only)")
    else:
        if not settings.whatsapp_app_secret:
            logger.error("WHATSAPP_APP_SECRET is not set — refusing unsigned webhook traffic")
            raise HTTPException(status_code=503, detail="WhatsApp channel misconfigured.")
        expected = (
            "sha256="
            + hmac.new(settings.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
        )
        given = request.headers.get("X-Hub-Signature-256", "")
        if not hmac.compare_digest(expected, given):
            logger.warning("whatsapp webhook rejected: signature mismatch (check WHATSAPP_APP_SECRET)")
            raise HTTPException(status_code=403, detail="Bad signature.")

    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    for phone_id, sender, text, wamid in _inbound_messages(payload):
        if wamid and _already_processed(wamid):
            logger.info("skipping duplicate whatsapp delivery wamid=%s", wamid)
            continue
        business = db.get_business_by_whatsapp(phone_id)
        if business:
            asyncio.create_task(_handle_message(business["id"], phone_id, sender, text))
    return {"status": "received"}


def _inbound_messages(payload: dict) -> list[tuple[str, str, str, str]]:
    """(phone_number_id, sender, text, wamid) for each real customer text
    message in a webhook payload. Delivery receipts (value['statuses']) and
    non-text types (media/location — later) fall straight through."""
    out = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            phone_id = (value.get("metadata") or {}).get("phone_number_id", "")
            for msg in value.get("messages", []) or []:
                sender = msg.get("from", "")
                text = ((msg.get("text") or {}).get("body") or "").strip()
                if msg.get("type") == "text" and phone_id and sender and text:
                    out.append((phone_id, sender, text, msg.get("id", "")))
    return out


async def _handle_message(business_id: str, phone_id: str, sender: str, text: str) -> None:
    """One customer message → one reply, off the webhook's clock. Best-effort:
    a failure is logged, never re-raised (Meta would just retry the webhook)."""
    try:
        reply = await chat_core.run_turn(
            business_id,
            f"wa-{sender}",  # the customer's number IS the conversation
            text,
            _schedule_background,
        )
        # Empty = a human took this thread over (run_turn stayed silent) — send
        # nothing; the owner replies from the inbox. Otherwise deliver the AI's reply.
        if reply and reply.strip():
            await _send_text(phone_id, sender, reply)
    except Exception:
        logger.exception("whatsapp turn failed for business=%s", business_id)


def _schedule_background(fn, *args) -> None:
    """chat_core's deferred-work hook, webhook flavor: fire an asyncio task
    (the web route uses FastAPI BackgroundTasks instead). Handles both async
    work (the distiller) and plain functions, like BackgroundTasks does."""
    if asyncio.iscoroutinefunction(fn):
        asyncio.create_task(fn(*args))
    else:
        asyncio.create_task(asyncio.to_thread(fn, *args))


async def _send_text(phone_id: str, to: str, text: str) -> None:
    """Deliver one reply through the Graph API."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{_GRAPH_URL}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                # WhatsApp caps text messages at 4096 chars; our replies are
                # short by prompt design, but never let an outlier bounce.
                "text": {"body": text[:4000]},
            },
        )
    if r.status_code >= 400:
        logger.error("whatsapp send failed (%s): %s", r.status_code, r.text[:300])


# ── business-initiated messages (templates) ──────────────────────────────────
# A REPLY (inside 24h of the customer's message) can be free-form text — that's
# _send_text above. A message the business STARTS (reminder / nurture / review /
# outreach) can only be delivered outside that window as an APPROVED TEMPLATE;
# free-form is rejected (131047). send_business_message routes to a template when
# one is configured for that message kind, else falls back to free-form text.

_TEMPLATE_SETTING = {
    "reminder": "whatsapp_template_reminder",
    "nurture": "whatsapp_template_nurture",
    "review": "whatsapp_template_review",
    "outreach": "whatsapp_template_outreach",
    "match": "whatsapp_template_match",
}


def _template_payload(to: str, name: str, lang: str, params: list) -> dict:
    """The Graph API body for a template send. Pure (no I/O) so it's unit-testable.
    `params` fill the body variables {{1}}, {{2}}, … in order."""
    body = [{"type": "text", "text": str(p)[:1000]} for p in (params or [])]
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {"name": name, "language": {"code": lang or "en_US"}},
    }
    if body:
        payload["template"]["components"] = [{"type": "body", "parameters": body}]
    return payload


async def _send_template(phone_id: str, to: str, name: str, lang: str, params: list) -> bool:
    """Deliver a pre-approved template — the only message type allowed outside the
    24h window. Returns True on success (a 2xx from Graph)."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{_GRAPH_URL}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json=_template_payload(to, name, lang, params),
        )
    if r.status_code >= 400:
        logger.error("whatsapp template send failed (%s): %s", r.status_code, r.text[:300])
    return r.status_code < 400


async def send_business_message(
    phone_id: str, to: str, *, kind: str, params: list, fallback_text: str
) -> bool:
    """Send a message the business INITIATED. If an approved template is configured
    for this `kind` (reminder/nurture/review/outreach), send the template (required
    outside 24h); otherwise send free-form text — correct within 24h / on the test
    number, and the current behaviour, so nothing changes until a template is set."""
    settings = get_settings()
    name = getattr(settings, _TEMPLATE_SETTING.get(kind, ""), "") if kind in _TEMPLATE_SETTING else ""
    if name:
        return await _send_template(phone_id, to, name, settings.whatsapp_template_lang, params)
    await _send_text(phone_id, to, fallback_text)
    return True
