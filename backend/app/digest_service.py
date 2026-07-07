"""Weekly owner ROI digest — churn defense, straight from the research: owners
cancel when the value is invisible, and "353 calls last month that would have
gone unanswered" is the single most persuasive retention line in the market.
Once a week (Monday morning, Dubai time) every owner with an alert email gets
a short money-framed summary of what their receptionist did.

Design mirrors notify_service's discipline:
  • best-effort — send_weekly_digests never raises, one broken tenant can't
    block the rest of the loop;
  • idempotent — last_digest_at + a 6-day rule means the hourly scheduler can
    re-check all Monday morning without ever double-sending;
  • quiet weeks are skipped — "your receptionist did nothing" is churn fuel,
    not value proof.
"""

import datetime
import logging

from app import db, notify_service

logger = logging.getLogger("agent-platform.digest")

# Re-send only after this much silence. Six (not seven) days so a digest sent
# late Monday morning is comfortably due again by the NEXT Monday's window.
_RESEND_AFTER = datetime.timedelta(days=6)


def compose_digest(biz: dict, stats: dict) -> tuple[str, str]:
    """Turn one business's week into (subject, body).

    notify_owner prefixes "[<business name>]" onto every subject it delivers,
    so the subject here starts at the receptionist's week. Hours saved uses the
    same ~4-minutes-per-conversation figure as /metrics and is labeled an
    estimate — invented precision is exactly what the honest-metrics pledge bans.
    """
    convs = stats.get("conversations_7d", 0)
    msgs = stats.get("messages_7d", 0)
    bookings = stats.get("bookings_7d", 0)
    leads = stats.get("leads_7d", 0)
    hours_saved = round(convs * 4 / 60, 1)

    subject = f"Your receptionist's week: {convs} chats, {bookings} bookings"
    body = (
        f"Here's what your AI receptionist handled this week at {biz.get('name', 'your business')}:\n\n"
        f"  • Conversations with customers: {convs}\n"
        f"  • Questions answered: {msgs}\n"
        f"  • Appointments booked: {bookings}\n"
        f"  • Leads captured for follow-up: {leads}\n"
        f"  • Staff hours saved: ~{hours_saved} (an estimate — about 4 minutes of "
        "front-desk time per conversation)\n\n"
        "It never slept. See the details on your dashboard: open /dashboard and "
        "sign in with your business key."
    )
    return subject, body


def _digest_due(last_digest_at) -> bool:
    """True when a business has never had a digest, or its last one is stale.
    Postgres hands back tz-aware datetimes; a naive one (fakes, old rows) is
    treated as UTC rather than crashing the whole send loop."""
    if last_digest_at is None:
        return True
    if not isinstance(last_digest_at, datetime.datetime):
        return True  # unreadable stamp — better one extra email than none ever
    last = last_digest_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc) - last > _RESEND_AFTER


def send_weekly_digests() -> int:
    """Send the digest to every business that's due one; return how many went.

    Runs on a worker thread (the scheduler wraps it in asyncio.to_thread) and
    from the /admin/send-digests route. NEVER raises: per-business failures are
    logged and skipped, and even a broken business listing returns 0.
    """
    sent = 0
    try:
        businesses = db.list_businesses_full()
    except Exception as exc:  # noqa: BLE001 — background work must never propagate
        logger.warning("[digest] listing businesses failed: %s", str(exc)[:150])
        return 0
    for biz in businesses:
        try:
            if not (biz.get("notify_email") or "").strip():
                continue  # notifications off = digests off
            if not _digest_due(biz.get("last_digest_at")):
                continue  # already got this week's
            stats = db.get_week_stats(biz["id"])
            if stats.get("messages_7d", 0) < 1:
                continue  # a silent week is not a story worth an email
            subject, body = compose_digest(biz, stats)
            # notify_owner re-reads the business, adds the [name] prefix and
            # delivers on a daemon thread — the exact plumbing every other
            # owner email already uses, failures included (silent).
            notify_service.notify_owner(biz["id"], subject, body)
            db.set_last_digest(biz["id"])
            sent += 1
        except Exception as exc:  # noqa: BLE001 — one tenant must not sink the rest
            logger.warning("[digest] failed for business=%s: %s", biz.get("id"), str(exc)[:150])
    if sent:
        logger.info("[digest] sent %d weekly digests", sent)
    return sent
