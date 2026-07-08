"""
Listings import — turn whatever a small agency already has (a Google Sheet /
CSV export, their portal XML feed, or the Reelly off-plan API) into our canonical
listing rows, keyed on the Trakheesi/Madhmoun permit number.

Field names vary wildly across CRMs and portals, so normalization maps a wide
set of aliases onto one schema: title, area, bedrooms, price, purpose,
permit_number, reference, notes. The permit_number is the compliance key
(module #5 hard-gates advertising on it) and the cross-source dedup key.
"""

import csv
import io
import json
import logging
import xml.etree.ElementTree as ET

from app.import_service import _fetch_raw  # SSRF-guarded fetch (private ranges blocked)

logger = logging.getLogger("agent-platform.listingimport")

# alias -> canonical field. Lower-cased, non-alnum stripped, on lookup.
_ALIASES = {
    "title": "title", "name": "title", "propertytitle": "title", "propertyname": "title",
    "area": "area", "community": "area", "location": "area", "subcommunity": "area", "city": "area",
    "bedrooms": "bedrooms", "beds": "bedrooms", "bed": "bedrooms", "br": "bedrooms", "bedroom": "bedrooms",
    "price": "price", "amount": "price", "rent": "price", "saleprice": "price", "askingprice": "price",
    "purpose": "purpose", "offeringtype": "purpose", "category": "purpose", "type": "purpose",
    "transactiontype": "purpose",
    "permitnumber": "permit_number", "permit": "permit_number", "trakheesi": "permit_number",
    "rerapermit": "permit_number", "madhmoun": "permit_number", "permitno": "permit_number",
    "dldpermit": "permit_number", "qrpermit": "permit_number",
    "reference": "reference", "ref": "reference", "refno": "reference", "referenceno": "reference",
    "propertyreference": "reference", "listingid": "reference", "id": "reference",
    "notes": "notes", "description": "notes", "remarks": "notes", "details": "notes",
}
_FIELDS = ("title", "area", "bedrooms", "price", "purpose", "permit_number", "reference", "notes")


def _canon_key(key: str) -> str:
    return "".join(ch for ch in (key or "").lower() if ch.isalnum())


def normalize_listing(raw: dict) -> dict | None:
    """One source record → our schema, or None if it has no title (not a listing)."""
    out = {f: "" for f in _FIELDS}
    for key, value in (raw or {}).items():
        field = _ALIASES.get(_canon_key(key))
        if field and not out[field] and value not in (None, ""):
            out[field] = str(value).strip()
    return out if out["title"] else None


def _normalize_many(rows: list[dict]) -> list[dict]:
    return [n for n in (normalize_listing(r) for r in rows) if n]


def parse_csv(text: str) -> list[dict]:
    """CSV (incl. a Google Sheet published as CSV) → normalized listings."""
    reader = csv.DictReader(io.StringIO(text))
    return _normalize_many(list(reader))


def parse_xml(text: str) -> list[dict]:
    """A property XML feed → normalized listings. Generic: every element that
    looks like a property/listing becomes a row from its child tags."""
    root = ET.fromstring(text)
    rows = []
    for el in root.iter():
        tag = _canon_key(el.tag)
        if tag not in ("property", "listing", "item"):
            continue
        record = {}
        for child in el:
            if child.text and child.text.strip():
                record[child.tag] = child.text.strip()
            # portal feeds often nest the permit under an attribute or sub-tag
            for k, v in (child.attrib or {}).items():
                record[f"{child.tag}_{k}"] = v
        if record:
            rows.append(record)
    return _normalize_many(rows)


def fetch_reelly(api_key: str, limit: int = 50) -> list[dict]:
    """Fetch off-plan projects from the Reelly API (token auth) → normalized.
    Reelly is the one genuinely open UAE listing data layer (free 20-project key)."""
    url = f"https://api.reelly.io/v1/properties?limit={int(limit)}"
    raw = _fetch_raw_authed(url, api_key)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ValueError("Reelly did not return JSON") from exc
    items = data.get("data") if isinstance(data, dict) else data
    return _normalize_many(items or [])


def _fetch_raw_authed(url: str, api_key: str) -> str:
    """SSRF-guarded GET with a bearer token (Reelly). Kept thin so tests patch it."""
    import urllib.request
    from app.import_service import _guard_public_url, _SSRF_OPENER

    _guard_public_url(url)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}",
                                               "User-Agent": "ReceptionAI listings"})
    with _SSRF_OPENER.open(req, timeout=15) as resp:
        return resp.read(2_000_000).decode("utf-8", "ignore")


def import_listings(fmt: str, *, data: str = "", url: str = "", api_key: str = "") -> list[dict]:
    """Dispatch to the right parser and return normalized listings (capped).
    `data` is pasted text; `url` is fetched (SSRF-guarded); `api_key` is Reelly."""
    fmt = (fmt or "").strip().lower()
    if fmt == "reelly":
        rows = fetch_reelly(api_key)
    else:
        text = data or (_fetch_raw(url) if url else "")
        if not text.strip():
            raise ValueError("no data to import")
        rows = parse_xml(text) if fmt == "xml" else parse_csv(text)
    if not rows:
        raise ValueError("no listings found in the import")
    return rows[:200]
