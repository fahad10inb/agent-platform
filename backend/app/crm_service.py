"""
CRM write-back — push a qualified, scored lead into the agency's own CRM.

Fire-and-forget on a daemon thread (never blocks or breaks the conversation),
graceful when unconfigured (logs, like owner notifications without a Resend key).
The integration surface is deliberately a single URL the agency gives us:
  - crm_type 'bitrix24' → the base inbound-webhook URL; we call crm.lead.add on it
    (Bitrix24 inbound webhooks are just a URL, the easiest real CRM to write to).
  - anything else (Zapier/Make/custom) → we POST the lead JSON straight to the URL.
This keeps a small agency's setup to "paste one webhook URL", no OAuth.
"""

import json
import logging
import threading
import urllib.request

from app import db

logger = logging.getLogger("agent-platform.crm")


def push_lead(business: dict, lead: dict) -> None:
    """Send a qualified lead to the business's CRM webhook, if it set one. Never
    raises — a CRM being down must not affect the caller's conversation."""
    url = (business.get("crm_webhook_url") or "").strip()
    if not url:
        logger.info("[crm] no webhook for business=%s — lead not pushed", business.get("id"))
        return
    crm_type = (business.get("crm_type") or "").strip().lower()
    threading.Thread(target=_deliver, args=(url, crm_type, lead), daemon=True).start()


def _payload(crm_type: str, url: str, lead: dict) -> tuple[str, bytes]:
    """(target_url, json body) for the CRM. Bitrix24 gets crm.lead.add-shaped
    fields; everyone else gets the raw lead."""
    if crm_type == "bitrix24":
        target = url.rstrip("/") + "/crm.lead.add.json"
        title = f"{lead.get('name') or 'Lead'} — {lead.get('score') or ''} ({lead.get('source') or 'AI'})"
        body = {
            "fields": {
                "TITLE": title.strip(" —"),
                "NAME": lead.get("name") or "",
                "PHONE": [{"VALUE": lead.get("phone") or "", "VALUE_TYPE": "MOBILE"}],
                "COMMENTS": lead.get("summary") or "",
                "SOURCE_DESCRIPTION": lead.get("source") or "AI receptionist",
            }
        }
        return target, json.dumps(body).encode()
    return url, json.dumps(lead).encode()


def _deliver(url: str, crm_type: str, lead: dict) -> None:
    target, body = _payload(crm_type, url, lead)
    try:
        req = urllib.request.Request(
            target, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read(2000)
        logger.info("[crm] pushed %s lead to %s CRM", lead.get("score"), crm_type or "generic")
    except Exception as exc:  # noqa: BLE001 — best-effort, log and move on
        logger.warning("[crm] push failed (%s): %s", crm_type or "generic", str(exc)[:200])


def push_lead_now(business_id: str, lead: dict) -> None:
    """Same as push_lead but looks the business up first — the seam tests patch."""
    business = db.get_business(business_id)
    if business:
        push_lead(business, lead)
