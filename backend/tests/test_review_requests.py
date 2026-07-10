"""Post-visit Google review requests: after an appointment, one warm message
asks the client for a Google review — timed per vertical (salon soon, clinic
next day), sent once per booking, only when the business set a review link, and
never to an opted-out client. The clock is frozen so the wall time can't flake
the 'has the visit settled yet?' math."""

import datetime
import zoneinfo

import pytest

from app import db, review_service, whatsapp
from app.config import get_settings

BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}   # vertical: clinic (24h wait)
VELVET = {"X-API-Key": "bizkey_velvet_hair_demo"}    # vertical: salon  (2h wait)
ADMIN = {"X-API-Key": "admin_test_key"}

_DUBAI = zoneinfo.ZoneInfo("Asia/Dubai")
# A fixed "now" all the tests reason against.
NOW = datetime.datetime(2026, 7, 10, 18, 0, tzinfo=_DUBAI)
TODAY = "2026-07-10"


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(review_service, "_now", lambda: NOW)


@pytest.fixture
def wa(monkeypatch):
    """Fake the Graph API send + turn the channel on; records what went out."""
    sent = []

    async def _fake_send(phone_id, to, text):
        sent.append((phone_id, to, text))

    monkeypatch.setattr(whatsapp, "_send_text", _fake_send)
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "token123")
    return sent


def _connect_wa(client, headers, phone_id="PID777"):
    """Give a business a WhatsApp number so review requests can actually deliver."""
    assert client.post(
        "/manage/velvet-hair" if headers is VELVET else "/manage/bright-smile",
        headers=headers, json={"whatsapp_phone_id": phone_id},
    ).status_code == 200


def _set_review_link(client, headers, url="https://g.page/r/velvet/review"):
    assert client.post(
        "/manage/velvet-hair" if headers is VELVET else "/manage/bright-smile",
        headers=headers, json={"google_review_url": url},
    ).status_code == 200


def test_salon_client_is_asked_after_the_visit_settles(client, frozen, wa):
    _connect_wa(client, VELVET)
    _set_review_link(client, VELVET)
    # Visit was 3h ago (15:00 today) — past the salon's 2h settle window.
    db.save_booking("velvet-hair", TODAY, "3:00 PM", "Lina Said", phone="0501234567", reason="color")

    assert review_service.send_due_review_requests() == 1
    assert len(wa) == 1
    phone_id, to, text = wa[0]
    assert phone_id == "PID777" and to == "971501234567"
    assert "g.page/r/velvet/review" in text and "Lina" in text

    # Idempotent: a second sweep asks no one again (send-once claim).
    assert review_service.send_due_review_requests() == 0


def test_not_asked_before_the_settle_window(client, frozen, wa):
    _connect_wa(client, VELVET)
    _set_review_link(client, VELVET)
    # Only 1h ago (17:00) — under the salon's 2h wait.
    db.save_booking("velvet-hair", TODAY, "5:00 PM", "Omar N", phone="0501112222", reason="cut")

    assert review_service.send_due_review_requests() == 0
    assert wa == []


def test_clinic_waits_a_day(client, frozen, wa):
    _connect_wa(client, BRIGHT)
    _set_review_link(client, BRIGHT, url="https://g.page/r/bright/review")
    # 3h ago is too soon for a clinic (24h wait) — nothing yet.
    db.save_booking("bright-smile", TODAY, "3:00 PM", "Sara Ali", phone="0509990000", reason="cleaning")
    assert review_service.send_due_review_requests() == 0
    assert wa == []

    # A visit ~25h ago (yesterday 5 PM) IS past the clinic window.
    db.save_booking("bright-smile", "2026-07-09", "5:00 PM", "Ravi P", phone="0508887777", reason="checkup")
    assert review_service.send_due_review_requests() == 1
    assert wa[0][2].count("g.page/r/bright/review") == 1


def test_no_link_means_no_claim_so_it_can_send_later(client, frozen, wa):
    """A business without a review link is skipped WITHOUT burning the once-only
    claim — so the client still gets asked once the owner pastes their link."""
    _connect_wa(client, VELVET)
    db.save_booking("velvet-hair", TODAY, "3:00 PM", "Dana K", phone="0501234567", reason="color")

    # No link yet → nothing sent, nothing claimed.
    assert review_service.send_due_review_requests() == 0
    assert wa == []

    # Owner adds the link later → the same past visit is now asked.
    _set_review_link(client, VELVET)
    assert review_service.send_due_review_requests() == 1
    assert len(wa) == 1


def test_cancelled_future_and_opted_out_are_skipped(client, frozen, wa):
    _connect_wa(client, VELVET)
    _set_review_link(client, VELVET)
    # Cancelled visit — never ask.
    db.save_booking("velvet-hair", TODAY, "1:00 PM", "Cx One", phone="0501111111", reason="cut")
    db.set_booking_status("velvet-hair", "Cx One", TODAY, "1:00 PM", "cancelled")
    # Future visit (8 PM today, 2h ahead of NOW) — hasn't happened.
    db.save_booking("velvet-hair", TODAY, "8:00 PM", "Cx Two", phone="0502222222", reason="cut")
    # Settled visit but the client opted out (PDPL do-not-contact).
    db.save_booking("velvet-hair", TODAY, "3:00 PM", "Cx Three", phone="0503333333", reason="cut")
    db.set_opt_out("velvet-hair", "0503333333")

    assert review_service.send_due_review_requests() == 0
    assert wa == []


def test_admin_endpoint_runs_the_sweep(client, frozen, wa):
    _connect_wa(client, VELVET)
    _set_review_link(client, VELVET)
    db.save_booking("velvet-hair", TODAY, "3:00 PM", "Nour A", phone="0504445555", reason="color")

    # Non-admin (a business key) can't run it.
    assert client.post("/admin/send-review-requests", headers=VELVET).status_code == 401
    assert client.post("/admin/send-review-requests").status_code == 401
    # Admin runs it and gets the count.
    r = client.post("/admin/send-review-requests", headers=ADMIN)
    assert r.status_code == 200 and r.json()["sent"] == 1


def test_settings_round_trips_the_review_link(client):
    assert client.post(
        "/manage/bright-smile", headers=BRIGHT,
        json={"google_review_url": "https://g.page/r/bright/review"},
    ).status_code == 200
    got = client.get("/manage/bright-smile", headers=BRIGHT).json()
    assert got["google_review_url"] == "https://g.page/r/bright/review"
