"""Batch-1 security fixes: history-leak guard, key rotation, WhatsApp fail-closed
signature, and the importer's SSRF guard."""

import pytest

from app import db, import_service
from app.config import get_settings

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}


# ── /chat/history no longer leaks WhatsApp transcripts ───────────────────────
def test_history_refuses_whatsapp_conversation_ids(client):
    """wa-<phone> ids are guessable, so the public history route must 404 them
    even when the conversation exists."""
    db.save_message("bright-smile", "wa-971501234567", "user", "my results?")
    db.save_message("bright-smile", "wa-971501234567", "model", "Let me check.")
    r = client.get("/chat/history?business_id=bright-smile&conversation_id=wa-971501234567")
    assert r.status_code == 404
    # A normal widget token still works.
    db.save_message("bright-smile", "web-abcdef12", "user", "hi")
    ok = client.get("/chat/history?business_id=bright-smile&conversation_id=web-abcdef12")
    assert ok.status_code == 200 and ok.json()[0]["text"] == "hi"


# ── admin key rotation (the leaked-key recovery path) ────────────────────────
def test_rotate_key_revokes_the_old_and_issues_a_new(client):
    r = client.post("/admin/businesses/bright-smile/rotate-key", headers=ADMIN)
    assert r.status_code == 200
    new_key = r.json()["api_key"]
    assert new_key.startswith("bizkey_") and new_key != "bizkey_bright_smile_demo"
    # The OLD (committed, leaked) key no longer opens the tenant's data...
    assert client.get("/bookings?business_id=bright-smile", headers=BRIGHT).status_code == 403
    # ...and the new one does.
    assert client.get("/bookings?business_id=bright-smile",
                      headers={"X-API-Key": new_key}).status_code == 200


def test_rotate_key_is_admin_only_and_404s_unknown(client):
    assert client.post("/admin/businesses/bright-smile/rotate-key").status_code == 401
    assert client.post("/admin/businesses/bright-smile/rotate-key", headers=BRIGHT).status_code == 401
    assert client.post("/admin/businesses/ghost-biz/rotate-key", headers=ADMIN).status_code == 404


# ── WhatsApp webhook fails closed without an app secret ──────────────────────
def test_webhook_refuses_to_process_without_app_secret(client, monkeypatch):
    """A live channel (access token set) but no app secret must 503, not trust
    unsigned traffic."""
    monkeypatch.setattr(get_settings(), "whatsapp_access_token", "token123")
    monkeypatch.setattr(get_settings(), "whatsapp_app_secret", "")
    r = client.post("/whatsapp/webhook", json={"entry": []})
    assert r.status_code == 503


# ── importer SSRF guard ──────────────────────────────────────────────────────
def test_guard_blocks_internal_addresses():
    for bad in (
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://localhost:8000/",
        "file:///etc/passwd",
        "ftp://example.com/x",
    ):
        with pytest.raises(ValueError):
            import_service._guard_public_url(bad)


def test_guard_allows_public_hosts():
    # A well-known public IP literal passes (no DNS needed).
    import_service._guard_public_url("https://8.8.8.8/")


def test_fetch_raw_refuses_private_before_any_network(monkeypatch):
    """The guard runs BEFORE the socket opens — a blocked URL never touches the
    network."""
    def _explode(*a, **k):
        raise AssertionError("must not open a connection for a blocked URL")

    monkeypatch.setattr(import_service._SSRF_OPENER, "open", _explode)
    with pytest.raises(ValueError):
        import_service._fetch_raw("http://10.0.0.5/internal")
