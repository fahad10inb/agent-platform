"""Weekly owner ROI digest: money-framed composition, the send rules (no email
= silence, 6-day idempotency, quiet weeks skipped), and the admin trigger.
Delivery is captured with the same Thread monkeypatch as test_notify — the
digest rides notify_owner's existing plumbing, so the tests exercise it for real."""

import datetime

from app import db, digest_service, notify_service

ADMIN = {"X-API-Key": "admin_test_key"}
BIZ = "bright-smile"


def _capture(monkeypatch):
    """Swallow the delivery thread + record (to, subject, body) triples."""
    sent = []
    monkeypatch.setattr(
        notify_service.threading, "Thread",
        lambda target, args, daemon: type("T", (), {"start": lambda self: sent.append(args)})(),
    )
    return sent


def _busy_week(biz=BIZ, conv="digest-conv"):
    """Two caller messages in one thread — an engaged conversation, per the
    fair-billing rule — plus a booking and a lead, so every number is nonzero."""
    db.save_message(biz, conv, "user", "hi, do you have anything tomorrow?")
    db.save_message(biz, conv, "model", "we do!")
    db.save_message(biz, conv, "user", "book me in please")
    db.save_message(biz, conv, "model", "done")
    db.save_booking(biz, "2026-08-01", "9:00 AM", "Mariam", "0501234567", "cleaning")
    db.save_lead(biz, "Omar", "0501112233", "whitening quote")


# ── composition ───────────────────────────────────────────────────────────────
def test_digest_copy_carries_the_numbers_and_the_estimate(client):
    stats = {"conversations_7d": 12, "messages_7d": 47, "bookings_7d": 5, "leads_7d": 3}
    subject, body = digest_service.compose_digest({"id": BIZ, "name": "Bright Smile Dental"}, stats)
    assert subject == "Your receptionist's week: 12 chats, 5 bookings"
    assert "47" in body and "5" in body and "3" in body
    # Hours saved uses the /metrics formula (12 * 4 / 60 = 0.8) and SAYS it's
    # an estimate — invented precision would betray the honest-metrics pledge.
    assert "0.8" in body and "estimate" in body
    assert "It never slept." in body and "dashboard" in body


# ── send rules ────────────────────────────────────────────────────────────────
def test_digest_reaches_the_owner_and_stamps_the_date(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    state["businesses"][BIZ]["notify_email"] = "owner@clinic.com"
    _busy_week()
    assert digest_service.send_weekly_digests() == 1
    to, subject, body = sent[0]
    assert to == "owner@clinic.com"
    assert subject.startswith("[Bright Smile Dental]")  # notify_owner's prefix
    assert "1 chats, 1 bookings" in subject
    assert "Leads captured for follow-up: 1" in body
    assert state["businesses"][BIZ]["last_digest_at"] is not None


def test_no_notify_email_means_no_digest(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    _busy_week()  # busy — but nobody asked to be emailed
    assert digest_service.send_weekly_digests() == 0
    assert sent == []
    assert state["businesses"][BIZ].get("last_digest_at") is None


def test_six_day_rule_prevents_double_sends(client, state, monkeypatch):
    """The scheduler re-checks hourly all Monday morning; last_digest_at is the
    only thing standing between the owner and four copies of the same email."""
    sent = _capture(monkeypatch)
    state["businesses"][BIZ]["notify_email"] = "owner@clinic.com"
    _busy_week()
    now = datetime.datetime.now(datetime.timezone.utc)
    state["businesses"][BIZ]["last_digest_at"] = now - datetime.timedelta(days=2)
    assert digest_service.send_weekly_digests() == 0
    assert sent == []
    # ...but a stale stamp (older than 6 days) means it's due again.
    state["businesses"][BIZ]["last_digest_at"] = now - datetime.timedelta(days=7)
    assert digest_service.send_weekly_digests() == 1
    assert len(sent) == 1


def test_quiet_week_sends_nothing(client, state, monkeypatch):
    """'Your receptionist did nothing this week' is churn fuel, not value proof."""
    sent = _capture(monkeypatch)
    state["businesses"][BIZ]["notify_email"] = "owner@clinic.com"
    assert digest_service.send_weekly_digests() == 0
    assert sent == []
    assert state["businesses"][BIZ].get("last_digest_at") is None  # still due next week


def test_one_broken_tenant_never_blocks_the_rest(client, state, monkeypatch):
    """Best-effort like every background pass: a per-business exception is
    logged and skipped, and send_weekly_digests never raises."""
    sent = _capture(monkeypatch)
    state["businesses"][BIZ]["notify_email"] = "owner@clinic.com"
    state["businesses"]["velvet-hair"]["notify_email"] = "salon@owner.com"
    _busy_week(BIZ)
    _busy_week("velvet-hair", conv="salon-conv")

    real_stats = db.get_week_stats

    def _boom(business_id):
        if business_id == BIZ:
            raise RuntimeError("stats query died")
        return real_stats(business_id)

    monkeypatch.setattr(digest_service.db, "get_week_stats", _boom)
    assert digest_service.send_weekly_digests() == 1  # the salon still got its week
    assert sent and sent[0][0] == "salon@owner.com"


# ── the admin trigger ─────────────────────────────────────────────────────────
def test_admin_send_digests_requires_the_admin_key(client):
    assert client.post("/admin/send-digests").status_code == 401
    wrong = client.post("/admin/send-digests", headers={"X-API-Key": "bizkey_bright_smile_demo"})
    assert wrong.status_code == 401


def test_admin_send_digests_runs_the_pass_and_reports_the_count(client, state, monkeypatch):
    _capture(monkeypatch)
    state["businesses"][BIZ]["notify_email"] = "owner@clinic.com"
    _busy_week()
    r = client.post("/admin/send-digests", headers=ADMIN)
    assert r.status_code == 200
    assert r.json() == {"sent": 1}
    # Idempotent under the 6-day rule: an immediate second run sends nothing.
    assert client.post("/admin/send-digests", headers=ADMIN).json() == {"sent": 0}
