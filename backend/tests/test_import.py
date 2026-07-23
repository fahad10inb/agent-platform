"""Website auto-import: URL in, review-ready onboarding prefill out —
clamped to form bounds, admin-gated, friendly on failure."""

import pytest

from app import import_service

ADMIN = {"X-API-Key": "admin_test_key"}


@pytest.fixture
def fake_site(monkeypatch):
    monkeypatch.setattr(import_service, "_fetch_text", lambda url: "The Fade Lab " * 20)

    async def _fake_extract(text):
        return {
            "name": "The Fade Lab", "type": "mens grooming studio", "vertical": "salon",
            "tone": "sharp and friendly", "hours": "Sat-Thu 10am-10pm",
            "open_hour": 10, "close_hour": 22,
            "services": "fades, beard sculpting", "staff": "Marwan - fades",
            "location": "Al Barsha 1", "policies": "walk-ins welcome", "faq": "fade 80 AED",
        }

    monkeypatch.setattr(import_service, "_extract", _fake_extract)


def test_import_returns_review_ready_prefill(client, fake_site):
    r = client.post("/onboarding/import", json={"url": "https://fadelab.ae"}, headers=ADMIN)
    assert r.status_code == 200
    d = r.json()
    assert d["name"] == "The Fade Lab" and d["vertical"] == "salon" and d["open_hour"] == 10


def test_import_is_admin_only(client, fake_site):
    assert client.post("/onboarding/import", json={"url": "https://x.ae"}).status_code == 401


def test_import_failure_is_friendly(client, monkeypatch):
    def _dead(url):
        raise OSError("no such host")

    monkeypatch.setattr(import_service, "_fetch_text", _dead)
    r = client.post("/onboarding/import", json={"url": "https://nope.example"}, headers=ADMIN)
    assert r.status_code == 422
    assert "double-check" in r.json()["detail"]


def test_description_mode_skips_the_fetch(client, fake_site, monkeypatch):
    """No website? Rough notes go through the same extractor — and we must
    never try to fetch anything."""
    def _no_fetch(url):
        raise AssertionError("fetch must not happen in description mode")

    monkeypatch.setattr(import_service, "_fetch_text", _no_fetch)
    r = client.post(
        "/onboarding/import",
        json={"description": "Barbershop in Karama, fades 60 AED, barbers Tony and Ali, open 10am-10pm"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "The Fade Lab"  # fake extractor's output


def test_import_requires_url_or_description(client):
    r = client.post("/onboarding/import", json={}, headers=ADMIN)
    assert r.status_code == 422


def test_clamp_forces_form_bounds():
    wild = {"name": "x" * 999, "vertical": "spaceship", "open_hour": 99, "close_hour": -3}
    out = import_service._clamp(wild)
    assert len(out["name"]) == 120
    assert out["vertical"] == "general"
    assert 0 <= out["open_hour"] < out["close_hour"] <= 24


def test_clamp_keeps_the_real_estate_profile_fields():
    """_clamp filters output to a fixed key list; the four RE fields were missing,
    so website-import silently blanked areas/focus/languages/ORN."""
    from app.import_service import _clamp
    out = _clamp({
        "name": "X", "type": "real estate agency", "vertical": "real_estate",
        "areas_covered": "JVC, Marina", "deal_focus": "Sale + rent",
        "languages": "English, Arabic", "orn": "28154",
    })
    assert out["areas_covered"] == "JVC, Marina"
    assert out["deal_focus"] == "Sale + rent"
    assert out["languages"] == "English, Arabic"
    assert out["orn"] == "28154"
