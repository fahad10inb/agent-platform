"""Admin WhatsApp diagnostics: check/fix whether a WhatsApp Business Account is
subscribed to this app (the thing that makes Meta deliver inbound messages).
The endpoints use the server's own token — here it's unset, so they report that
and never touch the network."""

ADMIN = {"X-API-Key": "admin_test_key"}


def test_whatsapp_status_needs_admin(client):
    assert client.get("/admin/whatsapp-status").status_code == 401
    assert client.post("/admin/whatsapp-subscribe?waba_id=x").status_code == 401


def test_reports_when_token_missing_without_network(client):
    # No WHATSAPP_ACCESS_TOKEN in the test env → both endpoints report it and
    # return before any Graph API call (so the suite makes no outbound request).
    r = client.get("/admin/whatsapp-status?waba_id=123", headers=ADMIN)
    assert r.status_code == 200 and "error" in r.json()
    r2 = client.post("/admin/whatsapp-subscribe?waba_id=123", headers=ADMIN)
    assert r2.status_code == 200 and "error" in r2.json()
