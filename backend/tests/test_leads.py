"""Lead capture: dedup is enforced by the DATABASE layer, not the model's
manners — the same phone re-captured is one evolving lead, never two rows."""

from app import db, notify_service
from app.tools.leads_tools import make_lead_tools


def _capture(business_id="skyline-realty"):
    return make_lead_tools(business_id)[0]


def test_same_phone_updates_instead_of_duplicating(client):
    capture = _capture()
    first = capture("Fahad", "123456790", "1.5M budget, Jumeirah")
    assert first["status"] == "captured"

    second = capture("Fahad", "123 456 790", "buy in Jumeirah, 1.5M", notes="ready soon")
    assert second["status"] == "updated"
    assert second["lead_id"] == first["lead_id"]

    rows = db.list_leads("skyline-realty")
    assert len(rows) == 1
    assert rows[0]["interest"] == "buy in Jumeirah, 1.5M"  # newest picture wins
    assert "ready soon" in rows[0]["notes"]


def test_different_phone_is_a_new_lead(client):
    capture = _capture()
    capture("Fahad", "123456790", "buy in Jumeirah")
    capture("Sara", "0509998888", "rent in Marina")
    assert len(db.list_leads("skyline-realty")) == 2


def test_leads_stay_scoped_per_business(client):
    _capture("skyline-realty")("Fahad", "123456790", "buy in Jumeirah")
    other = _capture("bright-smile")("Fahad", "123456790", "whitening quote")
    # Same phone at ANOTHER business is that business's own fresh lead.
    assert other["status"] == "captured"
    assert len(db.list_leads("bright-smile")) == 1


def test_owner_notified_once_not_on_updates(client, monkeypatch):
    sent = []
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: sent.append(a))
    capture = _capture()
    capture("Fahad", "123456790", "1.5M budget")
    capture("Fahad", "123456790", "buy in Jumeirah, 1.5M")
    assert len(sent) == 1  # one enquiry, one email — no duplicate pings
