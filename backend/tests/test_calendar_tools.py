"""Slot generation, time normalization, and the no-double-booking guarantees."""

from app import db
from app.tools.calendar_tools import _all_slots, _norm_time, make_calendar_tools

BIZ = {"id": "bright-smile", "open_hour": 9, "close_hour": 11, "slot_minutes": 30}


def _tools(business=BIZ):
    t = make_calendar_tools(business)
    return {f.__name__: f for f in t}


def test_norm_time_canonicalizes_variants():
    assert _norm_time("2:00 pm") == "2:00 PM"
    assert _norm_time(" 2 PM ") == "2:00 PM"
    assert _norm_time("14:00") == "2:00 PM"
    assert _norm_time("09:30") == "9:30 AM"
    assert _norm_time("9:30 AM") == "9:30 AM"
    assert _norm_time("12:00") == "12:00 PM"   # noon
    assert _norm_time("00:30") == "12:30 AM"   # after midnight
    assert _norm_time("14:00 PM") == "2:00 PM"  # trust the 24h digits
    assert _norm_time("half past nine") == "half past nine"  # unparseable: pass through


def test_all_slots_generates_the_day():
    assert _all_slots(9, 11, 30) == ["9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM"]


def test_bad_slot_minutes_cannot_hang_the_server():
    tools = _tools({"id": "b", "open_hour": 9, "close_hour": 17, "slot_minutes": -5})
    out = tools["check_availability"]("2026-07-10")  # would loop forever before the guard
    assert len(out["available_slots"]) == 16  # falls back to 30-minute slots


def test_lowercase_time_cannot_double_book(client):
    tools = _tools()
    first = tools["book_appointment"]("2026-07-10", "9:00 AM", "Sara", "0501234567", "cleaning")
    assert first["status"] == "confirmed"
    dup = tools["book_appointment"]("2026-07-10", "9:00 am", "Omar", "0507654321", "checkup")
    assert dup["status"] == "unavailable"


def test_race_lost_at_insert_reports_unavailable(client, monkeypatch):
    tools = _tools()
    monkeypatch.setattr(db, "save_booking", lambda *a, **k: None)  # unique index said no
    out = tools["book_appointment"]("2026-07-10", "9:00 AM", "Sara")
    assert out["status"] == "unavailable"


def test_reschedule_into_taken_slot_is_unavailable(client):
    tools = _tools()
    tools["book_appointment"]("2026-07-10", "9:00 AM", "Sara")
    tools["book_appointment"]("2026-07-10", "9:30 AM", "Omar")
    out = tools["reschedule_appointment"]("Sara", "2026-07-10", "9:00 AM", "2026-07-10", "9:30 am")
    assert out["status"] == "unavailable"


def test_availability_hides_booked_slots(client):
    tools = _tools()
    tools["book_appointment"]("2026-07-10", "9:00 AM", "Sara")
    out = tools["check_availability"]("2026-07-10")
    assert "9:00 AM" not in out["available_slots"]
    assert "9:30 AM" in out["available_slots"]
