"""The auth matrix: every protected endpoint must deny by default, allow the
right key, and never let one tenant read another's data."""

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
VELVET = {"X-API-Key": "bizkey_velvet_hair_demo"}


def test_bookings_requires_key(client):
    assert client.get("/bookings?business_id=bright-smile").status_code == 401


def test_bookings_rejects_other_tenants_key(client):
    r = client.get("/bookings?business_id=bright-smile", headers=VELVET)
    assert r.status_code == 403


def test_bookings_allows_own_key_and_admin(client):
    assert client.get("/bookings?business_id=bright-smile", headers=BRIGHT).status_code == 200
    assert client.get("/bookings?business_id=bright-smile", headers=ADMIN).status_code == 200


def test_business_list_is_admin_only(client):
    assert client.get("/businesses").status_code == 401
    assert client.get("/businesses", headers=BRIGHT).status_code == 401
    assert client.get("/businesses", headers=ADMIN).status_code == 200


def test_manage_never_returns_the_api_key(client):
    r = client.get("/manage/bright-smile", headers=BRIGHT)
    assert r.status_code == 200
    assert "api_key" not in r.json()


def test_onboarding_is_admin_only_and_validates_slug(client):
    payload = {"id": "new-biz", "name": "New Biz", "type": "salon"}
    assert client.post("/admin/businesses", json=payload).status_code == 401
    bad = client.post("/admin/businesses", json={**payload, "id": "Bad Slug!"}, headers=ADMIN)
    assert bad.status_code == 422  # slug pattern rejects spaces/uppercase
    ok = client.post("/admin/businesses", json=payload, headers=ADMIN)
    assert ok.status_code == 200
    assert ok.json()["api_key"].startswith("bizkey_")
    dup = client.post("/admin/businesses", json=payload, headers=ADMIN)
    assert dup.status_code == 409


def test_settings_bounds_reject_hostile_values(client):
    # slot_minutes <= 0 used to hang slot generation in an infinite loop.
    r = client.post("/manage/bright-smile", json={"slot_minutes": -5}, headers=BRIGHT)
    assert r.status_code == 422
    r = client.post("/manage/bright-smile", json={"open_hour": 99}, headers=BRIGHT)
    assert r.status_code == 422


def test_seed_does_not_clobber_edits(client, state):
    """Re-running the seed loop must not revert a business's saved settings."""
    from app.businesses import SEED_BUSINESSES
    from app import db

    client.post("/manage/bright-smile", json={"tone": "very custom tone"}, headers=BRIGHT)
    for b in SEED_BUSINESSES:  # simulate a redeploy's startup seeding
        if db.get_business(b["id"]) is None:
            db.upsert_business(b)
    assert state["businesses"]["bright-smile"]["tone"] == "very custom tone"
