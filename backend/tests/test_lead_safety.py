"""The deterministic lead-capture safety net — a caller who leaves a phone is
never silently lost, even when the model's capture_lead tool doesn't fire."""

from app import db
from app.lead_safety import _find_phone, ensure_lead_captured

RE = {"id": "skyline-realty", "vertical": "real_estate"}


def _seed(cid, *msgs):
    for role, text in msgs:
        db.save_message("skyline-realty", cid, role, text)


def test_find_phone_various_uae_formats():
    assert _find_phone("call me on 0559876543") == "971559876543"
    assert _find_phone("+971 55 987 6543 please") == "971559876543"
    assert _find_phone("00971559876543") == "971559876543"
    assert _find_phone("my budget is 1400000 and 2 beds") == ""   # not a phone
    assert _find_phone("no number here at all") == ""


def test_captures_when_the_tool_missed_it():
    _seed("wa-1",
          ("user", "Hi I'm Tariq Aziz, 0559876543, keen on a 2BR in JVC"),
          ("model", "Our viewing hours are 9-8."))   # note: the model did NOT capture
    assert ensure_lead_captured(RE, "wa-1") is True
    got = [ld for ld in db.list_leads("skyline-realty") if "9876543" in (ld.get("phone") or "")]
    assert got and got[0]["name"] == "Tariq Aziz"


def test_fallback_name_flags_a_net_caught_lead():
    _seed("wa-1b", ("user", "hey, do you have 2BRs? reach me on 0559871111"))
    assert ensure_lead_captured(RE, "wa-1b") is True
    got = [ld for ld in db.list_leads("skyline-realty") if "9871111" in (ld.get("phone") or "")]
    assert got and got[0]["name"] == "New enquiry (auto)"


def test_no_duplicate_when_a_lead_already_exists():
    db.save_lead("skyline-realty", "Tariq Aziz", "0559876543", "2BR JVC")
    _seed("wa-2", ("user", "I'm Tariq, 0559876543"))
    assert ensure_lead_captured(RE, "wa-2") is False   # the tool already captured it


def test_skips_when_the_caller_already_booked():
    db.save_booking("skyline-realty", "2026-08-01", "2:00 PM", "Sara", "0559876543", "viewing")
    _seed("wa-3", ("user", "I'm Sara, 0559876543, please book me"))
    assert ensure_lead_captured(RE, "wa-3") is False


def test_does_nothing_without_a_phone():
    _seed("wa-4", ("user", "do you have any 2-beds in JVC?"))
    assert ensure_lead_captured(RE, "wa-4") is False


def test_skips_non_lead_verticals():
    _seed("wa-5", ("user", "I'm Omar, 0559876543"))
    assert ensure_lead_captured({"id": "skyline-realty", "vertical": "clinic"}, "wa-5") is False
