"""Lead qualification: A/B/C scoring, the qualify_lead tool (store + enrich the
owner's lead + CRM push), the CRM payload shaping, and real-estate gating."""

from app import chat_core, crm_service, db
from app.tools.qualify_tools import make_qualify_tools, score_lead, summarize


def _qualify(business_id="skyline-realty"):
    return make_qualify_tools({"id": business_id})[0]


# ── scoring ──────────────────────────────────────────────────────────────────
def test_scoring_tiers():
    # A: budget + area + urgency (>=4 points)
    assert score_lead({"budget": "1.5-2M", "area": "JVC", "timeline": "this month"})[0] == "A"
    # A: budget + area + ready financing
    assert score_lead({"budget": "1.5M", "area": "Marina", "pay_method": "cash"})[0] == "A"
    # B: budget + area but vague timeline / no financing (2 points)
    assert score_lead({"budget": "1.5M", "area": "JVC", "timeline": "just looking"})[0] == "B"
    # C: barely anything
    assert score_lead({"area": "somewhere"})[0] == "C"
    assert score_lead({})[0] == "C"


def test_summary_is_compact_and_scored():
    s = summarize({"budget": "1.5-2M", "area": "Dubai Marina", "bedrooms": "2",
                   "pay_method": "cash", "timeline": "this month"}, "A")
    assert s.startswith("[A] ") and "1.5-2M" in s and "Dubai Marina" in s and "cash" in s


# ── the qualify_lead tool ────────────────────────────────────────────────────
def test_qualify_stores_scores_and_enriches_the_lead(client, monkeypatch):
    pushes = []
    monkeypatch.setattr(crm_service, "push_lead", lambda biz, lead: pushes.append(lead))

    out = _qualify()("Rania", "0501234567", budget="1.8M", area="JVC",
                     bedrooms="2", timeline="this month", pay_method="cash")
    assert out["status"] == "qualified" and out["score"] == "A"

    # Stored qualification.
    q = db.get_qualification("skyline-realty", "0501234567")
    assert q["score"] == "A" and q["fields"]["area"] == "JVC"
    # The owner's Leads tab shows the scored summary.
    lead = db.list_leads("skyline-realty")[0]
    assert lead["interest"].startswith("[A]") and "JVC" in lead["interest"]
    # Pushed to CRM with the score.
    assert pushes and pushes[0]["score"] == "A"


def test_re_qualifying_same_phone_updates_not_duplicates(client, monkeypatch):
    monkeypatch.setattr(crm_service, "push_lead", lambda *a, **k: None)
    q = _qualify()
    q("Rania", "0501234567", budget="1.8M", area="JVC")               # B
    q("Rania", "0501234567", budget="1.8M", area="JVC", pay_method="cash")  # now A
    assert db.get_qualification("skyline-realty", "0501234567")["score"] == "A"
    assert len(db.list_leads("skyline-realty")) == 1  # one lead, updated


# ── CRM payload shaping ──────────────────────────────────────────────────────
def test_bitrix_payload_shape():
    target, body = crm_service._payload(
        "bitrix24", "https://acme.bitrix24.com/rest/1/tok/",
        {"name": "Rania", "phone": "0501234567", "score": "A", "summary": "[A] JVC", "source": "AI"},
    )
    import json
    assert target.endswith("/crm.lead.add.json")
    fields = json.loads(body)["fields"]
    assert fields["NAME"] == "Rania"
    assert fields["PHONE"][0]["VALUE"] == "0501234567"
    assert "A" in fields["TITLE"]


def test_generic_payload_is_the_raw_lead():
    target, body = crm_service._payload("", "https://hooks.zapier.com/x", {"name": "R", "score": "B"})
    import json
    assert target == "https://hooks.zapier.com/x"
    assert json.loads(body)["score"] == "B"


def test_push_lead_noops_without_a_webhook(client):
    # No crm_webhook_url on the business → nothing sent, no error.
    crm_service.push_lead({"id": "skyline-realty"}, {"name": "R", "phone": "05000"})


# ── vertical gating ──────────────────────────────────────────────────────────
def test_qualify_tool_only_for_real_estate(client, monkeypatch):
    seen = {}

    async def _fake(system_prompt, history, tools=None):
        seen["tools"] = [t.__name__ for t in (tools or [])]
        return "ok"

    monkeypatch.setattr(chat_core, "generate_reply", _fake)
    # skyline-realty is vertical real_estate → qualify_lead present.
    import asyncio
    asyncio.run(chat_core.run_turn("skyline-realty", "web-re01", "hi", lambda *a: None))
    assert "qualify_lead" in seen["tools"]
    # bright-smile is a clinic → no qualify_lead.
    asyncio.run(chat_core.run_turn("bright-smile", "web-cl01", "hi", lambda *a: None))
    assert "qualify_lead" not in seen["tools"]
