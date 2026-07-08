"""Regression tests for the pre-launch review fixes: reminder day-word, permit
notes withheld, phone-normalization consistency, scorer negation, XML namespaces."""

import datetime
import zoneinfo

from app import db, nurture_service, reminder_service
from app.tools.qualify_tools import score_lead
from app import listing_import

_TZ = zoneinfo.ZoneInfo("Asia/Dubai")


# ── reminder day-word reflects the actual date, not the stage ────────────────
def test_same_day_reminder_does_not_say_tomorrow(monkeypatch):
    monkeypatch.setattr(reminder_service, "_now",
                        lambda: datetime.datetime(2026, 7, 8, 9, 0, tzinfo=_TZ))
    # A booking TODAY at 5pm (~8h out) fires the 24h stage — but must not say "tomorrow".
    txt = reminder_service.compose_reminder(
        {"name": "Clinic"}, {"patient_name": "Sam", "date": "2026-07-08", "time": "5:00 PM"}, "24h")
    assert "today" in txt and "tomorrow" not in txt
    # A genuine next-day booking DOES say tomorrow.
    txt2 = reminder_service.compose_reminder(
        {"name": "Clinic"}, {"patient_name": "Sam", "date": "2026-07-09", "time": "5:00 PM"}, "24h")
    assert "tomorrow" in txt2


# ── phone normalization is consistent across formats ─────────────────────────
def test_booked_lead_detected_across_phone_formats(client):
    # Lead stored 05x, booking stored +971 — must still be seen as the same person.
    db.save_booking("skyline-realty", "2026-07-20", "5:00 PM", "Sam", "+971 55 300 1122", "viewing")
    assert db.phone_has_booking("skyline-realty", "0553001122") is True


def test_forget_and_dedup_match_across_formats(client, monkeypatch):
    from app import notify_service
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: None)
    db.save_lead("skyline-realty", "Sam", "0553001122", "2BR")
    # Same person, different format → find_recent_lead finds them (no duplicate).
    assert db.find_recent_lead("skyline-realty", "+971553001122") is not None


# ── permit gate: an unpermitted price hidden in the description is withheld ───
def test_permit_gate_withholds_price_in_notes(client):
    from app.prompt_service import build_system_prompt
    db.replace_listings("skyline-realty", [
        {"title": "Villa X", "area": "Emirates Hills", "notes": "asking AED 25M, sea view"},
    ])  # no permit
    p = build_system_prompt(db.get_business("skyline-realty"))
    assert "25M" not in p and "sea view" not in p  # the description was withheld too


# ── scorer no longer over-counts on negations ───────────────────────────────
def test_scorer_ignores_negated_signals():
    # "not pre-approved" + "not moving anytime soon" must NOT score as ready/urgent.
    s, _ = score_lead({"budget": "1.5M", "area": "JVC",
                       "pre_approval": "not pre-approved", "timeline": "not moving anytime soon"})
    assert s == "B"  # budget + area only = 2 points, not bumped to A
    # Genuine positives still score A.
    s2, _ = score_lead({"budget": "1.5M", "area": "JVC", "pay_method": "cash"})
    assert s2 == "A"


# ── XML import handles namespaced feeds ──────────────────────────────────────
def test_xml_import_handles_namespaces():
    xml = """<feed xmlns="http://example.com/props">
      <property><title>2BR Marina</title><community>Dubai Marina</community>
        <price>1.8M</price><permit_number>7129</permit_number></property>
    </feed>"""
    rows = listing_import.parse_xml(xml)
    assert len(rows) == 1 and rows[0]["title"] == "2BR Marina" and rows[0]["permit_number"] == "7129"
