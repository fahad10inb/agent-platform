"""Getting a booking into the owner's real calendar — without the Google OAuth swamp.

Three ways, no OAuth, no Google verification, no 7-day token expiry:
  • /calendar/{token}.ics          — a feed they paste into Google Calendar
  • /manage/{id}/bookings/{n}.ics  — one booking, "Add to calendar", instant
  • POST /manage/{id}/calendar-token — mint/rotate the feed URL
"""

import datetime

from app import db
from app.ics import build_ics

BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
VELVET = {"X-API-Key": "bizkey_velvet_hair_demo"}
ADMIN = {"X-API-Key": "admin_test_key"}

BIZ = {"id": "bright-smile", "name": "Bright Smile Dental", "slot_minutes": 30,
       "location": "Jumeirah, Dubai"}
NOW = datetime.datetime(2026, 7, 14, 8, 0, tzinfo=datetime.timezone.utc)


# ── the .ics itself ──────────────────────────────────────────────────────────
def test_a_dubai_booking_becomes_a_correct_utc_event():
    """Bookings are stored as a Dubai date + a slot label. Dubai is UTC+4 with no
    DST, so 4:00 PM must land as 12:00Z — get this wrong and every viewing shows
    up in the owner's calendar at the wrong hour."""
    ics = build_ics(BIZ, [{"id": 7, "date": "2026-07-16", "time": "4:00 PM",
                           "patient_name": "Ahmed", "phone": "0501234567",
                           "reason": "viewing", "status": "booked"}], now=NOW)
    assert "BEGIN:VCALENDAR" in ics and "END:VCALENDAR" in ics
    assert "DTSTART:20260716T120000Z" in ics          # 4pm Dubai = 12:00 UTC
    assert "DTEND:20260716T123000Z" in ics            # + the 30-min slot
    assert "SUMMARY:Ahmed - viewing" in ics
    assert "STATUS:CONFIRMED" in ics
    assert "LOCATION:Jumeirah\\, Dubai" in ics        # comma escaped per RFC 5545
    assert "0501234567" in ics                        # the phone rides in the body


def test_a_cancelled_booking_is_cancelled_not_dropped():
    """Dropping it would leave a ghost viewing sitting in the owner's calendar."""
    ics = build_ics(BIZ, [{"id": 8, "date": "2026-07-16", "time": "9:00 AM",
                           "patient_name": "Gone", "status": "cancelled"}], now=NOW)
    assert "STATUS:CANCELLED" in ics


def test_the_uid_is_stable_so_a_refeed_does_not_duplicate_the_viewing():
    a = build_ics(BIZ, [{"id": 7, "date": "2026-07-16", "time": "4:00 PM",
                         "patient_name": "Ahmed"}], now=NOW)
    b = build_ics(BIZ, [{"id": 7, "date": "2026-07-16", "time": "4:00 PM",
                         "patient_name": "Ahmed"}],
                  now=NOW + datetime.timedelta(hours=5))
    assert "UID:booking-7@receptionai" in a
    assert a.count("UID:") == b.count("UID:") == 1
    # Same UID across reads = the calendar updates the event instead of adding a
    # second one every time it polls.
    assert "UID:booking-7@receptionai" in b


def test_an_unparseable_row_is_skipped_not_fatal():
    """One bad row must never take down the whole feed."""
    ics = build_ics(BIZ, [
        {"id": 1, "date": "not-a-date", "time": "4:00 PM", "patient_name": "Bad"},
        {"id": 2, "date": "2026-07-16", "time": "half past nine", "patient_name": "Also bad"},
        {"id": 3, "date": "2026-07-16", "time": "4:00 PM", "patient_name": "Good"},
    ], now=NOW)
    assert ics.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:Good" in ics


# ── the endpoints ────────────────────────────────────────────────────────────
def _mint(client):
    r = client.post("/manage/bright-smile/calendar-token", headers=BRIGHT)
    assert r.status_code == 200
    return r.json()["url"]


def test_the_owner_mints_a_feed_url_and_it_serves_their_bookings(client):
    db.save_booking("bright-smile", "2026-07-16", "4:00 PM", "Ahmed", "0501234567", "viewing")
    url = _mint(client)
    assert "/calendar/cal_" in url and url.endswith(".ics")

    path = url[url.index("/calendar/"):]
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in r.text and "SUMMARY:Ahmed - viewing" in r.text


def test_the_served_ics_has_no_bom_and_an_ascii_separator(client):
    """The feed must NOT lead with a UTF-8 BOM: Google Calendar's URL-subscription
    parser silently drops the whole calendar when the body doesn't start with
    BEGIN:VCALENDAR, so a leading BOM makes every day show empty. The em-dash
    mojibake ("â") is fixed with a plain ASCII separator instead — no client can
    misread that."""
    db.save_booking("bright-smile", "2026-07-16", "4:00 PM", "Ahmed", "0501234567", "viewing")
    path = _mint(client)[len("http://testserver"):]
    raw = client.get(path).content                     # bytes, before any decode
    assert not raw.startswith(b"\xef\xbb\xbf")          # NO BOM
    assert raw.lstrip().startswith(b"BEGIN:VCALENDAR")  # body opens as Google needs
    assert "—".encode() not in raw                 # no em-dash bytes anywhere
    assert b"SUMMARY:Ahmed - viewing" in raw            # ASCII hyphen separator


def test_the_feed_needs_no_auth_header_because_calendars_cannot_send_one(client):
    """Google Calendar subscribes to a bare URL — the token IS the auth."""
    db.save_booking("bright-smile", "2026-07-16", "4:00 PM", "Ahmed")
    path = _mint(client)[len("http://testserver"):]
    assert client.get(path).status_code == 200          # no X-API-Key sent


def test_a_wrong_or_rotated_token_404s_and_cannot_enumerate_businesses(client):
    assert client.get("/calendar/cal_nonsense.ics").status_code == 404

    old = _mint(client)[len("http://testserver"):]
    assert client.get(old).status_code == 200
    _mint(client)                                       # rotate
    assert client.get(old).status_code == 404           # every old subscription dies


def test_minting_a_token_is_tenant_scoped(client):
    assert client.post("/manage/bright-smile/calendar-token").status_code == 401
    assert client.post("/manage/bright-smile/calendar-token", headers=VELVET).status_code == 403
    assert client.post("/manage/bright-smile/calendar-token", headers=ADMIN).status_code == 200


def test_add_to_calendar_returns_one_booking_and_is_authed(client):
    bid = db.save_booking("bright-smile", "2026-07-16", "4:00 PM", "Ahmed", "0501234567", "viewing")
    r = client.get(f"/manage/bright-smile/bookings/{bid}.ics", headers=BRIGHT)
    assert r.status_code == 200
    assert r.text.count("BEGIN:VEVENT") == 1 and "SUMMARY:Ahmed - viewing" in r.text

    # Another tenant cannot pull it, and an unknown booking 404s.
    assert client.get(f"/manage/bright-smile/bookings/{bid}.ics", headers=VELVET).status_code == 403
    assert client.get("/manage/bright-smile/bookings/99999.ics", headers=BRIGHT).status_code == 404
