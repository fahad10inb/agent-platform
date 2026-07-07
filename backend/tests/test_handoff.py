"""Escalation to a human (request_human) + after-hours prompt behavior: the
agent always has a graceful exit, the owner always hears about it, and the
prompt tells the truth about whether the business is open right now."""

import datetime
import zoneinfo

from app import db, notify_service, prompt_service
from app.prompt_service import build_system_prompt
from app.tools.handoff_tools import make_handoff_tools

BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}


def _capture(monkeypatch):
    """Swallow the thread + record what would have been delivered."""
    sent = []
    monkeypatch.setattr(
        notify_service.threading, "Thread",
        lambda target, args, daemon: type("T", (), {"start": lambda self: sent.append(args)})(),
    )
    return sent


def _request_human(biz):
    return {f.__name__: f for f in make_handoff_tools(biz)}["request_human"]


def _freeze(monkeypatch, hour):
    frozen = datetime.datetime(2026, 7, 7, hour, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))
    monkeypatch.setattr(prompt_service, "_now", lambda: frozen)


# ── the request_human tool ────────────────────────────────────────────────────
def test_request_human_shares_the_transfer_number(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    state["businesses"]["bright-smile"]["notify_email"] = "owner@clinic.com"
    state["businesses"]["bright-smile"]["transfer_number"] = "+971 4 123 4567"
    out = _request_human(db.get_business("bright-smile"))("billing dispute needs a manager")
    assert out["status"] == "transfer"
    assert out["transfer_number"] == "+971 4 123 4567"
    assert "+971 4 123 4567" in out["message"]
    to, subject, body = sent[0]  # the owner is alerted with the reason
    assert to == "owner@clinic.com"
    assert "asked for a human" in subject and "billing dispute" in subject


def test_request_human_without_number_takes_a_message(client, state, monkeypatch):
    sent = _capture(monkeypatch)
    state["businesses"]["bright-smile"]["notify_email"] = "owner@clinic.com"
    state["businesses"]["bright-smile"].pop("transfer_number", None)
    out = _request_human(db.get_business("bright-smile"))("caller is frustrated about a refund")
    assert out["status"] == "no_transfer_available"
    assert "capture_lead" in out["message"]  # steered to take a message instead
    assert sent and "frustrated about a refund" in sent[0][1]  # owner still notified


def test_chat_exposes_request_human(client, monkeypatch):
    """The tool is actually wired into /chat's toolbox."""
    from app import chat_core

    seen = {}

    async def _fake(system_prompt, history, tools=None):
        seen["tools"] = [t.__name__ for t in (tools or [])]
        return "ok"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    client.post("/chat", json={"message": "hi", "business_id": "bright-smile"})
    assert "request_human" in seen["tools"]


# ── settings plumbing ─────────────────────────────────────────────────────────
def test_transfer_settings_roundtrip(client):
    r = client.post(
        "/manage/bright-smile",
        json={"transfer_number": "+97141234567", "after_hours_mode": "book_only"},
        headers=BRIGHT,
    )
    assert r.status_code == 200
    g = client.get("/manage/bright-smile", headers=BRIGHT).json()
    assert g["transfer_number"] == "+97141234567"
    assert g["after_hours_mode"] == "book_only"
    # Only the three known modes are accepted.
    bad = client.post("/manage/bright-smile", json={"after_hours_mode": "party_mode"}, headers=BRIGHT)
    assert bad.status_code == 422


# ── the prompt: escalation line + after-hours line ────────────────────────────
def test_transfer_prompt_line_only_when_configured():
    p = build_system_prompt({"name": "X", "type": "clinic", "transfer_number": "+971 50 111 2222"})
    assert "request_human" in p
    bare = build_system_prompt({"name": "X", "type": "clinic"})
    assert "request_human" not in bare


def test_after_hours_line_absent_when_open(monkeypatch):
    _freeze(monkeypatch, 10)  # 10am inside 9–17
    p = build_system_prompt({"name": "X", "type": "clinic", "open_hour": 9, "close_hour": 17})
    assert "CLOSED" not in p


def test_after_hours_modes(monkeypatch):
    _freeze(monkeypatch, 22)  # 10pm — well past closing
    base = {"name": "X", "type": "clinic", "open_hour": 9, "close_hour": 17}
    take_message = build_system_prompt(base)  # unset mode falls back to take_message
    assert "RIGHT NOW the business is CLOSED" in take_message
    assert "as soon as the business opens" in take_message
    assert "confirm the booking" in build_system_prompt({**base, "after_hours_mode": "book_only"})
    assert "do NOT book anything" in build_system_prompt({**base, "after_hours_mode": "info_only"})
