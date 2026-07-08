"""Test harness: swap the real Postgres layer for an in-memory fake BEFORE
app.main is imported (main runs init_db + seeding at import time), then expose
a TestClient. Same trick as the companion's fake_supabase — db.py is the single
storage seam, so faking that one module tests everything above it for real.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Settings are cached on first read — pin test env values before anything reads them.
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ADMIN_API_KEY", "admin_test_key")
os.environ.setdefault("DATABASE_URL", "postgresql://unused-in-tests")

import pytest  # noqa: E402

from app import db  # noqa: E402

# ── in-memory state, same shape the real tables hold ─────────────────────────
_S = {"businesses": {}, "bookings": [], "memory": [], "leads": [], "messages": [],
      "services": [], "listings": [], "usage": {}, "next_id": 1}


def _nid() -> int:
    _S["next_id"] += 1
    return _S["next_id"] - 1


def _fake_init_db():
    return None


def _fake_get_business(business_id):
    b = _S["businesses"].get(business_id)
    return dict(b) if b else None


def _fake_upsert_business(b):
    cur = _S["businesses"].get(b["id"], {})
    merged = {**cur, **b}
    if not merged.get("api_key"):
        merged["api_key"] = cur.get("api_key")
    _S["businesses"][b["id"]] = merged


def _fake_update_business_settings(business_id, fields):
    allowed = db._EDITABLE_BUSINESS_FIELDS
    if business_id in _S["businesses"]:
        _S["businesses"][business_id].update({k: v for k, v in fields.items() if k in allowed})


def _fake_list_businesses():
    return [{"id": b["id"], "name": b["name"], "type": b["type"]} for b in _S["businesses"].values()]


def _fake_save_booking(business_id, date, time, patient_name, phone="", reason=""):
    # The real layer enforces UNIQUE (business_id, date, time) — mirror it.
    for r in _S["bookings"]:
        if (r["business_id"], r["date"], r["time"]) == (business_id, date, time):
            return None
    row = {
        "id": _nid(), "business_id": business_id, "date": date, "time": time,
        "patient_name": patient_name, "phone": phone, "reason": reason,
    }
    _S["bookings"].append(row)
    return row["id"]


def _fake_list_bookings(business_id, limit=100, offset=0):
    rows = [dict(r) for r in reversed(_S["bookings"]) if r["business_id"] == business_id]
    return rows[offset:offset + limit]


def _fake_save_message(business_id, conversation_id, role, text):
    _S["messages"].append(
        {"business_id": business_id, "conversation_id": conversation_id, "role": role, "text": text}
    )


def _fake_count_user_messages(business_id, conversation_id):
    return sum(1 for m in _S["messages"]
               if m["business_id"] == business_id and m["conversation_id"] == conversation_id
               and m["role"] == "user")


def _fake_get_history(business_id, conversation_id, limit=40):
    rows = [
        {"role": m["role"], "text": m["text"]}
        for m in _S["messages"]
        if m["business_id"] == business_id and m["conversation_id"] == conversation_id
    ]
    return rows[-limit:]


def _fake_bump_usage(business_id, messages=1):
    _S["usage"][business_id] = _S["usage"].get(business_id, 0) + messages


def _user_msgs_per_conversation(business_id):
    """user-message counts per conversation — the fair-billing rule's raw data."""
    per_conv = {}
    for m in _S["messages"]:
        if m["business_id"] == business_id and m["role"] == "user":
            per_conv[m["conversation_id"]] = per_conv.get(m["conversation_id"], 0) + 1
    return per_conv


def _fake_get_metrics(business_id):
    # Mirrors the real layer's fair-billing rule: a conversation counts only
    # once the caller sent a SECOND message; messages stay raw. The fake has no
    # timestamps, so "today" and "30d" see the same window.
    per_conv = _user_msgs_per_conversation(business_id)
    engaged = sum(1 for n in per_conv.values() if n >= 2)
    return {
        "conversations_today": engaged,
        "conversations_30d": engaged,
        "messages_30d": sum(per_conv.values()),
        "bookings_30d": sum(1 for b in _S["bookings"] if b["business_id"] == business_id),
        "leads_30d": sum(1 for r in _S["leads"] if r["business_id"] == business_id),
    }


def _fake_get_week_stats(business_id):
    # Same >=2-user-message rule as get_metrics; everything counts as "this week".
    per_conv = _user_msgs_per_conversation(business_id)
    return {
        "conversations_7d": sum(1 for n in per_conv.values() if n >= 2),
        "messages_7d": sum(per_conv.values()),
        "bookings_7d": sum(1 for b in _S["bookings"] if b["business_id"] == business_id),
        "leads_7d": sum(1 for r in _S["leads"] if r["business_id"] == business_id),
    }


def _fake_set_last_digest(business_id):
    if business_id in _S["businesses"]:
        _S["businesses"][business_id]["last_digest_at"] = datetime.datetime.now(
            datetime.timezone.utc
        )


def _fake_list_businesses_full():
    return [
        {"id": b["id"], "name": b["name"], "notify_email": b.get("notify_email"),
         "last_digest_at": b.get("last_digest_at")}
        for b in _S["businesses"].values()
    ]


def _fake_get_usage(business_id, days=30):
    n = _S["usage"].get(business_id, 0)
    return [{"day": "today", "messages": n}] if n else []


def _fake_get_month_usage(business_id):
    return _S["usage"].get(business_id, 0)


def _fake_claim_quota_notice(business_id, month):
    b = _S["businesses"].get(business_id)
    if b is None or b.get("quota_notice_month") == month:
        return False
    b["quota_notice_month"] = month
    return True


def _digits(s):
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _fake_forget_caller(business_id, phone="", name=""):
    counts = {}
    digits = _digits(phone)
    if digits:
        before = len(_S["bookings"])
        _S["bookings"][:] = [r for r in _S["bookings"]
                             if not (r["business_id"] == business_id and _digits(r.get("phone")) == digits)]
        counts["bookings"] = before - len(_S["bookings"])
        before = len(_S["leads"])
        _S["leads"][:] = [r for r in _S["leads"]
                          if not (r["business_id"] == business_id and _digits(r.get("phone")) == digits)]
        counts["leads"] = before - len(_S["leads"])
        before = len(_S["messages"])
        _S["messages"][:] = [m for m in _S["messages"]
                             if not (m["business_id"] == business_id and m["conversation_id"] == f"wa-{digits}")]
        counts["whatsapp_messages"] = before - len(_S["messages"])
    if name:
        key = db._norm(name)
        before = len(_S["memory"])
        _S["memory"][:] = [m for m in _S["memory"]
                           if not (m["business_id"] == business_id and m["caller"] == key)]
        counts["caller_memory"] = before - len(_S["memory"])
    return counts


def _fake_booked_times(business_id, date):
    return [r["time"] for r in _S["bookings"] if r["business_id"] == business_id and r["date"] == date]


def _fake_find_bookings(business_id, patient_name):
    name = (patient_name or "").strip().lower()
    return [
        {"id": r["id"], "date": r["date"], "time": r["time"],
         "patient_name": r["patient_name"], "phone": r["phone"]}
        for r in _S["bookings"]
        if r["business_id"] == business_id and r["patient_name"].lower() == name
    ]


def _fake_cancel_booking(business_id, patient_name, date, time):
    name = (patient_name or "").strip().lower()
    before = len(_S["bookings"])
    _S["bookings"][:] = [
        r for r in _S["bookings"]
        if not (r["business_id"] == business_id and r["patient_name"].lower() == name
                and r["date"] == date and r["time"] == time)
    ]
    return len(_S["bookings"]) < before


def _fake_reschedule_booking(business_id, patient_name, old_date, old_time, new_date, new_time):
    for r in _S["bookings"]:
        if (r["business_id"], r["date"], r["time"]) == (business_id, new_date, new_time):
            return None  # unique index would reject
    name = (patient_name or "").strip().lower()
    for r in _S["bookings"]:
        if (r["business_id"] == business_id and r["patient_name"].lower() == name
                and r["date"] == old_date and r["time"] == old_time):
            r["date"], r["time"] = new_date, new_time
            return True
    return False


def _fake_save_caller_memory(business_id, name, note):
    _S["memory"].append({"business_id": business_id, "caller": db._norm(name), "note": note})


def _fake_get_caller_memory(business_id, name):
    key = db._norm(name)
    return [m["note"] for m in _S["memory"] if m["business_id"] == business_id and m["caller"] == key]


def _fake_replace_caller_memory(business_id, name, notes):
    # The real layer does DELETE + INSERTs in one transaction; in memory that's
    # simply a filter-then-extend.
    key = db._norm(name)
    _S["memory"][:] = [
        m for m in _S["memory"] if not (m["business_id"] == business_id and m["caller"] == key)
    ]
    for note in notes:
        _S["memory"].append({"business_id": business_id, "caller": key, "note": note})


def _fake_bookings_with_times(business_id, date):
    return [
        {"time": r["time"], "reason": r["reason"]}
        for r in _S["bookings"]
        if r["business_id"] == business_id and r["date"] == date
    ]


def _fake_list_services(business_id):
    return [
        {k: s[k] for k in ("id", "name", "duration_min", "price", "category", "bookable")}
        for s in _S["services"]
        if s["business_id"] == business_id
    ]


def _fake_replace_services(business_id, services):
    # Real layer: DELETE + INSERTs in one transaction — here, filter then extend.
    _S["services"][:] = [s for s in _S["services"] if s["business_id"] != business_id]
    for s in services:
        _S["services"].append({
            "id": _nid(), "business_id": business_id, "name": s["name"],
            "duration_min": s["duration_min"], "price": s.get("price", ""),
            "category": s.get("category", ""), "bookable": s.get("bookable", True),
        })


def _fake_save_lead(business_id, name, phone, interest, notes=""):
    row = {"id": _nid(), "business_id": business_id, "name": name,
           "phone": phone, "interest": interest, "notes": notes}
    _S["leads"].append(row)
    return row["id"]


def _fake_list_leads(business_id, limit=100, offset=0):
    rows = [dict(r) for r in reversed(_S["leads"]) if r["business_id"] == business_id]
    return rows[offset:offset + limit]


def _fake_list_listings(business_id):
    return [dict(r) for r in _S["listings"] if r["business_id"] == business_id]


def _fake_replace_listings(business_id, listings):
    _S["listings"] = [r for r in _S["listings"] if r["business_id"] != business_id]
    for row in listings:
        _S["listings"].append({
            "id": _nid(), "business_id": business_id, "title": row["title"],
            "area": row.get("area", ""), "bedrooms": row.get("bedrooms", ""),
            "price": row.get("price", ""), "purpose": row.get("purpose", ""),
            "notes": row.get("notes", ""),
        })


def _fake_rotate_api_key(business_id, new_key):
    b = _S["businesses"].get(business_id)
    if b is None:
        return False
    b["api_key"] = new_key
    return True


def _fake_get_business_by_whatsapp(phone_number_id):
    if not phone_number_id:
        return None
    for b in _S["businesses"].values():
        if b.get("whatsapp_phone_id") == phone_number_id:
            return dict(b)
    return None


def _fake_find_recent_lead(business_id, phone, within_hours=48):
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    for r in reversed(_S["leads"]):  # newest first, like the SQL ORDER BY id DESC
        if r["business_id"] == business_id and "".join(ch for ch in r["phone"] if ch.isdigit()) == digits:
            return dict(r)
    return None


def _fake_update_lead(lead_id, interest, notes=""):
    for r in _S["leads"]:
        if r["id"] == lead_id:
            r["interest"], r["notes"] = interest, notes


# Swap the seam BEFORE app.main import (module scope: conftest loads first).
db.init_db = _fake_init_db
db.get_business = _fake_get_business
db.upsert_business = _fake_upsert_business
db.update_business_settings = _fake_update_business_settings
db.list_businesses = _fake_list_businesses
db.save_booking = _fake_save_booking
db.list_bookings = _fake_list_bookings
db.booked_times = _fake_booked_times
db.bookings_with_times = _fake_bookings_with_times
db.list_services = _fake_list_services
db.replace_services = _fake_replace_services
db.find_bookings = _fake_find_bookings
db.cancel_booking = _fake_cancel_booking
db.reschedule_booking = _fake_reschedule_booking
db.save_caller_memory = _fake_save_caller_memory
db.get_caller_memory = _fake_get_caller_memory
db.replace_caller_memory = _fake_replace_caller_memory
db.save_lead = _fake_save_lead
db.list_leads = _fake_list_leads
db.find_recent_lead = _fake_find_recent_lead
db.update_lead = _fake_update_lead
db.list_listings = _fake_list_listings
db.replace_listings = _fake_replace_listings
db.get_business_by_whatsapp = _fake_get_business_by_whatsapp
db.rotate_api_key = _fake_rotate_api_key
db.save_message = _fake_save_message
db.get_history = _fake_get_history
db.count_user_messages = _fake_count_user_messages
db.bump_usage = _fake_bump_usage
db.get_usage = _fake_get_usage
db.get_month_usage = _fake_get_month_usage
db.claim_quota_notice = _fake_claim_quota_notice
db.forget_caller = _fake_forget_caller
db.get_metrics = _fake_get_metrics
db.get_week_stats = _fake_get_week_stats
db.set_last_digest = _fake_set_last_digest
db.list_businesses_full = _fake_list_businesses_full

from app import main as main_module  # noqa: E402  (imports AFTER the swap)
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_state():
    """Fresh rows, conversations and rate-limit buckets per test; keep the
    seeded businesses."""
    from app import security

    _S["bookings"].clear()
    _S["memory"].clear()
    _S["leads"].clear()
    _S["messages"].clear()
    _S["services"].clear()
    _S["listings"].clear()
    _S["usage"].clear()
    # Reset each SEEDED business to its pristine seed values, so no per-test
    # mutation leaks into the next test — a changed name, a set notify_email, a
    # rotated api_key, a quota cap, a digest stamp all vanish. (Businesses a test
    # created via onboarding aren't seeds and are left as-is.)
    from app.businesses import SEED_BUSINESSES

    seed_by_id = {b["id"]: b for b in SEED_BUSINESSES}
    for bid in list(_S["businesses"]):
        if bid in seed_by_id:
            _S["businesses"][bid] = dict(seed_by_id[bid])
    security._hits.clear()
    yield


@pytest.fixture
def client():
    return TestClient(main_module.app)


@pytest.fixture
def state():
    return _S
