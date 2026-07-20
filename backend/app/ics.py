"""
iCalendar (RFC 5545) output — how a booking gets into the owner's real calendar.

The honest alternative to a Google Calendar OAuth integration. Google's OAuth for
the Calendar scope is a *sensitive* scope: an unverified app sits in "Testing",
where refresh tokens expire after ~7 days (a pilot would die in week two), and
escaping that needs Google verification — a verified domain, a privacy policy, a
demo video, and a multi-week review we don't control.

An .ics file needs none of that and works with EVERY calendar:
  • one booking  → a downloadable invite the owner taps once (instant)
  • all bookings → a token-gated feed URL they paste into Google Calendar
                   ("Other calendars → From URL"), which then keeps itself
                   updated. NOTE: Google polls external feeds slowly (hours), so
                   the per-booking invite is what makes a fresh viewing appear
                   immediately. The feed is the set-and-forget backstop.

Times: bookings are stored as a Dubai date + a slot label ("4:00 PM"). Dubai is
UTC+4 with no DST, so we emit plain UTC (…Z) — the most portable form there is.
"""

import datetime
import hashlib
import zoneinfo

from app.tools.calendar_tools import _norm_time

_DUBAI = zoneinfo.ZoneInfo("Asia/Dubai")
_DEFAULT_MINUTES = 60


def _escape(text: str) -> str:
    """RFC 5545 text escaping — a raw comma or semicolon corrupts the field."""
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """RFC 5545 caps a line at 75 octets; longer lines continue with a leading
    space. Strict parsers (Outlook) reject unfolded long lines."""
    if len(line) <= 73:
        return line
    out, rest = [line[:73]], line[73:]
    while rest:
        out.append(" " + rest[:72])
        rest = rest[72:]
    return "\r\n".join(out)


def _start_utc(date: str, time_label: str) -> datetime.datetime | None:
    """A booking's Dubai date + slot label as an aware UTC datetime, or None if
    either is unparseable (a bad row must never break the whole feed)."""
    try:
        day = datetime.date.fromisoformat((date or "").strip())
    except ValueError:
        return None
    label = _norm_time(time_label or "")
    try:
        clock = datetime.datetime.strptime(label, "%I:%M %p").time()
    except ValueError:
        return None
    local = datetime.datetime.combine(day, clock, tzinfo=_DUBAI)
    return local.astimezone(datetime.timezone.utc)


def _stamp(dt: datetime.datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _uid(business_id: str, booking: dict) -> str:
    """Stable per-booking UID. It must NOT change between feed reads, or the
    calendar shows the same viewing twice. Prefer the row id; fall back to a hash
    of the slot so a row without an id is still stable."""
    bid = booking.get("id")
    if bid:
        return f"booking-{bid}@receptionai"
    seed = f"{business_id}|{booking.get('date')}|{booking.get('time')}|{booking.get('patient_name')}"
    return f"booking-{hashlib.sha1(seed.encode()).hexdigest()[:16]}@receptionai"


def _minutes(business: dict) -> int:
    slot = business.get("slot_minutes")
    return slot if isinstance(slot, int) and 5 <= slot <= 480 else _DEFAULT_MINUTES


def _event(business: dict, booking: dict, now: datetime.datetime) -> list[str]:
    """One VEVENT, or [] when the booking can't be placed on a clock."""
    start = _start_utc(booking.get("date"), booking.get("time"))
    if start is None:
        return []
    end = start + datetime.timedelta(minutes=_minutes(business))
    who = (booking.get("patient_name") or "Customer").strip()
    reason = (booking.get("reason") or "").strip()
    phone = (booking.get("phone") or "").strip()
    cancelled = (booking.get("status") or "booked") == "cancelled"

    # Plain ASCII hyphen, not an em-dash: a fancy dash renders as mojibake ("â")
    # in any calendar app that opens the downloaded file as Latin-1 instead of UTF-8.
    title = f"{who} - {reason}" if reason else who
    desc_bits = [f"Booked by your AI receptionist ({business.get('name') or business.get('id')})."]
    if phone:
        desc_bits.append(f"Phone: {phone}")
    if reason:
        desc_bits.append(f"Reason: {reason}")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{_uid(business.get('id', ''), booking)}",
        f"DTSTAMP:{_stamp(now)}",
        f"DTSTART:{_stamp(start)}",
        f"DTEND:{_stamp(end)}",
        _fold(f"SUMMARY:{_escape(title)}"),
        _fold(f"DESCRIPTION:{_escape(' '.join(desc_bits))}"),
    ]
    location = (business.get("location") or "").strip()
    if location:
        lines.append(_fold(f"LOCATION:{_escape(location)}"))
    # A cancelled booking must be CANCELLED in the feed, not silently dropped —
    # dropping it leaves a ghost viewing sitting in the owner's calendar.
    lines.append("STATUS:CANCELLED" if cancelled else "STATUS:CONFIRMED")
    lines.append("END:VEVENT")
    return lines


def build_ics(business: dict, bookings: list[dict], now: datetime.datetime | None = None) -> str:
    """A complete VCALENDAR for these bookings. Used for both the single-booking
    invite (one row) and the subscribable feed (all rows)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    name = business.get("name") or business.get("id") or "ReceptionAI"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ReceptionAI//Bookings//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        _fold(f"X-WR-CALNAME:{_escape(name)} - bookings"),
        "X-WR-TIMEZONE:Asia/Dubai",
        # Ask subscribers to re-poll hourly. Google treats this as a hint only.
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for booking in bookings or []:
        lines.extend(_event(business, booking, now))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
