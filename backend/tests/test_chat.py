"""The chat pipeline: tenant isolation of conversation history (the worst bug
the review found), history capping, rollback on failure, and input bounds."""

import pytest

from app import main as main_module


@pytest.fixture
def fake_llm(monkeypatch):
    """Stub Gemini; records the history each call received."""
    calls = []

    async def _fake(system_prompt, history, tools=None):
        calls.append([dict(t) for t in history])
        return "ok"

    monkeypatch.setattr(main_module, "generate_reply", _fake)
    return calls


def test_same_conversation_id_never_bleeds_across_businesses(client, fake_llm):
    client.post("/chat", json={"message": "my dental secret", "conversation_id": "shared", "business_id": "bright-smile"})
    client.post("/chat", json={"message": "hello salon", "conversation_id": "shared", "business_id": "velvet-hair"})
    # The salon's model call must contain ONLY the salon's message.
    salon_history = fake_llm[1]
    texts = " ".join(t["text"] for t in salon_history)
    assert "dental secret" not in texts
    assert "hello salon" in texts


def test_unknown_business_is_404(client, fake_llm):
    r = client.post("/chat", json={"message": "hi", "business_id": "nope"})
    assert r.status_code == 404


def test_message_bounds(client, fake_llm):
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 5000}).status_code == 422


def test_history_is_capped(client, fake_llm):
    key = "bright-smile:long"
    main_module._conversations[key] = [{"role": "user", "text": f"t{i}"} for i in range(100)]
    r = client.post("/chat", json={"message": "latest", "conversation_id": "long", "business_id": "bright-smile"})
    assert r.status_code == 200
    # Trimmed to the cap (40) at send time, +1 for the model reply appended after.
    assert len(main_module._conversations[key]) <= 41
    assert main_module._conversations[key][-2]["text"] == "latest"


def test_failed_turn_is_rolled_back(client, monkeypatch):
    async def _boom(system_prompt, history, tools=None):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(main_module, "generate_reply", _boom)
    r = client.post("/chat", json={"message": "hi", "conversation_id": "c1", "business_id": "bright-smile"})
    assert r.status_code == 500
    # The unanswered user turn must not haunt the next request's context.
    assert main_module._conversations["bright-smile:c1"] == []


def test_production_errors_hide_internals(client, monkeypatch):
    async def _boom(system_prompt, history, tools=None):
        raise RuntimeError("SECRET_DB_PASSWORD in traceback")

    monkeypatch.setattr(main_module, "generate_reply", _boom)
    monkeypatch.setattr(main_module.settings, "environment", "production")
    r = client.post("/chat", json={"message": "hi", "business_id": "bright-smile"})
    assert r.status_code == 500
    assert "SECRET_DB_PASSWORD" not in r.text
