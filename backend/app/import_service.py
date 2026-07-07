"""Website auto-import — the "just give us your website" onboarding (the
single biggest UX gap vs competitors like Rosie: theirs starts from a URL,
ours started from a blank form).

Flow: fetch the business's homepage → strip it to readable text → one LLM call
fills our onboarding form as JSON. The result is ALWAYS returned as a prefill
for the human to review and edit — never applied blind, because websites lie,
menus go stale, and hours change.
"""

import asyncio
import json
import logging
import re
import urllib.request
from html.parser import HTMLParser

from google.genai import types

from app.config import get_settings
from app.llm_service import _get_client

logger = logging.getLogger("agent-platform.import")


class _TextExtractor(HTMLParser):
    """Boil HTML down to visible text (scripts/styles skipped)."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def _fetch_text(url: str) -> str:
    """Blocking fetch + text-strip (runs in a thread). Bounded read + timeout
    so a huge or hanging site can't stall onboarding."""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ReceptionAI onboarding importer)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read(400_000).decode("utf-8", "ignore")
    p = _TextExtractor()
    p.feed(raw)
    return " ".join(p.parts)[:15_000]


_EXTRACT_PROMPT = """You are filling an onboarding form for an AI receptionist from a business's website text.
Return STRICT JSON only (no markdown fences) with these keys — use "" for anything the text doesn't clearly state, never invent:
{
 "name": "business name",
 "type": "short business type, e.g. 'dental clinic', 'hair salon'",
 "vertical": "one of: salon | clinic | real_estate | general",
 "tone": "one line describing a fitting receptionist tone for this brand",
 "hours": "opening hours as customers should hear them, e.g. 'Mon-Sat 9am-9pm'",
 "open_hour": 9,
 "close_hour": 21,
 "services": "comma-separated services offered",
 "staff": "team members and specialties if named, e.g. 'Sara - color specialist'",
 "location": "address/area, landmarks, parking info",
 "policies": "booking/cancellation/payment policies if stated",
 "faq": "other useful facts: prices, insurance, offers, anything a caller might ask"
}
open_hour/close_hour are integers 0-24 (best guess from the stated hours; default 9 and 18 if unclear).
Keep every field CONCISE — faq under 120 words, everything else under 40 words. Total output must stay small.

WEBSITE TEXT:
"""


async def _extract(text: str) -> dict:
    """One low-temperature LLM pass turning site text into form JSON."""
    settings = get_settings()
    response = await _get_client().aio.models.generate_content(
        model=settings.gemini_model,
        contents=_EXTRACT_PROMPT + text,
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2000,
            # Gemini 2.5's hidden "thinking" tokens count AGAINST the output
            # budget — without this the JSON comes back truncated mid-string.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw = (response.text or "").strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


def _clamp(data: dict) -> dict:
    """Force the LLM's output inside the same bounds the form enforces, so the
    prefill can never itself be rejected by validation."""
    limits = {"name": 120, "type": 60, "tone": 200, "hours": 500, "services": 2000,
              "staff": 1000, "location": 500, "policies": 2000, "faq": 8000}
    out = {}
    for key, cap in limits.items():
        out[key] = str(data.get(key) or "")[:cap]
    vertical = str(data.get("vertical") or "general").strip().lower()
    out["vertical"] = vertical if vertical in ("salon", "clinic", "real_estate", "general") else "general"
    try:
        oh, ch = int(data.get("open_hour", 9)), int(data.get("close_hour", 18))
    except (TypeError, ValueError):
        oh, ch = 9, 18
    out["open_hour"] = min(max(oh, 0), 23)
    out["close_hour"] = min(max(ch, 1), 24)
    if out["close_hour"] <= out["open_hour"]:
        out["open_hour"], out["close_hour"] = 9, 18
    return out


async def import_from_website(url: str) -> dict:
    """URL in → review-ready onboarding prefill out. Raises on unreachable
    site or unparseable output (the route turns that into a friendly 422)."""
    text = await asyncio.to_thread(_fetch_text, url)
    if len(text) < 80:
        raise ValueError("page had no readable text")
    data = _clamp(await _extract(text))
    logger.info("[import] extracted prefill from %s (name=%r)", url, data.get("name"))
    return data
