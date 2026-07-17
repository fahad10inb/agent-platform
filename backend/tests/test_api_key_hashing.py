"""API keys are stored HASHED, never in plaintext — a DB dump must not hand an
attacker a live tenant credential. Verification still accepts a legacy plaintext
row, so the switch can't lock out an existing business mid-migration."""

from app import db, security

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}


# ── the primitives ───────────────────────────────────────────────────────────
def test_hash_is_tagged_deterministic_and_not_the_plaintext():
    h = security.hash_key("bizkey_secret")
    assert h.startswith("sha256:") and "bizkey_secret" not in h
    assert h == security.hash_key("bizkey_secret")            # deterministic
    assert h != security.hash_key("bizkey_secret2")


def test_verify_accepts_hash_and_legacy_plaintext_but_nothing_else():
    h = security.hash_key("k1")
    assert security.verify_key("k1", h) is True               # hashed match
    assert security.verify_key("wrong", h) is False
    assert security.verify_key("k1", "k1") is True            # legacy plaintext match
    assert security.verify_key("k1", "k2") is False
    assert security.verify_key("", h) is False
    assert security.verify_key("k1", "") is False


# ── the live paths ───────────────────────────────────────────────────────────
def test_a_newly_onboarded_business_stores_the_hash_not_the_key(client):
    r = client.post("/admin/businesses", headers=ADMIN,
                    json={"id": "fresh-co", "name": "Fresh Co", "type": "salon"})
    assert r.status_code == 200
    plaintext = r.json()["api_key"]                            # shown once
    assert plaintext.startswith("bizkey_")

    # What's stored is the HASH, never the plaintext.
    stored = db.get_business("fresh-co")["api_key"]
    assert stored.startswith("sha256:") and stored != plaintext

    # …and the plaintext the owner was handed actually authenticates.
    assert client.get("/manage/fresh-co", headers={"X-API-Key": plaintext}).status_code == 200
    assert client.get("/manage/fresh-co", headers={"X-API-Key": "bizkey_wrong"}).status_code == 403


def test_rotation_stores_the_hash_and_the_old_key_dies(client):
    client.post("/admin/businesses", headers=ADMIN,
                json={"id": "rot-co", "name": "Rot Co", "type": "salon"})
    first = client.post("/admin/businesses/rot-co/rotate-key", headers=ADMIN).json()["api_key"]
    assert client.get("/manage/rot-co", headers={"X-API-Key": first}).status_code == 200

    second = client.post("/admin/businesses/rot-co/rotate-key", headers=ADMIN).json()["api_key"]
    assert db.get_business("rot-co")["api_key"].startswith("sha256:")
    assert client.get("/manage/rot-co", headers={"X-API-Key": second}).status_code == 200
    assert client.get("/manage/rot-co", headers={"X-API-Key": first}).status_code == 403   # revoked


def test_a_legacy_plaintext_seed_key_still_authenticates(client):
    """The seeded demo tenants carry plaintext keys (they predate hashing). The
    legacy branch of verify_key must keep them working, or the migration would
    lock out every existing business."""
    assert (db.get_business("bright-smile")["api_key"] or "").startswith("bizkey_")  # plaintext
    assert client.get("/manage/bright-smile", headers=BRIGHT).status_code == 200
