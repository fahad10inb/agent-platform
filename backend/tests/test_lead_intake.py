"""Portal lead-intake: parsing the portal emails, the instant-response ingest
(capture + owner alert + outreach + conversation seed), and the token-gated
endpoint."""

from app import db, lead_intake, notify_service, whatsapp
from app.config import get_settings

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}

_BAYUT_EMAIL = """You have a new lead from Bayut.

Name: Ahmed Khan
Mobile: +971 50 987 6543
Email: ahmed.k@example.com
Reference: BY-4421
Message: Interested in the 2BR in JVC, can I view this week?

Sent via bayut.com
"""


# ── parsing ──────────────────────────────────────────────────────────────────
def test_parses_a_bayut_lead_email():
    lead = lead_intake.parse_portal_lead("New lead from Bayut", _BAYUT_EMAIL)
    assert lead["source"] == "Bayut"
    assert lead["name"] == "Ahmed Khan"
    assert lead["phone"] == "+971 50 987 6543"
    assert lead["email"] == "ahmed.k@example.com"
    assert lead["property_ref"] == "BY-4421"
    assert "JVC" in lead["message"]


def test_detects_property_finder_and_dubizzle():
    assert lead_intake.detect_source("Enquiry via Property Finder") == "Property Finder"
    assert lead_intake.detect_source("A dubizzle enquiry") == "Dubizzle"
    assert lead_intake.detect_source("some random newsletter") == "unknown"


def test_falls_back_to_regex_when_unlabelled():
    body = "Hi, call me on 0501112233 about the villa, thanks"
    lead = lead_intake.parse_portal_lead("website enquiry", body)
    assert lead["phone"] == "0501112233"


def test_no_contact_details_is_not_a_lead():
    assert lead_intake.parse_portal_lead("Newsletter", "Market report attached, no reply needed") is None


def test_ignores_the_portal_noreply_sender():
    body = "Name: Sara\nMessage: interested\nSent by noreply@bayut.com to you"
    lead = lead_intake.parse_portal_lead("lead", body)
    # A phone-less lead still needs SOME contact; the no-reply address is skipped,
    # so with no human email/phone this isn't a usable lead.
    assert lead is None


# ── ingest = capture + alert + instant outreach ──────────────────────────────
def test_ingest_captures_alerts_and_reaches_out(client, monkeypatch):
    sent, alerts = [], []

    async def _fake_send(phone_id, to, text):
        sent.append((phone_id, to, text))

    monkeypatch.setattr(whatsapp, "_send_text", _fake_send)
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: alerts.append(a))
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "token123")
    db.update_business_settings("skyline-realty", {"whatsapp_phone_id": "PID-RE"})

    parsed = lead_intake.parse_portal_lead("New lead from Bayut", _BAYUT_EMAIL)
    out = lead_intake.ingest_lead(db.get_business("skyline-realty"), parsed)

    assert out["status"] == "captured" and out["reached_out"] is True
    # Lead saved with source + interest.
    lead = db.list_leads("skyline-realty")[0]
    assert lead["phone"] == "+971 50 987 6543" and "Bayut" in lead["notes"]
    # Owner alerted once, instantly.
    assert len(alerts) == 1
    # The lead was messaged on the normalized WhatsApp number, and the opener
    # was seeded into that thread so their reply qualifies naturally.
    assert sent and sent[0][1] == "971509876543"
    history = db.get_history("skyline-realty", "wa-971509876543")
    assert history and history[-1]["role"] == "model" and "budget" in history[-1]["text"].lower()


def test_ingest_dedupes_a_re_notified_lead(client, monkeypatch):
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: None)
    parsed = lead_intake.parse_portal_lead("New lead from Bayut", _BAYUT_EMAIL)
    first = lead_intake.ingest_lead(db.get_business("skyline-realty"), parsed)
    second = lead_intake.ingest_lead(db.get_business("skyline-realty"), parsed)
    assert first["status"] == "captured" and second["status"] == "updated"
    assert len(db.list_leads("skyline-realty")) == 1  # one lead, not two


# ── the endpoint ─────────────────────────────────────────────────────────────
def test_ingest_endpoint_is_token_routed(client, monkeypatch):
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: None)
    # Admin mints the token; only admin can.
    assert client.post("/admin/businesses/skyline-realty/ingest-token").status_code == 401
    r = client.post("/admin/businesses/skyline-realty/ingest-token", headers=ADMIN)
    token = r.json()["lead_ingest_token"]

    ok = client.post("/leads/ingest", json={"token": token, "subject": "New lead from Bayut",
                                            "body": _BAYUT_EMAIL})
    assert ok.status_code == 200 and ok.json()["status"] == "captured"
    assert db.list_leads("skyline-realty")[0]["phone"] == "+971 50 987 6543"


def test_ingest_endpoint_rejects_unknown_token(client):
    r = client.post("/leads/ingest", json={"token": "lead_totally-wrong", "body": _BAYUT_EMAIL})
    assert r.status_code == 404  # same as a wrong token — no business enumeration


def test_ingest_endpoint_ignores_a_contactless_forward(client):
    r = client.post("/admin/businesses/skyline-realty/ingest-token", headers=ADMIN)
    token = r.json()["lead_ingest_token"]
    out = client.post("/leads/ingest", json={"token": token, "body": "just a market report, no contact"})
    assert out.status_code == 200 and out.json()["status"] == "ignored"
