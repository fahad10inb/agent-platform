"""
The AI brain — a thin wrapper around Google's Gemini API.

One job: given a system prompt (the AI's instructions) and a user message,
return the AI's reply as text. Keeping ALL "talk to the model" code in this one
place means the rest of the app never has to know how the SDK works — if we ever
swap models or providers, we change only this file.
"""

import asyncio
import logging
import re
from functools import lru_cache

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger("agent-platform.llm")


@lru_cache
def _get_client() -> genai.Client:
    """Create the Gemini client once (it holds the API key + connection).

    Done lazily (only on the first real call) so the server can still START
    even if the key isn't set yet — you only hit the error when you actually
    try to chat, with a clear message telling you what to fix.
    """
    key = get_settings().gemini_api_key
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and put your Gemini API key in it."
        )
    return genai.Client(api_key=key)


async def generate_reply(
    system_prompt: str,
    history: list[dict],
    tools: list | None = None,
) -> str:
    """Send the WHOLE conversation + instructions to Gemini; return the reply.

    `history` is the conversation so far: a list of {"role": "user"|"model",
    "text": "..."} turns, oldest first. Sending all of it (not just the latest
    line) is what gives the AI memory — it can see what was said earlier and
    follow up naturally.

    `await` because the network call is slow. `.aio` is the SDK's async client.

    `tools` is an optional list of plain Python functions the AI may call. When
    provided, the SDK runs the whole "agent loop" automatically (call → run your
    function → feed result back → final answer), so the text we return already
    accounts for any tool results.
    """
    # Convert our simple {role, text} turns into the SDK's Content objects.
    # The SDK uses "user" for the person and "model" for the AI.
    contents = [
        types.Content(
            role="user" if turn["role"] == "user" else "model",
            parts=[types.Part(text=turn["text"])],
        )
        for turn in history
    ]

    settings = get_settings()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        # A little warmth/variety; 0 = robotic, 1 = wilder. Env-tunable so the
        # voice can be dialed on Render without a deploy.
        temperature=settings.gemini_temperature,
        # A receptionist reply is a couple of sentences — cap the output so a
        # runaway generation can't produce (and bill) an essay.
        max_output_tokens=settings.gemini_max_output_tokens,
        tools=tools,  # None = no tools; a list = the AI may call them
    )

    # TODO(cost): Gemini's Batch API / "flex" service tiers promise ~50% off for
    # latency-tolerant work (the distill/consolidate passes qualify; chat never
    # will). NOT wired up yet because our pinned google-genai SDK's support for
    # them is unverified — verify the SDK surface first, then route background
    # calls through it.
    # Resilience: a hard timeout (a hung upstream call must not hold the caller
    # hostage) and ONE retry on transient failure (blip-shaped errors are common;
    # systematic ones will fail twice and surface properly). Retrying with tools
    # is safe: the destructive tools are idempotent under retry (booking twice
    # hits the unique slot index → "unavailable"; a second cancel → "not_found").
    tool_names = {getattr(t, "__name__", "") for t in (tools or [])} - {""}
    last_exc: Exception | None = None
    for attempt in (1, 2):
        try:
            response = await asyncio.wait_for(
                _get_client().aio.models.generate_content(
                    model=settings.gemini_model,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.llm_timeout_seconds,
            )
            text = (response.text or "").strip()
            leaked = bool(text) and _looks_like_leaked_tool_call(text, tool_names)
            if text and not leaked:
                return text
            # Two model failure shapes land here: a TEXT-LESS turn (tools ran —
            # a lead was saved, a slot was booked — but the caller would get a
            # blank bubble) and a LEAKED turn (the model TYPED its tool call,
            # `capture_lead(name='X')`, instead of executing it). If tools DID
            # run, a blind retry would re-run them — a second book_appointment
            # hits its own booking and reports "unavailable" — so we make one
            # follow-up call that shows the model its own tool transcript and
            # demands a reply, with tools DISABLED so nothing executes twice.
            # If nothing ran, a clean retry is side-effect-free — just loop.
            activity = _tool_activity_lines(response)
            if not activity and attempt == 1:
                logger.warning(
                    "model returned %s with no tool activity — retrying the turn",
                    "leaked tool-call text" if leaked else "empty text",
                )
                continue
            return await _recover_empty_reply(
                response, contents, config, settings, leaked_text=text if leaked else None
            )
        except asyncio.TimeoutError as exc:
            last_exc = exc
            logger.warning("gemini call timed out (attempt %d/2, %ss)", attempt, settings.llm_timeout_seconds)
        except Exception as exc:  # transient 5xx/network — retry once
            last_exc = exc
            logger.warning("gemini call failed (attempt %d/2): %s", attempt, str(exc)[:200])
        if attempt == 1:
            await asyncio.sleep(0.6)
    raise last_exc if last_exc else RuntimeError("gemini call failed")


def _looks_like_leaked_tool_call(text: str, tool_names: set[str]) -> bool:
    """Gemini occasionally TYPES its tool call — the whole reply is literally
    `recall_caller(caller_name='fahad')` — instead of executing it. The caller
    must never see tool syntax, and nothing actually ran."""
    stripped = text.strip().strip("`").strip()
    return any(re.match(rf"(?:print\()?\s*{re.escape(n)}\s*\(", stripped) for n in tool_names)


def _tool_activity_lines(response) -> list[str]:
    """What the model actually DID this turn — every tool call and its result,
    scraped from the SDK's automatic-function-calling transcript."""
    lines: list[str] = []
    for content in getattr(response, "automatic_function_calling_history", None) or []:
        for part in getattr(content, "parts", None) or []:
            call = getattr(part, "function_call", None)
            if call is not None:
                lines.append(f"- you called {call.name}({dict(call.args or {})})")
            result = getattr(part, "function_response", None)
            if result is not None:
                lines.append(f"  it returned: {result.response}")
    return lines


async def _recover_empty_reply(response, contents, config, settings, leaked_text: str | None = None) -> str:
    """One tools-off follow-up call: tell the model what its tools already did
    and make it speak. Returns "" if this too fails — the /chat route keeps a
    generic last-resort line for that."""
    activity = _tool_activity_lines(response)
    if leaked_text:
        problem = (
            f'Your last turn was the literal text "{leaked_text}" — you TYPED a '
            "tool call instead of executing it, so nothing ran and the caller "
            "saw raw code. Never show tool syntax to a caller.\n"
        )
    else:
        problem = (
            "Your last turn produced no message text, so the caller is staring "
            "at a blank bubble.\n"
        )
    note = (
        "(SYSTEM NOTE — the caller never sees this. "
        + problem
        + ("This is what you actually did with your tools:\n" + "\n".join(activity) + "\n" if activity else "")
        + "Write your reply to the caller NOW. State plainly what you just did — "
        "do not redo it, do not contradict it, do not apologize — and ask the "
        "one question still needed, if any.)"
    )
    followup = list(contents) + [types.Content(role="user", parts=[types.Part(text=note)])]
    recovery_config = types.GenerateContentConfig(
        system_instruction=config.system_instruction,
        temperature=config.temperature,
        max_output_tokens=config.max_output_tokens,
        tools=None,  # nothing may execute twice
    )
    try:
        second = await asyncio.wait_for(
            _get_client().aio.models.generate_content(
                model=settings.gemini_model,
                contents=followup,
                config=recovery_config,
            ),
            timeout=settings.llm_timeout_seconds,
        )
        text = (second.text or "").strip()
        if text:
            logger.info("empty-reply recovery succeeded (%d tool steps)", len(activity))
        return text
    except Exception as exc:
        logger.warning("empty-reply recovery failed: %s", str(exc)[:200])
        return ""
