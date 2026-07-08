"""The owner's Conversations inbox: list threads (web + WhatsApp), read a
thread — authenticated, so unlike public /chat/history it CAN show wa-* threads,
but only for the owning tenant."""

from app import db

BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}
ADMIN = {"X-API-Key": "admin_test_key"}
VELVET = {"X-API-Key": "bizkey_velvet_hair_demo"}


def _seed():
    db.save_message("bright-smile", "web-abc12345", "user", "hi there")
    db.save_message("bright-smile", "web-abc12345", "model", "Hello! How can I help?")
    db.save_message("bright-smile", "wa-971501234567", "user", "is 4pm free?")
    db.save_message("bright-smile", "wa-971501234567", "model", "Yes — shall I book it?")


def test_inbox_lists_conversations_newest_first(client):
    _seed()
    r = client.get("/manage/bright-smile/conversations", headers=BRIGHT)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    # The WhatsApp thread moved most recently → it's first, with a preview.
    assert rows[0]["conversation_id"] == "wa-971501234567"
    assert rows[0]["messages"] == 2 and "book it" in rows[0]["last_text"]


def test_inbox_shows_a_whatsapp_thread_to_the_authenticated_owner(client):
    _seed()
    r = client.get("/manage/bright-smile/conversations/wa-971501234567", headers=BRIGHT)
    assert r.status_code == 200
    thread = r.json()
    assert [t["role"] for t in thread] == ["user", "model"]
    assert thread[0]["text"] == "is 4pm free?"


def test_inbox_needs_auth_and_is_tenant_scoped(client):
    _seed()
    # No key → 401.
    assert client.get("/manage/bright-smile/conversations").status_code == 401
    # Another tenant's key → 403 (can't read bright-smile's inbox).
    assert client.get("/manage/bright-smile/conversations", headers=VELVET).status_code == 403
    assert client.get("/manage/bright-smile/conversations/wa-971501234567",
                      headers=VELVET).status_code == 403
    # Admin can (it opens any business).
    assert client.get("/manage/bright-smile/conversations", headers=ADMIN).status_code == 200


def test_public_history_still_hides_whatsapp_threads(client):
    """The inbox is authenticated; the PUBLIC /chat/history must still 404 a
    wa-* thread so a guessable phone-number id can't leak a transcript."""
    _seed()
    assert client.get(
        "/chat/history?business_id=bright-smile&conversation_id=wa-971501234567"
    ).status_code == 404
