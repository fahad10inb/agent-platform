"""The differentiator: the platform remembers callers — automatically, deduped,
and scoped to one business."""

from app.tools.calendar_tools import make_calendar_tools
from app.tools.memory_tools import make_memory_tools


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


def test_landing_page_serves_the_pitch(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "remembers" in r.text  # the differentiator is the headline
