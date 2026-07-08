"""Lead nurture cadence: the due-stage logic, the send-once sweep, skipping
converted (booked) leads, and the admin trigger."""

import datetime
import zoneinfo

import pytest

from app import db, nurture_service, whatsapp
from app.config import get_settings

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
_TZ = zoneinfo.ZoneInfo("Asia/Dubai")
_NOW = datetime.datetime(2026, 7, 8, 10, 0, tzinfo=_TZ)


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(nurture_service, "_now", lambda: _NOW)


def _lead(days_old, business_id="skyline-realty", name="Sam", phone="0501234567"):
    return {"business_id": business_id, "name": name, "phone": phone, "interest": "2BR",
            "created_at": _NOW - datetime.timedelta(days=days_old)}


def _wire(monkeypatch):
    sent = []

    async def _fake_send(phone_id, to, text):
        sent.append((to, text))

    monkeypatch.setattr(whatsapp, "_send_text", _fake_send)
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "token123")
    db.update_business_settings("skyline-realty", {"whatsapp_phone_id": "PID-RE"})
    return sent


# ── cadence logic ────────────────────────────────────────────────────────────
def test_due_stage_picks_the_most_advanced_passed():
    assert nurture_service._due_stage(0.5) is None   # too fresh
    assert nurture_service._due_stage(3) == "day2"
    assert nurture_service._due_stage(8) == "day7"
    assert nurture_service._due_stage(40) == "day30"  # old lead → only the last touch


def test_copy_is_warm_and_never_discount_baits():
    text = nurture_service.compose_nurture({"name": "Skyline"}, {"name": "Sam Ali"}, "day2")
    assert "Sam" in text and "Skyline" in text  # greets the lead, names the business
    low = nurture_service.compose_nurture({"name": "Skyline"}, {"name": "Sam Ali"}, "day30").lower()
    assert "discount" not in low and "%" not in low and "off" not in low.split()


# ── the sweep ────────────────────────────────────────────────────────────────
def test_sweep_sends_the_due_touch_once(client, frozen, monkeypatch):
    sent = _wire(monkeypatch)
    monkeypatch.setattr(db, "leads_for_nurture", lambda within_days=45: [_lead(7)])  # day7 due
    assert nurture_service.send_due_nurtures() == 1
    assert len(sent) == 1 and sent[0][0] == "971501234567"
    # A second sweep at the same age must NOT message again (same stage claimed).
    assert nurture_service.send_due_nurtures() == 0
    assert len(sent) == 1


def test_sweep_advances_stages_as_the_lead_ages(client, frozen, monkeypatch):
    sent = _wire(monkeypatch)
    monkeypatch.setattr(db, "leads_for_nurture", lambda within_days=45: [_lead(3)])
    nurture_service.send_due_nurtures()  # day2
    # The same lead, now 8 days old → day7 becomes due (a different stage).
    monkeypatch.setattr(db, "leads_for_nurture", lambda within_days=45: [_lead(8)])
    assert nurture_service.send_due_nurtures() == 1
    assert len(sent) == 2


def test_a_booked_lead_is_not_nurtured(client, frozen, monkeypatch):
    sent = _wire(monkeypatch)
    monkeypatch.setattr(db, "leads_for_nurture", lambda within_days=45: [_lead(7)])
    # The lead converted — a booking exists for that phone.
    db.save_booking("skyline-realty", "2026-07-20", "5:00 PM", "Sam", "0501234567", "viewing")
    assert nurture_service.send_due_nurtures() == 0
    assert sent == []


def test_fresh_lead_gets_nothing(client, frozen, monkeypatch):
    _wire(monkeypatch)
    monkeypatch.setattr(db, "leads_for_nurture", lambda within_days=45: [_lead(0.2)])
    assert nurture_service.send_due_nurtures() == 0


# ── the admin trigger ────────────────────────────────────────────────────────
def test_admin_send_nurtures_is_admin_only(client):
    assert client.post("/admin/send-nurtures").status_code == 401
    assert client.post("/admin/send-nurtures", headers=BRIGHT).status_code == 401
    assert client.post("/admin/send-nurtures", headers=ADMIN).status_code == 200
