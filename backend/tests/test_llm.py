"""The empty-reply recovery: when Gemini's tool loop ends on a text-less turn
(tools ran, caller sees a blank bubble), ONE tools-off follow-up call shows the
model its own tool transcript and makes it speak — nothing may execute twice."""

import asyncio
from types import SimpleNamespace

from google.genai import types

from app import llm_service


def _fake_client(responses: list, calls: list):
    """A stand-in Gemini client: pops canned responses, records every call."""

    async def generate_content(*, model, contents, config):
        calls.append({"model": model, "contents": contents, "config": config})
        return responses.pop(0)

    return SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))


def _afc_history():
    """A realistic automatic-function-calling transcript: the model captured a
    lead and then went silent."""
    return [
        types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(
                name="capture_lead",
                args={"name": "Fahad", "phone": "123456790", "interest": "buy in Jumeirah, 1.5M"},
            ))],
        ),
        types.Content(
            role="user",
            parts=[types.Part(function_response=types.FunctionResponse(
                name="capture_lead", response={"status": "captured", "lead_id": 7},
            ))],
        ),
    ]


def test_empty_reply_recovers_with_the_tool_transcript(monkeypatch):
    calls: list = []
    responses = [
        SimpleNamespace(text="", automatic_function_calling_history=_afc_history()),
        SimpleNamespace(text="Done, Fahad — I've saved your details and an agent will call you today!"),
    ]
    monkeypatch.setattr(llm_service, "_get_client", lambda: _fake_client(responses, calls))

    reply = asyncio.run(llm_service.generate_reply("be warm", [{"role": "user", "text": "buy"}], tools=[lambda: None]))

    assert reply.startswith("Done, Fahad")
    assert len(calls) == 2
    # The recovery call must NOT be able to re-run tools...
    assert calls[1]["config"].tools is None
    # ...and must show the model what it actually did.
    note = calls[1]["contents"][-1].parts[0].text
    assert "capture_lead" in note and "Fahad" in note and "captured" in note


def test_recovery_failure_still_returns_empty_not_crash(monkeypatch):
    """If the follow-up ALSO comes back blank, generate_reply returns "" and the
    /chat route's generic last-resort line takes over — the turn never 500s."""
    calls: list = []
    responses = [
        SimpleNamespace(text="", automatic_function_calling_history=None),
        SimpleNamespace(text=""),
    ]
    monkeypatch.setattr(llm_service, "_get_client", lambda: _fake_client(responses, calls))

    reply = asyncio.run(llm_service.generate_reply("be warm", [{"role": "user", "text": "hi"}]))

    assert reply == ""
    assert len(calls) == 2


def test_nonempty_reply_never_triggers_a_second_call(monkeypatch):
    calls: list = []
    responses = [SimpleNamespace(text="Hello there!")]
    monkeypatch.setattr(llm_service, "_get_client", lambda: _fake_client(responses, calls))

    reply = asyncio.run(llm_service.generate_reply("be warm", [{"role": "user", "text": "hi"}]))

    assert reply == "Hello there!"
    assert len(calls) == 1


def test_tool_activity_lines_reads_the_afc_transcript():
    lines = llm_service._tool_activity_lines(
        SimpleNamespace(automatic_function_calling_history=_afc_history())
    )
    assert any("capture_lead" in line for line in lines)
    assert any("captured" in line for line in lines)
    # And a response with no transcript yields no lines (plain empty reply).
    assert llm_service._tool_activity_lines(SimpleNamespace(automatic_function_calling_history=None)) == []
