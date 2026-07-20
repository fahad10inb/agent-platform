"""Real-estate agency profile — the fields that let the AI understand WHO the
agency is (areas covered, sale/rent/off-plan focus, languages, RERA ORN). They
must reach the system prompt and round-trip through onboarding + settings, so the
agent answers area questions honestly and can state the agency's registration."""

from app import db
from app.prompt_service import build_system_prompt

ADMIN = {"X-API-Key": "admin_test_key"}


def test_profile_facts_land_in_the_prompt():
    p = build_system_prompt({
        "name": "Skyline", "type": "real estate agency", "vertical": "real_estate",
        "areas_covered": "JVC, Dubai Marina, Downtown",
        "deal_focus": "Secondary sales and rentals, plus off-plan",
        "languages": "English, Arabic",
        "orn": "28154",
    })
    assert "JVC" in p and "Dubai Marina" in p
    assert "Secondary sales" in p
    assert "English, Arabic" in p
    assert "28154" in p and "ORN" in p


def test_absent_profile_adds_nothing():
    # A business with no profile filled in must not sprout empty ORN/area lines.
    p = build_system_prompt({"name": "X", "type": "clinic", "vertical": "clinic"})
    assert "ORN" not in p
    assert "communities this agency covers" not in p


def test_onboarding_round_trips_the_profile(client):
    r = client.post("/admin/businesses", headers=ADMIN, json={
        "id": "prof-co", "name": "Prof Co", "type": "real estate agency",
        "vertical": "real_estate",
        "areas_covered": "Palm Jumeirah, Emirates Hills",
        "deal_focus": "Luxury sales",
        "languages": "English, Russian",
        "orn": "99001",
    })
    assert r.status_code == 200
    b = db.get_business("prof-co")
    assert b["areas_covered"] == "Palm Jumeirah, Emirates Hills"
    assert b["deal_focus"] == "Luxury sales"
    assert b["languages"] == "English, Russian"
    assert b["orn"] == "99001"


def test_manage_get_hands_the_profile_back_to_the_form(client):
    # The settings form AND the owner's-view profile card read from GET /manage.
    # The AI can store the fields all day; if the API whitelist doesn't return
    # them, the owner's view shows an empty card. (This exact gap shipped once.)
    client.post("/manage/skyline-realty", headers=ADMIN, json={
        "areas_covered": "Palm Jumeirah, Marina", "deal_focus": "Rentals",
        "languages": "English", "orn": "55555",
    })
    out = client.get("/manage/skyline-realty", headers=ADMIN).json()
    assert out["areas_covered"] == "Palm Jumeirah, Marina"
    assert out["deal_focus"] == "Rentals"
    assert out["languages"] == "English"
    assert out["orn"] == "55555"


def test_settings_update_edits_the_profile_and_reaches_the_prompt(client):
    r = client.post("/manage/skyline-realty", headers=ADMIN,
                    json={"areas_covered": "JVC only", "orn": "12345"})
    assert r.status_code == 200
    b = db.get_business("skyline-realty")
    assert b["areas_covered"] == "JVC only"
    assert b["orn"] == "12345"
    # The edit must be live for the very next conversation.
    p = build_system_prompt(b)
    assert "JVC only" in p and "12345" in p
