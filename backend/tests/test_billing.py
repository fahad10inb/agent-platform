"""Batch-3 billing/ops floor: the monthly quota fuse (graceful decline + one
owner notice), the admin plan endpoint, the PDPL forget-caller erasure, and the
request-id header."""

from app import chat_core, db, notify_service

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}


def _spy_model(monkeypatch):
    """Replace the LLM with a counter so we can prove it is / isn't called."""
    calls = {"n": 0}

    async def _fake(system_prompt, history, tools=None):
        calls["n"] += 1
        return "ok"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    return calls


# ── the quota fuse ───────────────────────────────────────────────────────────
def test_over_quota_declines_gracefully_without_calling_the_model(client, monkeypatch):
    calls = _spy_model(monkeypatch)
    notices = []
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: notices.append(a))

    client.post("/admin/businesses/bright-smile/plan",
                json={"plan": "starter", "monthly_msg_quota": 5}, headers=ADMIN)
    for _ in range(5):
        db.bump_usage("bright-smile")

    r = client.post("/chat", json={"message": "hi", "conversation_id": "web-q0001", "business_id": "bright-smile"})
    assert r.status_code == 200
    assert "can't take new messages" in r.json()["reply"].lower()
    assert calls["n"] == 0  # the model was never called — no Gemini spend past the cap
    assert len(notices) == 1  # owner emailed exactly once

    # A second over-quota turn still declines but does NOT email again.
    client.post("/chat", json={"message": "still there?", "conversation_id": "web-q0002", "business_id": "bright-smile"})
    assert len(notices) == 1


def test_approaching_quota_warns_once_but_keeps_answering(client, monkeypatch):
    calls = _spy_model(monkeypatch)
    notices = []
    monkeypatch.setattr(notify_service, "notify_owner", lambda *a, **k: notices.append(a))

    client.post("/admin/businesses/bright-smile/plan",
                json={"plan": "starter", "monthly_msg_quota": 10}, headers=ADMIN)
    for _ in range(8):  # 80%
        db.bump_usage("bright-smile")

    r = client.post("/chat", json={"message": "hi", "conversation_id": "web-a0001", "business_id": "bright-smile"})
    assert r.json()["reply"] == "ok"  # still answering
    assert calls["n"] == 1
    assert len(notices) == 1  # the heads-up email, once


def test_uncapped_business_always_answers(client, monkeypatch):
    calls = _spy_model(monkeypatch)
    for _ in range(1000):
        db.bump_usage("bright-smile")  # no plan set → quota is NULL → uncapped
    r = client.post("/chat", json={"message": "hi", "conversation_id": "web-u0001", "business_id": "bright-smile"})
    assert r.json()["reply"] == "ok"
    assert calls["n"] == 1


# ── the admin plan endpoint ──────────────────────────────────────────────────
def test_set_plan_is_admin_only(client):
    body = {"plan": "starter", "monthly_msg_quota": 100}
    assert client.post("/admin/businesses/bright-smile/plan", json=body).status_code == 401
    assert client.post("/admin/businesses/bright-smile/plan", json=body, headers=BRIGHT).status_code == 401
    assert client.post("/admin/businesses/ghost/plan", json=body, headers=ADMIN).status_code == 404
    assert client.post("/admin/businesses/bright-smile/plan", json=body, headers=ADMIN).status_code == 200


def test_tenant_cannot_raise_its_own_quota(client):
    """The quota is admin-only: a tenant's /manage save must never carry it."""
    client.post("/admin/businesses/bright-smile/plan",
                json={"plan": "starter", "monthly_msg_quota": 5}, headers=ADMIN)
    # Even if a tenant POSTs monthly_msg_quota, the settings model drops it.
    client.post("/manage/bright-smile", json={"name": "Bright Smile", "monthly_msg_quota": 999999},
                headers=BRIGHT)
    assert db.get_business("bright-smile")["monthly_msg_quota"] == 5


# ── PDPL forget-caller ───────────────────────────────────────────────────────
def test_forget_caller_erases_every_table(client):
    db.save_booking("bright-smile", "2026-09-01", "9:00 AM", "Sara", "0501234567", "cleaning")
    db.save_lead("bright-smile", "Sara", "0501234567", "whitening quote")
    # Real WhatsApp threads are keyed wa-<E.164>, and erasure must match it even
    # when the admin types a different format ("050 123 4567").
    db.save_message("bright-smile", "wa-971501234567", "user", "hi")
    db.save_caller_memory("bright-smile", "Sara", "prefers mornings")

    r = client.post("/admin/forget-caller",
                    json={"business_id": "bright-smile", "phone": "050 123 4567", "name": "Sara"},
                    headers=ADMIN)
    assert r.status_code == 200
    d = r.json()["deleted"]
    assert d["bookings"] == 1 and d["leads"] == 1 and d["whatsapp_messages"] == 1 and d["caller_memory"] == 1
    assert db.list_leads("bright-smile") == []
    assert db.get_caller_memory("bright-smile", "Sara") == []


def test_forget_caller_needs_admin_and_an_identifier(client):
    assert client.post("/admin/forget-caller", json={"business_id": "bright-smile", "phone": "050"}).status_code == 401
    assert client.post("/admin/forget-caller", json={"business_id": "bright-smile"},
                       headers=ADMIN).status_code == 422  # neither phone nor name
    assert client.post("/admin/forget-caller", json={"business_id": "ghost", "phone": "050"},
                       headers=ADMIN).status_code == 404


# ── request id ───────────────────────────────────────────────────────────────
def test_every_response_carries_a_request_id(client):
    r = client.get("/health")
    assert r.headers.get("X-Request-ID")
