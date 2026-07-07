"""Owner notifications — the moment the platform starts FEELING alive to the
business owner. Every competitor surveyed (Smith.ai, Rosie, Goodcall) sends the
owner an email/SMS after every call or booking; until now our owner was blind
unless they opened the dashboard.

Design:
  • Per-business `notify_email` (set in Settings). Empty = notifications off.
  • Sent via Resend's HTTP API when RESEND_API_KEY is configured; otherwise the
    notification is logged (so local/dev behaves identically minus delivery).
  • Fired from inside the booking/lead TOOLS, which run synchronously on the
    event loop — so delivery happens on a daemon thread: the customer's reply
    is never delayed by an email API, and a failure can never break a booking.
"""

import json
import logging
import threading
import urllib.request

from app import db
from app.config import get_settings

logger = logging.getLogger("agent-platform.notify")


def _deliver(to_email: str, subject: str, body: str) -> None:
    """Blocking send (runs on a daemon thread). Resend if configured, log if not."""
    settings = get_settings()
    key = (getattr(settings, "resend_api_key", "") or "").strip()
    if not key:
        logger.info("[notify] (no RESEND_API_KEY - log only) to=%s subject=%s", to_email, subject)
        return
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps({
                "from": settings.notify_from,
                "to": [to_email],
                "subject": subject,
                "text": body,
            }).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("[notify] sent to=%s status=%s", to_email, resp.status)
    except Exception as exc:  # noqa: BLE001 — notification failure must stay silent
        logger.warning("[notify] send failed to=%s: %s", to_email, str(exc)[:150])


def notify_owner(business_id: str, subject: str, body: str) -> None:
    """Fire-and-forget notification to the business owner (if they set an email).

    Never blocks the caller, never raises — a booking must succeed identically
    whether or not the owner's inbox is reachable.
    """
    try:
        biz = db.get_business(business_id)
        to_email = ((biz or {}).get("notify_email") or "").strip()
        if not to_email:
            return
        name = (biz or {}).get("name") or business_id
        threading.Thread(
            target=_deliver,
            args=(to_email, f"[{name}] {subject}", body),
            daemon=True,
        ).start()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[notify] skipped: %s", str(exc)[:120])
