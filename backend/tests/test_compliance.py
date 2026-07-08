"""Compliance guardrail (module #5): the HARD permit gate (unpermitted prices
withheld from the model), the transactional-escalation rules, and PDPL opt-out."""

from app import db, nurture_service, reminder_service
from app.prompt_service import build_system_prompt
from app.tools.qualify_tools import make_qualify_tools


# ── hard permit gate: an unpermitted price never reaches the model ───────────
def test_unpermitted_price_is_withheld_from_the_prompt(client):
    db.replace_listings("skyline-realty", [
        {"title": "2BR Marina", "area": "Dubai Marina", "price": "1.8M",
         "purpose": "sale", "permit_number": "7129XYZ"},
        {"title": "Secret Villa", "area": "Emirates Hills", "price": "25M",
         "purpose": "sale"},  # no permit — the 25M must NOT appear
    ])
    p = build_system_prompt(db.get_business("skyline-realty"))
    assert "1.8M" in p and "permit 7129XYZ" in p          # permitted: price present
    assert "25M" not in p                                 # unpermitted: price GONE
    assert "Secret Villa" in p and "[NO PERMIT — price withheld]" in p
    assert "not been given its price" in p                # the instruction is there


# ── transactional escalation rules in the real-estate prompt ─────────────────
def test_real_estate_prompt_carries_the_escalation_rules(client):
    p = build_system_prompt(db.get_business("skyline-realty"))
    assert "never cross these lines" in p.lower() or "COMPLIANCE" in p
    assert "do NOT negotiate" in p
    assert "qualify" in p and "mortgage" in p.lower()
    assert "request_human" in p and "stop_contact" in p


# ── PDPL opt-out: the tool + both sweeps honoring it ─────────────────────────
def _tools(business_id="skyline-realty"):
    return {f.__name__: f for f in make_qualify_tools({"id": business_id})}


def test_stop_contact_records_the_opt_out(client):
    out = _tools()["stop_contact"]("0501234567")
    assert out["status"] == "opted_out"
    assert db.is_opted_out("skyline-realty", "+971 50 123 4567")  # matched on digits


def test_opted_out_lead_is_not_nurtured(client, monkeypatch):
    import datetime
    import zoneinfo
    now = datetime.datetime(2026, 7, 8, 10, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))
    monkeypatch.setattr(nurture_service, "_now", lambda: now)
    lead = {"business_id": "skyline-realty", "name": "Sam", "phone": "0501234567",
            "created_at": now - datetime.timedelta(days=7)}
    monkeypatch.setattr(db, "leads_for_nurture", lambda within_days=45: [lead])
    db.set_opt_out("skyline-realty", "0501234567")
    assert nurture_service.send_due_nurtures() == 0  # respected — nothing sent


def test_opted_out_caller_gets_no_reminder(client, monkeypatch):
    import datetime
    import zoneinfo
    now = datetime.datetime(2026, 7, 8, 10, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai"))
    monkeypatch.setattr(reminder_service, "_now", lambda: now)
    db.update_business_settings("skyline-realty", {"whatsapp_phone_id": "PID"})
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "t")
    db.save_booking("skyline-realty", "2026-07-09", "10:00 AM", "Sam", "0501234567", "viewing")
    db.set_opt_out("skyline-realty", "0501234567")
    assert reminder_service.send_due_reminders() == 0  # opt-out wins over the reminder
