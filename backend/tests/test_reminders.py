"""Appointment reminders: the due-stage logic, UAE number normalization, the
send-once sweep, the confirm tool, and the admin trigger."""

import datetime
import zoneinfo

import pytest

from app import db, reminder_service, whatsapp
from app.config import get_settings
from app.tools.calendar_tools import make_calendar_tools

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
_FROZEN = datetime.datetime(2026, 7, 8, 10, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(reminder_service, "_now", lambda: _FROZEN)


# ── pure logic ───────────────────────────────────────────────────────────────
def test_due_stage_picks_the_nearest_threshold():
    assert reminder_service._due_stage(23) == "24h"
    assert reminder_service._due_stage(1.5) == "2h"   # nearer threshold wins
    assert reminder_service._due_stage(48) is None    # too far out — wait
    assert reminder_service._due_stage(0) is None      # already started
    assert reminder_service._due_stage(-3) is None     # in the past


def test_uae_number_normalizes_to_whatsapp_e164():
    assert reminder_service._to_wa_number("0501234567") == "971501234567"
    assert reminder_service._to_wa_number("+971 50 123 4567") == "971501234567"
    assert reminder_service._to_wa_number("00971501234567") == "971501234567"


def test_reminder_copy_names_the_business_service_and_when(frozen):
    # `frozen` pins now to 2026-07-08, so the 2026-07-09 booking really IS
    # "tomorrow" — without it this rots against the real clock.
    biz = {"name": "Bright Smile Dental"}
    booking = {"patient_name": "Sara Ali", "reason": "cleaning", "date": "2026-07-09", "time": "10:00 AM"}
    text = reminder_service.compose_reminder(biz, booking, "24h")
    assert "Sara" in text and "Bright Smile Dental" in text
    assert "cleaning" in text and "tomorrow" in text and "10:00 AM" in text
    assert "confirm" in text.lower()


# ── the sweep ────────────────────────────────────────────────────────────────
def _wire_whatsapp(monkeypatch):
    """Connect bright-smile to WhatsApp and capture outbound sends."""
    sent = []

    async def _fake_send(phone_id, to, text):
        sent.append((phone_id, to, text))

    monkeypatch.setattr(whatsapp, "_send_text", _fake_send)
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "token123")
    db.update_business_settings("bright-smile", {"whatsapp_phone_id": "PID-1"})
    return sent


def test_sweep_sends_a_reminder_once(client, frozen, monkeypatch):
    sent = _wire_whatsapp(monkeypatch)
    # A booking exactly 24h out (2026-07-09 10:00 vs frozen 2026-07-08 10:00).
    db.save_booking("bright-smile", "2026-07-09", "10:00 AM", "Sara", "0501234567", "cleaning")

    assert reminder_service.send_due_reminders() == 1
    assert len(sent) == 1 and sent[0][1] == "971501234567" and "tomorrow" in sent[0][2]
    # A second sweep must NOT message the same caller again for the same stage.
    assert reminder_service.send_due_reminders() == 0
    assert len(sent) == 1


def test_sweep_sends_both_stages_over_time(client, frozen, monkeypatch):
    sent = _wire_whatsapp(monkeypatch)
    db.save_booking("bright-smile", "2026-07-09", "10:00 AM", "Sara", "0501234567", "cleaning")
    reminder_service.send_due_reminders()  # the 24h stage
    # Advance to 1.5h before the appointment → the 2h stage becomes due.
    monkeypatch.setattr(reminder_service, "_now",
                        lambda: datetime.datetime(2026, 7, 9, 8, 30, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai")))
    assert reminder_service.send_due_reminders() == 1
    assert len(sent) == 2


def test_sweep_skips_far_future_and_cancelled(client, frozen, monkeypatch):
    sent = _wire_whatsapp(monkeypatch)
    db.save_booking("bright-smile", "2026-07-20", "10:00 AM", "Late", "0501110000", "checkup")  # 12 days out
    db.save_booking("bright-smile", "2026-07-09", "10:00 AM", "Gone", "0502220000", "filling")
    # Flip the near one to cancelled (covers the sweep's defensive status check).
    db.set_booking_status("bright-smile", "Gone", "2026-07-09", "10:00 AM", "cancelled")
    assert reminder_service.send_due_reminders() == 0
    assert sent == []


# ── the confirm tool (two-way reply) ─────────────────────────────────────────
def test_confirm_appointment_marks_the_booking(client):
    cal = {f.__name__: f for f in make_calendar_tools({"id": "bright-smile", "open_hour": 9, "close_hour": 17})}
    db.save_booking("bright-smile", "2026-07-09", "10:00 AM", "Sara", "0501234567", "cleaning")
    out = cal["confirm_appointment"]("Sara", "2026-07-09", "10:00 AM")
    assert out["status"] == "confirmed"
    booking = next(b for b in db.list_bookings("bright-smile") if b["patient_name"] == "Sara")
    assert booking["status"] == "confirmed"
    # An unknown slot is a clean not_found, not a crash.
    assert cal["confirm_appointment"]("Sara", "2099-01-01", "9:00 AM")["status"] == "not_found"


# ── the admin trigger ────────────────────────────────────────────────────────
def test_admin_send_reminders_is_admin_only(client):
    assert client.post("/admin/send-reminders").status_code == 401
    assert client.post("/admin/send-reminders", headers=BRIGHT).status_code == 401
    assert client.post("/admin/send-reminders", headers=ADMIN).status_code == 200
