"""The differentiator: the platform remembers callers — automatically, deduped,
and scoped to one business."""

import datetime
import zoneinfo

import pytest

from app.tools import calendar_tools as ct
from app.tools.calendar_tools import make_calendar_tools
from app.tools.memory_tools import make_memory_tools

# The booking test uses a fixed date — freeze "now" so it stays in the future and
# the test can't rot against the real clock (see test_calendar_tools).
_FROZEN = datetime.datetime(2026, 7, 7, 10, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))


@pytest.fixture(autouse=True)
def _frozen_clock(monkeypatch):
    monkeypatch.setattr(ct, "_now", lambda: _FROZEN)


def _mem(business_id="bright-smile"):
    return {f.__name__: f for f in make_memory_tools(business_id)}


def _cal():
    return {f.__name__: f for f in make_calendar_tools({"id": "bright-smile", "open_hour": 9, "close_hour": 17, "slot_minutes": 30})}


def test_new_caller_profile_is_empty(client):
    out = _mem()["recall_caller"]("Mariam")
    assert out["returning_caller"] is False
    assert out["visit_count"] == 0


def test_booking_automatically_becomes_memory(client):
    """A visit is remembered even if the model never calls remember_about_caller."""
    _cal()["book_appointment"]("2026-07-10", "9:00 AM", "Mariam", "0501112222", "blow-dry")
    out = _mem()["recall_caller"]("Mariam")
    assert out["returning_caller"] is True
    assert out["visit_count"] == 1
    assert any("blow-dry" in n for n in out["known_notes"])


def test_remember_dedupes_exact_repeats(client):
    tools = _mem()
    tools["remember_about_caller"]("Mariam", "prefers Rana as her stylist")
    dup = tools["remember_about_caller"]("Mariam", "Prefers Rana as her stylist ")
    assert dup["status"] == "already_known"
    assert len(tools["recall_caller"]("Mariam")["known_notes"]) == 1


def test_memory_is_isolated_per_business(client):
    _mem("bright-smile")["remember_about_caller"]("Sarah", "allergic to lidocaine")
    other = _mem("velvet-hair")["recall_caller"]("Sarah")
    assert other["known_notes"] == []
    assert other["returning_caller"] is False


def test_appointments_hidden_without_phone_verification(client):
    """Anti-IDOR: typing a name into the public widget must not expose that
    person's appointment details — until the caller proves the number on file."""
    _cal()["book_appointment"]("2026-08-01", "9:00 AM", "Mariam", "0501234567", "cleaning")
    stranger = _mem()["recall_caller"]("Mariam")
    assert stranger["identity_verified"] is False
    assert stranger["appointments"] == "hidden — verify with phone_last4 first"
    owner = _mem()["recall_caller"]("Mariam", phone_last4="4567")
    assert owner["identity_verified"] is True
    assert owner["appointments"][0]["date"] == "2026-08-01"


def test_find_and_cancel_require_verification(client):
    cal = _cal()
    cal["book_appointment"]("2026-08-01", "9:00 AM", "Mariam", "0501234567", "cleaning")
    assert cal["find_my_appointments"]("Mariam")["status"] == "verification_needed"
    assert cal["cancel_appointment"]("Mariam", "2026-08-01", "9:00 AM")["status"] == "verification_needed"
    assert (
        cal["cancel_appointment"]("Mariam", "2026-08-01", "9:00 AM", phone_last4="4567")["status"]
        == "cancelled"
    )


def test_caller_without_phone_on_file_is_not_locked_out(client):
    cal = _cal()
    cal["book_appointment"]("2026-08-01", "9:00 AM", "Omar")  # booked without a phone
    assert cal["find_my_appointments"]("Omar")["appointments"]


def test_history_endpoint_serves_the_widget(client, state):
    from app import db

    db.save_message("bright-smile", "web-abc12345", "user", "hi")
    db.save_message("bright-smile", "web-abc12345", "model", "hello!")
    r = client.get("/chat/history?business_id=bright-smile&conversation_id=web-abc12345")
    assert r.status_code == 200
    assert [t["role"] for t in r.json()] == ["user", "model"]


def test_landing_page_serves_the_pitch(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "remembers" in r.text  # the differentiator is the headline


def test_landing_page_carries_the_fair_billing_pledge(client):
    """The anti-billing-betrayal section (the market's #1 complaint): all three
    pledges in writing, plus the honest 'not live yet' framing, plus the FAQ."""
    r = client.get("/")
    assert "Fair billing, in writing" in r.text
    assert "Spam and one-line drive-bys are never counted." in r.text
    assert "Your usage meter is always visible on your dashboard." in r.text
    assert "Cancel anytime — one click, no email maze." in r.text
    assert "When paid plans launch, these three are the contract." in r.text
    assert "Will spam or junk messages count against me?" in r.text


def test_widget_greets_with_ai_disclosure(client):
    """Disclosure-by-default: the widget's fresh-start greeting says it's the
    AI assistant and offers the human path, before the caller types a word."""
    r = client.get("/widget")
    assert r.status_code == 200
    assert (
        "Hi! I'm the AI assistant here — I can answer questions, book you in, "
        "or get you a human. How can I help?"
    ) in r.text
    assert "Book an appointment" in r.text  # the starter chips survived
