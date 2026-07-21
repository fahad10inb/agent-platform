"""Requirement-match alerts — a listing that fits a lead's captured requirements
should ping that lead ONCE, never blast, and never advertise an unpermitted unit."""

from app import db, matcher_service
from app.matcher_service import compose_match, matches

BID = "skyline-realty"  # a seeded real_estate tenant

PERMITTED = {
    "area": "JVC", "bedrooms": "2", "price": "1.4M", "purpose": "sale",
    "permit_number": "7129XYZ", "title": "2BR Bloom Towers",
}


def _lead(**over):
    fields = {"area": "JVC", "bedrooms": "2", "purpose": "buy", "budget": "1.5M"}
    fields.update(over)
    return fields


# ── matching logic ───────────────────────────────────────────────────────────
def test_a_clean_match():
    assert matches(_lead(), PERMITTED) is True


def test_area_substring_still_matches():
    assert matches(_lead(area="Marina"), {**PERMITTED, "area": "Dubai Marina"}) is True


def test_wrong_area_does_not_match():
    assert matches(_lead(area="Downtown"), PERMITTED) is False


def test_wrong_bedrooms_does_not_match():
    assert matches(_lead(bedrooms="3"), PERMITTED) is False


def test_rent_lead_not_matched_to_a_sale_listing():
    assert matches(_lead(purpose="rent"), PERMITTED) is False


def test_over_budget_does_not_match():
    assert matches(_lead(budget="1M"), PERMITTED) is False   # 1.4M > 1M*1.1


def test_an_unpermitted_listing_never_matches():
    assert matches(_lead(), {**PERMITTED, "permit_number": ""}) is False


def test_no_area_on_the_lead_means_no_blind_match():
    assert matches(_lead(area=""), PERMITTED) is False


def test_compose_names_the_lead_the_area_and_the_price():
    msg = compose_match({"name": "Skyline Realty"}, "Ahmed Khan", PERMITTED)
    assert "Ahmed" in msg and "JVC" in msg and "1.4M" in msg


# ── the sweep ────────────────────────────────────────────────────────────────
def _seed_match(phone="971501234567"):
    db.replace_listings(BID, [dict(PERMITTED)])
    db.upsert_qualification(BID, phone, "Ahmed Khan", _lead(), "A")


def test_sweep_alerts_a_matching_lead_once():
    _seed_match()
    assert matcher_service.send_due_matches() == 1
    # the alert is seeded into the lead's thread so their reply re-qualifies
    hist = db.get_history(BID, "wa-971501234567")
    assert any("matching what you were after" in m["text"] for m in hist)
    # a second sweep re-alerts no one (throttle + once-per-property)
    assert matcher_service.send_due_matches() == 0


def test_sweep_skips_a_lead_who_already_booked():
    _seed_match()
    db.save_booking(BID, "2026-08-01", "2:00 PM", "Ahmed Khan", "971501234567", "viewing")
    assert matcher_service.send_due_matches() == 0


def test_sweep_skips_an_opted_out_lead():
    _seed_match()
    db.set_opt_out(BID, "971501234567")
    assert matcher_service.send_due_matches() == 0


def test_sweep_ignores_a_non_matching_lead():
    db.replace_listings(BID, [dict(PERMITTED)])
    db.upsert_qualification(BID, "971509999999", "Sara", _lead(area="Downtown"), "B")
    assert matcher_service.send_due_matches() == 0
