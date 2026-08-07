"""The domain post-condition ledger: for every action the AI CLAIMS, verify the
required effect exists — else repair it (lead, handoff) or escalate to a human
(booking / reschedule / cancel, which we must never guess at). This is the
generalization of the lead net to every action."""

from app import db, notify_service, postconditions

RE = {"id": "skyline-realty", "vertical": "real_estate"}


def _capture_alerts(monkeypatch):
    alerts = []
    monkeypatch.setattr(
        notify_service, "notify_owner", lambda bid, subj, body: alerts.append(subj)
    )
    return alerts


def test_booking_claim_with_no_booking_escalates_to_the_owner(monkeypatch):
    """A caller who thinks they're booked but isn't is worse than a lost lead — we
    must NOT auto-book (which slot?), so we alert the owner to confirm."""
    alerts = _capture_alerts(monkeypatch)
    postconditions.reconcile_claims(RE, "c1", ["appointment booked"])
    assert alerts and ("book" in alerts[0].lower() or "viewing" in alerts[0].lower())


def test_existing_booking_is_not_a_false_alarm(monkeypatch):
    """Verify passes when the booking is really on record — no owner spam."""
    alerts = _capture_alerts(monkeypatch)
    db.save_message("skyline-realty", "c2", "user", "I'm Omar, 0559873333")
    db.save_booking(
        "skyline-realty", "2026-08-20", "4:00 PM", "Omar", "0559873333", "viewing"
    )
    postconditions.reconcile_claims(RE, "c2", ["appointment booked"])
    assert alerts == []


def test_handoff_claim_alerts_a_human(monkeypatch):
    """Claiming a human handoff without the tool must still reach a human."""
    alerts = _capture_alerts(monkeypatch)
    postconditions.reconcile_claims(RE, "c3", ["human handoff"])
    assert any("human" in a.lower() for a in alerts)


def test_lead_claim_is_repaired_by_the_net(monkeypatch):
    """The lead entry repairs deterministically — the number is right there."""
    db.save_message("skyline-realty", "c4", "user", "I'm Sara, 0559871234")
    postconditions.reconcile_claims(RE, "c4", ["lead / follow-up"])
    got = [
        r
        for r in db.list_leads("skyline-realty")
        if "9871234" in (r.get("phone") or "")
    ]
    assert got  # saved deterministically, even though no tool fired


def test_unknown_or_empty_claims_do_nothing(monkeypatch):
    alerts = _capture_alerts(monkeypatch)
    postconditions.reconcile_claims(RE, "c5", [])
    postconditions.reconcile_claims(RE, "c6", ["some unmapped action"])
    assert alerts == []
