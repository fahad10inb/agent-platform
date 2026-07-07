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


class _LinkExtractor(HTMLParser):
    """Collect internal <a href> targets so we can crawl the pages that
    actually hold the good stuff (prices live on /services, not /)."""

    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.hrefs.append(v)


# The pages worth following, in any language we serve (crawl4ai/Firecrawl's
# lesson: score links by intent keywords instead of crawling blindly).
_LINK_KEYWORDS = ("service", "price", "pricing", "menu", "about", "contact",
                  "book", "team", "staff", "location", "hours", "treatment",
                  "خدمات", "اسعار", "أسعار", "حجز", "تواصل")


def _fetch_raw(url: str) -> str:
    """One bounded, time-limited page fetch."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ReceptionAI onboarding importer)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read(400_000).decode("utf-8", "ignore")


def _strip(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return " ".join(p.parts)


def _fetch_text(url: str) -> str:
    """Gather LLM-ready text for a site (runs in a thread).

    Three-layer strategy borrowed from the current OSS extraction stacks:
      1. homepage text,
      2. + up to 3 internal pages whose links look like services/prices/about
         (that's where the real answers live),
      3. if everything came back thin (JS-rendered sites), fall back to the
         Jina Reader proxy (r.jina.ai), which renders the page server-side and
         returns clean markdown — no key needed.
    """
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    base = re.match(r"^(https?://[^/]+)", url, re.IGNORECASE).group(1)

    text = ""
    try:
        home = _fetch_raw(url)
        text = _strip(home)
        # Score internal links by intent keywords; follow the best few.
        links = _LinkExtractor()
        links.feed(home)
        seen, picked = set(), []
        for href in links.hrefs:
            full = href if href.startswith("http") else base + ("" if href.startswith("/") else "/") + href
            if not full.startswith(base) or full.rstrip("/") in seen:
                continue
            seen.add(full.rstrip("/"))
            if any(k in full.lower() for k in _LINK_KEYWORDS):
                picked.append(full)
            if len(picked) >= 3:
                break
        for page in picked:
            try:
                text += "\n\n" + _strip(_fetch_raw(page))
            except Exception:  # noqa: BLE001 — a broken subpage shouldn't sink the import
                continue
    except Exception:  # noqa: BLE001 — homepage fetch failed; the fallback may still work
        pass

    if len(text.strip()) < 200:
        # JS-heavy site (or blocked) — let Jina Reader render it for us.
        try:
            text = _fetch_raw("https://r.jina.ai/" + url)
            logger.info("[import] used jina reader fallback for %s", url)
        except Exception:  # noqa: BLE001
            pass
    return text[:24_000]


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


# Native structured output: the model is CONSTRAINED to this schema by the API
# itself (the Dify/agent-stack standard) — malformed or fenced JSON simply
# can't happen, unlike prompt-and-pray extraction.
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "vertical": {"type": "string", "enum": ["salon", "clinic", "real_estate", "general"]},
        "tone": {"type": "string"},
        "hours": {"type": "string"},
        "open_hour": {"type": "integer"},
        "close_hour": {"type": "integer"},
        "services": {"type": "string"},
        "staff": {"type": "string"},
        "location": {"type": "string"},
        "policies": {"type": "string"},
        "faq": {"type": "string"},
    },
    "required": ["name", "type", "vertical"],
}


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
            response_mime_type="application/json",
            response_schema=_SCHEMA,
        ),
    )
    raw = (response.text or "").strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()  # belt-and-suspenders
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


async def import_from_website(url: str = "", description: str = "") -> dict:
    """URL and/or plain-text description in → review-ready onboarding prefill
    out. The description path covers the many small businesses with NO website:
    the admin pastes rough notes ("barbershop in Karama, fades 60, Tony and
    Ali, open 10-10") and the same extractor fills the form. Raises on
    unreachable/thin input (the route turns that into a friendly 422)."""
    text = (description or "").strip()
    if url and len(text) < 40:
        text = await asyncio.to_thread(_fetch_text, url)
    if len(text) < 40:
        raise ValueError("no readable text to extract from")
    data = _clamp(await _extract(text))
    logger.info("[import] extracted prefill (source=%s, name=%r)",
                "description" if description.strip() else url, data.get("name"))
    return data
