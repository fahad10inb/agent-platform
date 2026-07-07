"""Structured service menu: endpoint auth + validation, replace semantics,
prompt rendering, per-service slot math, and the overlap guarantees (a 15-min
trim and a 90-min color must never share the same stretch of calendar)."""

import datetime
import zoneinfo

import pytest

from app import db
from app.prompt_service import build_system_prompt
from app.tools import calendar_tools as ct

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
VELVET = {"X-API-Key": "bizkey_velvet_hair_demo"}

MENU = [
    {"name": "quick cut", "duration_min": 30, "price": "50 AED"},
    {"name": "full color", "duration_min": 90, "price": "250 AED"},
]


@pytest.fixture
def frozen_clock(monkeypatch):
    """Pin 'now' well before the test dates so notice windows can't interfere."""
    frozen = datetime.datetime(2026, 7, 7, 8, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))
    monkeypatch.setattr(ct, "_now", lambda: frozen)
    return frozen


def _tools(biz=None):
    biz = biz or {"id": "bright-smile", "open_hour": 9, "close_hour": 17, "slot_minutes": 30}
    return {f.__name__: f for f in ct.make_calendar_tools(biz)}


# ── the /manage/{id}/services endpoint ───────────────────────────────────────
def test_services_endpoint_auth_matrix(client):
    """Deny by default, deny cross-tenant, allow own key and admin."""
    rows = {"services": [{"name": "skin fade", "duration_min": 45, "price": "80 AED"}]}
    assert client.post("/manage/bright-smile/services", json=rows).status_code == 401
    assert client.post("/manage/bright-smile/services", json=rows, headers=VELVET).status_code == 403
    assert client.post("/manage/bright-smile/services", json=rows, headers=BRIGHT).status_code == 200
    assert client.post("/manage/bright-smile/services", json=rows, headers=ADMIN).status_code == 200


def test_services_endpoint_validates_rows(client):
    """Durations outside 5–480, empty names and >50 rows are all rejected."""
    for bad in (
        {"services": [{"name": "x", "duration_min": 3}]},
        {"services": [{"name": "x", "duration_min": 500}]},
        {"services": [{"name": "", "duration_min": 30}]},
        {"services": [{"name": f"s{i}", "duration_min": 30} for i in range(51)]},
    ):
        assert client.post("/manage/bright-smile/services", json=bad, headers=BRIGHT).status_code == 422


def test_replace_semantics_and_manage_prefill(client):
    """POST replaces the whole menu (no appending), GET /manage returns it for
    the dashboard textarea, and menus never leak across tenants."""
    client.post("/manage/bright-smile/services", json={"services": MENU}, headers=BRIGHT)
    rows = client.get("/manage/bright-smile", headers=BRIGHT).json()["services_rows"]
    assert [s["name"] for s in rows] == ["quick cut", "full color"]
    assert rows[1]["duration_min"] == 90 and rows[1]["price"] == "250 AED"

    client.post("/manage/bright-smile/services",
                json={"services": [{"name": "beard trim", "duration_min": 15}]}, headers=BRIGHT)
    rows = client.get("/manage/bright-smile", headers=BRIGHT).json()["services_rows"]
    assert [s["name"] for s in rows] == ["beard trim"]  # replaced, not appended

    assert client.get("/manage/velvet-hair", headers=VELVET).json()["services_rows"] == []


# ── the menu in the prompt ────────────────────────────────────────────────────
def test_menu_renders_in_prompt(client):
    db.replace_services("bright-smile", [{"name": "skin fade", "duration_min": 45, "price": "80 AED"}])
    p = build_system_prompt(db.get_business("bright-smile"))
    assert "SERVICE MENU" in p
    assert "skin fade — 45 min — 80 AED" in p
    assert "Quote prices from this menu" in p


def test_no_menu_means_no_menu_block(client):
    p = build_system_prompt(db.get_business("velvet-hair"))
    assert "SERVICE MENU" not in p


# ── per-service slot math ─────────────────────────────────────────────────────
def test_service_duration_drives_the_grid(client, frozen_clock):
    """A 90-min service walks the day in 90-min steps and can't spill past
    closing; a name that's not on the menu falls back to the global grid."""
    db.replace_services("bright-smile", MENU)
    tools = _tools({"id": "bright-smile", "open_hour": 9, "close_hour": 12, "slot_minutes": 30})
    out = tools["check_availability"]("2026-07-08", service="Full Color")  # case-insensitive
    assert out["available_slots"] == ["9:00 AM", "10:30 AM"]
    assert out["service"] == "full color" and out["duration_min"] == 90

    fallback = tools["check_availability"]("2026-07-08", service="something else")
    assert len(fallback["available_slots"]) == 6  # 9:00–11:30 on the 30-min grid


def test_booked_service_blocks_every_slot_it_covers(client, frozen_clock):
    """Availability must hide any start that would land inside the 9:00–10:30
    color, not just the 9:00 slot itself."""
    db.replace_services("bright-smile", MENU)
    tools = _tools()
    assert tools["book_appointment"](
        "2026-07-08", "9:00 AM", "Sara", "0501234567", service="full color"
    )["status"] == "confirmed"
    free = tools["check_availability"]("2026-07-08", service="quick cut")["available_slots"]
    assert "9:00 AM" not in free and "9:30 AM" not in free and "10:00 AM" not in free
    assert "10:30 AM" in free


def test_overlap_blocked_short_into_long(client, frozen_clock):
    """New 30-min booking inside an existing 90-min booking's window: refused."""
    db.replace_services("bright-smile", MENU)
    tools = _tools()
    tools["book_appointment"]("2026-07-08", "9:00 AM", "Sara", service="full color")
    denied = tools["book_appointment"]("2026-07-08", "10:00 AM", "Omar", service="quick cut")
    assert denied["status"] == "unavailable"
    ok = tools["book_appointment"]("2026-07-08", "10:30 AM", "Omar", service="quick cut")
    assert ok["status"] == "confirmed"  # first slot after the color ends


def test_overlap_blocked_long_over_short(client, frozen_clock):
    """New 90-min booking that would swallow an existing 30-min one: refused."""
    db.replace_services("bright-smile", MENU)
    tools = _tools()
    tools["book_appointment"]("2026-07-08", "11:00 AM", "Sara", service="quick cut")
    denied = tools["book_appointment"]("2026-07-08", "10:00 AM", "Omar", service="full color")
    assert denied["status"] == "unavailable"  # 10:00–11:30 covers the 11:00 cut
    ok = tools["book_appointment"]("2026-07-08", "11:30 AM", "Omar", service="full color")
    assert ok["status"] == "confirmed"  # starts exactly when the cut ends


def test_existing_duration_inferred_from_reason(client, frozen_clock):
    """A booking saved without the service param still blocks its true window,
    because its stored reason names the service."""
    db.replace_services("bright-smile", MENU)
    db.save_booking("bright-smile", "2026-07-08", "9:00 AM", "Sara", "", "full color for the wedding")
    tools = _tools()
    denied = tools["book_appointment"]("2026-07-08", "10:00 AM", "Omar", service="quick cut")
    assert denied["status"] == "unavailable"


def test_booking_reason_records_the_service_name(client, frozen_clock, state):
    """book_appointment writes the menu name into the reason — that's what
    future overlap checks read the duration back from."""
    db.replace_services("bright-smile", MENU)
    _tools()["book_appointment"](
        "2026-07-08", "9:00 AM", "Sara", "050", reason="going gray", service="full color"
    )
    assert state["bookings"][0]["reason"] == "full color — going gray"


def test_no_menu_keeps_the_old_behavior(client, frozen_clock):
    """Businesses without service rows behave exactly as before — the optional
    service arg is ignored and the exact-slot check still rules."""
    tools = _tools()
    assert tools["book_appointment"](
        "2026-07-08", "9:00 AM", "Sara", service="full color"
    )["status"] == "confirmed"
    dup = tools["book_appointment"]("2026-07-08", "9:00 AM", "Omar")
    assert dup["status"] == "unavailable"
    free = tools["check_availability"]("2026-07-08")["available_slots"]
    assert "9:00 AM" not in free and "9:30 AM" in free
