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


def test_empty_with_no_tool_activity_retries_then_recovers(monkeypatch):
    """No tools ran, so retrying the whole turn is side-effect-free: one clean
    retry first; if that is ALSO blank, the tools-off recovery; if everything
    stays blank, "" — the /chat route's last-resort line takes over, never a 500."""
    calls: list = []
    responses = [
        SimpleNamespace(text="", automatic_function_calling_history=None),
        SimpleNamespace(text="", automatic_function_calling_history=None),
        SimpleNamespace(text=""),
    ]
    monkeypatch.setattr(llm_service, "_get_client", lambda: _fake_client(responses, calls))

    reply = asyncio.run(llm_service.generate_reply("be warm", [{"role": "user", "text": "hi"}]))

    assert reply == ""
    assert len(calls) == 3


def test_leaked_tool_call_text_never_reaches_the_caller(monkeypatch):
    """The Fahad bug, part 2: the whole reply is `recall_caller(caller_name='fahad')`
    — typed, not executed. Nothing ran, so the turn is retried cleanly."""
    calls: list = []
    responses = [
        SimpleNamespace(text="recall_caller(caller_name='fahad')", automatic_function_calling_history=None),
        SimpleNamespace(text="Nice to meet you, Fahad! What's the best number to reach you on?"),
    ]
    monkeypatch.setattr(llm_service, "_get_client", lambda: _fake_client(responses, calls))

    def recall_caller():
        pass

    reply = asyncio.run(
        llm_service.generate_reply("be warm", [{"role": "user", "text": "name is fahad"}], tools=[recall_caller])
    )

    assert reply.startswith("Nice to meet you")
    assert len(calls) == 2


def test_leak_detector_only_flags_bare_tool_syntax():
    names = {"recall_caller", "capture_lead"}
    assert llm_service._looks_like_leaked_tool_call("recall_caller(caller_name='x')", names)
    assert llm_service._looks_like_leaked_tool_call("`capture_lead(name='A', phone='050')`", names)
    assert llm_service._looks_like_leaked_tool_call("print(recall_caller(caller_name='x'))", names)
    # Normal prose — even prose that mentions saving details — is untouched.
    assert not llm_service._looks_like_leaked_tool_call("I've saved your details!", names)
    assert not llm_service._looks_like_leaked_tool_call("We can call you back today.", names)


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
