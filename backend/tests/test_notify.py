"""Owner notifications: bookings/leads/cancellations reach the owner's inbox,
delivery never blocks or breaks the booking, and no email set = silence."""

from app import notify_service
from app.tools.calendar_tools import make_calendar_tools
from app.tools.leads_tools import make_lead_tools


def _capture(monkeypatch):
    """Swallow the thread + record what would have been delivered."""
    sent = []
    monkeypatch.setattr(
        notify_service.threading, "Thread",
        lambda target, args, daemon: type("T", (), {"start": lambda self: sent.append(args)})(),
    )
    return sent


def test_booking_notifies_the_owner(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    state["businesses"]["bright-smile"]["notify_email"] = "owner@clinic.com"
    tools = {f.__name__: f for f in make_calendar_tools({"id": "bright-smile", "open_hour": 9, "close_hour": 17, "slot_minutes": 30})}
    out = tools["book_appointment"]("2026-08-01", "9:00 AM", "Mariam", "0501234567", "cleaning")
    assert out["status"] == "confirmed"
    to, subject, body = sent[0]
    assert to == "owner@clinic.com"
    assert "Mariam" in subject and "9:00 AM" in subject
    assert "0501234567" in body


def test_lead_notifies_the_owner(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    state["businesses"]["skyline-realty"]["notify_email"] = "agent@realty.com"
    tools = {f.__name__: f for f in make_lead_tools("skyline-realty")}
    tools["capture_lead"]("Omar", "0501112233", "2BR in Marina")
    assert sent and "Omar" in sent[0][1] and "Marina" in sent[0][2]


def test_no_email_configured_means_no_send(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    state["businesses"]["bright-smile"].pop("notify_email", None)  # seeded biz persists across tests
    tools = {f.__name__: f for f in make_calendar_tools({"id": "bright-smile", "open_hour": 9, "close_hour": 17, "slot_minutes": 30})}
    tools["book_appointment"]("2026-08-01", "10:00 AM", "Sara")
    assert sent == []


def test_notify_failure_never_breaks_the_booking(client, state, monkeypatch):
    state["businesses"]["bright-smile"]["notify_email"] = "owner@clinic.com"

    def _boom(*a, **k):
        raise RuntimeError("smtp on fire")

    monkeypatch.setattr(notify_service.threading, "Thread", _boom)
    tools = {f.__name__: f for f in make_calendar_tools({"id": "bright-smile", "open_hour": 9, "close_hour": 17, "slot_minutes": 30})}
    out = tools["book_appointment"]("2026-08-01", "11:00 AM", "Sara", "0509998888", "checkup")
    assert out["status"] == "confirmed"  # the booking survives the inbox
