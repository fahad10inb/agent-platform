"""
The AI brain — a thin wrapper around Google's Gemini API.

One job: given a system prompt (the AI's instructions) and a user message,
return the AI's reply as text. Keeping ALL "talk to the model" code in this one
place means the rest of the app never has to know how the SDK works — if we ever
swap models or providers, we change only this file.
"""

from functools import lru_cache

from google import genai
from google.genai import types

from app.config import get_settings

# The chat model. Flash is fast and cheap — right for a snappy receptionist.
_MODEL = "gemini-2.5-flash"


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

    response = await _get_client().aio.models.generate_content(
        model=_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,  # a little warmth/variety; 0 = robotic, 1 = wilder
            tools=tools,  # None = no tools; a list = the AI may call them
        ),
    )
    return (response.text or "").strip()
