"""
Scheduling tools — built per request, BOUND to one business.

Now a REAL (if simple) calendar owned by our own database:
  • slots are generated from the business's open/close hours + slot length,
  • times already booked are subtracted, so we only offer FREE slots,
  • booking refuses a slot that's already taken (no double-booking).

Still a closure factory (make_calendar_tools) so each tool acts only on its own
business's data without the AI ever handling the business_id.
"""

import datetime
import re
import zoneinfo

from app import db, notify_service

_TZ = zoneinfo.ZoneInfo("Asia/Dubai")


def _now() -> datetime.datetime:
    """Dubai wall clock — a seam so tests can freeze time."""
    return datetime.datetime.now(_TZ)


def _label_to_minutes(label: str):
    """'2:00 PM' -> minutes since midnight (None if unparseable)."""
    m = re.match(r"^(\d{1,2}):(\d{2}) (AM|PM)$", label or "")
    if not m:
        return None
    h, mins, suffix = int(m.group(1)), int(m.group(2)), m.group(3)
    h = h % 12 + (12 if suffix == "PM" else 0)
    return h * 60 + mins


def _norm_time(t: str) -> str:
    """Canonicalize a caller-provided time to slot format: '2:00 pm', '2 PM' and
    '14:00' all become '2:00 PM'. Without this the taken-slot check compares raw
    strings, and a lowercase or 24-hour variant books a duplicate of a taken slot.
    Unparseable input comes back stripped so exact matches still work."""
    s = (t or "").strip().upper().replace(".", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$", s)
    if not m:
        return (t or "").strip()
    h, mins, suffix = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if h > 24 or mins > 59:
        return (t or "").strip()
    if suffix is None:  # 24-hour input like "14:00"
        suffix = "AM" if h < 12 or h == 24 else "PM"
        h = h % 12 or 12
    elif h > 12:  # "14:00 PM" — trust the 24-hour digits
        h -= 12
    elif h == 0:
        h = 12
    return f"{h}:{mins:02d} {suffix}"


def _all_slots(open_hour: int, close_hour: int, slot_minutes: int) -> list[str]:
    """Every bookable time between open and close, e.g. '9:00 AM', '9:30 AM' ..."""
    slots: list[str] = []
    minutes = open_hour * 60
    end = close_hour * 60
    while minutes < end:
        h, m = divmod(minutes, 60)
        suffix = "AM" if h < 12 else "PM"
        hour12 = h % 12 or 12  # 0 -> 12, 13 -> 1, etc.
        slots.append(f"{hour12}:{m:02d} {suffix}")
        minutes += slot_minutes
    return slots


def make_calendar_tools(business: dict) -> list:
    """Return [check_availability, book_appointment] bound to this business."""
    business_id = business["id"]
    open_hour = business.get("open_hour") or 9
    close_hour = business.get("close_hour") or 17
    slot_minutes = business.get("slot_minutes") or 30
    # Guard against bad stored values (rows may predate API validation): a
    # non-positive slot length makes slot generation loop forever, and inverted
    # hours produce an empty or nonsense day. Fall back to sane defaults.
    if slot_minutes <= 0:
        slot_minutes = 30
    if not (0 <= open_hour < close_hour <= 24):
        open_hour, close_hour = 9, 17
    # Booking hygiene (Fresha-style), with safe defaults for rows that predate
    # these settings: minimum notice stops "book 9:00 at 8:55", the advance
    # window stops far-future junk, buffer adds breathing room between slots.
    _mn = business.get("min_notice_hours")
    min_notice_h = 1 if _mn is None else max(0, _mn)
    max_advance_d = business.get("max_advance_days") or 60
    buffer_min = max(0, business.get("buffer_min") or 0)
    step = slot_minutes + buffer_min
    # Structured service menu (per-service durations). When a caller names a
    # menu service, ITS duration drives the slot grid instead of the global
    # slot_minutes — a 15-min beard trim and a 90-min color stop sharing one
    # one-size-fits-all grid. No menu rows = the old behavior, untouched.
    # Longest names first so "skin fade" wins over "fade" when a stored reason
    # mentions both (duration inference must be deterministic).
    services = sorted(
        db.list_services(business_id),
        key=lambda s: len((s.get("name") or "")),
        reverse=True,
    )

    def _find_service(name: str) -> dict | None:
        """The menu row whose name matches (case-insensitive), else None."""
        key = (name or "").strip().lower()
        if not key:
            return None
        for s in services:
            if (s.get("name") or "").strip().lower() == key:
                return s
        return None

    def _infer_duration(reason: str) -> int:
        """An EXISTING booking's length, recovered from the service its stored
        reason names (book_appointment writes the menu name into the reason for
        exactly this). Bookings that predate the menu — or never matched a
        service — fall back to the global slot length."""
        low = (reason or "").lower()
        for s in services:
            nm = (s.get("name") or "").strip().lower()
            if nm and nm in low:
                return s.get("duration_min") or slot_minutes
        return slot_minutes

    def _overlaps_existing(date: str, time_label: str, duration: int, exclude_time: str = "") -> bool:
        """True when [start, start+duration) would cut into ANY existing
        booking's [start, start+its-duration). With mixed durations a plain
        same-start check isn't enough: a new 90-min color starting 30 minutes
        before someone's trim — or a quick trim dropped into the middle of a
        color — must both be refused. `exclude_time` skips one booking (the one
        being MOVED by a reschedule, so it doesn't collide with itself)."""
        start = _label_to_minutes(time_label)
        if start is None:
            return False
        end = start + duration
        for r in db.bookings_with_times(business_id, date):
            if exclude_time and _norm_time(r.get("time") or "") == exclude_time:
                continue
            b_start = _label_to_minutes(r.get("time") or "")
            if b_start is None:
                continue
            b_end = b_start + _infer_duration(r.get("reason") or "")
            if start < b_end and b_start < end:
                return True
        return False

    def _date_check(date: str):
        """None if the date is bookable; else a human reason why not."""
        try:
            d = datetime.date.fromisoformat((date or "").strip())
        except ValueError:
            return None  # non-ISO input: let exact-match flows handle it
        today = _now().date()
        if d < today:
            return f"{date} has already passed"
        if d > today + datetime.timedelta(days=max_advance_d):
            return f"bookings open up to {max_advance_d} days ahead"
        return None

    def _too_soon(date: str, time_label: str) -> bool:
        """True when the slot starts inside the minimum-notice window."""
        try:
            d = datetime.date.fromisoformat((date or "").strip())
        except ValueError:
            return False
        mins = _label_to_minutes(time_label)
        if mins is None:
            return False
        slot_dt = datetime.datetime.combine(
            d, datetime.time(mins // 60, mins % 60), tzinfo=_TZ
        )
        return slot_dt < _now() + datetime.timedelta(hours=min_notice_h)

    def check_availability(date: str, service: str = "") -> dict:
        """Check which appointment times are still FREE on a given date.

        Args:
            date: The day to check, as a concrete date (e.g. "2026-07-01").
            service: The service the caller wants, exactly as it appears on the
                SERVICE MENU (optional — its duration shapes the offered times).

        Returns:
            A dict with the date and the list of free time slots.
        """
        why = _date_check(date)
        if why:
            print(f"  TOOL -> check_availability(date={date!r}) [biz={business_id}] refused: {why}")
            return {"date": date, "available_slots": [], "note": why}
        svc = _find_service(service)
        if services:
            # Menu math: the requested service's length sets both the grid step
            # and the overlap window; slots that would run past closing go too.
            duration = (svc.get("duration_min") if svc else None) or slot_minutes
            free = [
                s for s in _all_slots(open_hour, close_hour, duration + buffer_min)
                if (_label_to_minutes(s) or 0) + duration <= close_hour * 60
                and not _overlaps_existing(date, s, duration)
                and not _too_soon(date, s)
            ]
        else:
            taken = set(db.booked_times(business_id, date))
            free = [
                s for s in _all_slots(open_hour, close_hour, step)
                if s not in taken and not _too_soon(date, s)
            ]
        print(f"  TOOL -> check_availability(date={date!r}) [biz={business_id}] free={len(free)}")
        out = {"date": date, "available_slots": free}
        if svc:
            out["service"] = svc["name"]
            out["duration_min"] = svc["duration_min"]
        return out

    def book_appointment(
        date: str, time: str, patient_name: str, phone: str = "", reason: str = "",
        service: str = "",
    ) -> dict:
        """Book an appointment in a specific slot, if it's still free.

        Collect the caller's full name AND mobile number, and the reason for the
        visit, before booking (ask for whatever's missing). UAE clinics take all
        three. Date and time are required; phone/reason strongly preferred.

        Args:
            date: The day of the appointment (a concrete date like "2026-07-01").
            time: The exact slot (must match an available one, e.g. "2:00 PM").
            patient_name: The caller's full name.
            phone: The caller's mobile number.
            reason: The reason for the visit (e.g. "cleaning", "toothache").
            service: The service being booked, exactly as it appears on the
                SERVICE MENU (optional — it reserves that service's duration).

        Returns:
            A confirmation dict, or status "unavailable" if that slot is taken.
        """
        time = _norm_time(time)
        why = _date_check(date)
        if why:
            return {"status": "unavailable", "reason": why, "date": date, "time": time}
        if _too_soon(date, time):
            return {
                "status": "unavailable",
                "reason": f"we need at least {min_notice_h} hour(s) notice for bookings",
                "date": date, "time": time,
            }
        svc = _find_service(service)
        if svc:
            # The stored reason must name the menu service — that's how future
            # overlap checks recover this booking's true duration from the DB.
            if (svc["name"] or "").strip().lower() not in (reason or "").lower():
                reason = svc["name"] + (f" — {reason}" if (reason or "").strip() else "")
        if services:
            duration = (svc.get("duration_min") if svc else None) or slot_minutes
            if _overlaps_existing(date, time, duration):
                print(f"  TOOL -> book_appointment DENIED (overlap) date={date!r} time={time!r} [biz={business_id}]")
                return {"status": "unavailable", "reason": f"{time} on {date} is already booked", "date": date, "time": time}
        elif time in set(db.booked_times(business_id, date)):
            print(f"  TOOL -> book_appointment DENIED (taken) date={date!r} time={time!r} [biz={business_id}]")
            return {"status": "unavailable", "reason": f"{time} on {date} is already booked", "date": date, "time": time}

        # No PII (name/phone) in server logs — Render keeps them.
        print(f"  TOOL -> book_appointment(date={date!r}, time={time!r}) [biz={business_id}]")
        booking_id = db.save_booking(business_id, date, time, patient_name, phone, reason)
        if booking_id is None:
            # Two callers raced for the same slot; the DB's unique index kept
            # exactly one. Tell this caller it's taken.
            return {"status": "unavailable", "reason": f"{time} on {date} is already booked", "date": date, "time": time}
        # Automatic visit memory: the platform remembers every visit by itself,
        # so a returning caller is recognized even if the model never thought to
        # call remember_about_caller. Best-effort — a memory failure must never
        # break the booking that just succeeded.
        if reason:
            try:
                db.save_caller_memory(business_id, patient_name, f"came in for {reason} ({date})")
            except Exception:
                pass
        # The owner hears about it the moment it happens (fire-and-forget).
        notify_service.notify_owner(
            business_id,
            f"New booking: {patient_name} — {date} at {time}",
            f"{patient_name} booked {reason or 'an appointment'} for {date} at {time}.\n"
            f"Phone: {phone or '—'}\n\nBooked automatically by your AI receptionist.",
        )
        return {
            "status": "confirmed",
            "booking_id": booking_id,
            "date": date,
            "time": time,
            "patient_name": patient_name,
        }

    def find_my_appointments(patient_name: str, phone_last4: str = "") -> dict:
        """Look up a caller's existing appointments by name, after verifying
        their identity with the last 4 digits of the mobile number they booked with.

        Call this before cancelling or rescheduling. If it returns
        "verification_needed", ask the caller for their mobile number and call
        again with its last 4 digits — never guess.

        Args:
            patient_name: The caller's full name.
            phone_last4: Last 4 digits of the mobile number used when booking.

        Returns:
            A dict with their appointments (date + time), or verification_needed.
        """
        appts = db.find_bookings(business_id, patient_name)
        on_file = [(r.get("phone") or "") for r in appts if r.get("phone")]
        verified = bool(phone_last4) and any(p.endswith(phone_last4[-4:]) for p in on_file)
        print(f"  TOOL -> find_my_appointments [biz={business_id}] found={len(appts)} verified={verified}")
        if on_file and not verified:
            # Anti-IDOR: names are public knowledge; the number on file is not.
            return {
                "patient_name": patient_name,
                "status": "verification_needed",
                "message": "Ask the caller for the mobile number they booked with, then call again with its last 4 digits.",
            }
        return {
            "patient_name": patient_name,
            "appointments": [{"id": r["id"], "date": r["date"], "time": r["time"]} for r in appts],
        }

    def _verified(patient_name: str, phone_last4: str):
        """True = last-4 match; None = no phone on file (nothing to check);
        False = mismatch or not provided. Matching happens HERE — the stored
        number is never shown to the model or the caller."""
        on_file = [(r.get("phone") or "") for r in db.find_bookings(business_id, patient_name) if r.get("phone")]
        if not on_file:
            return None
        return bool(phone_last4) and any(p.endswith(phone_last4[-4:]) for p in on_file)

    _VERIFY_MSG = "Ask the caller for the mobile number they booked with, then retry with its last 4 digits."

    def cancel_appointment(patient_name: str, date: str, time: str, phone_last4: str = "") -> dict:
        """Cancel a caller's appointment. Confirm the exact date and time first,
        and verify identity with the last 4 digits of their booking mobile number.

        Args:
            patient_name: The caller's full name.
            date: The appointment's date.
            time: The appointment's time slot.
            phone_last4: Last 4 digits of the mobile number used when booking.

        Returns:
            A dict with status "cancelled", "not_found", or "verification_needed".
        """
        if _verified(patient_name, phone_last4) is False:
            return {"status": "verification_needed", "message": _VERIFY_MSG}
        time = _norm_time(time)
        ok = db.cancel_booking(business_id, patient_name, date, time)
        if ok:
            notify_service.notify_owner(
                business_id,
                f"Booking cancelled: {patient_name} — {date} at {time}",
                f"{patient_name} cancelled their {date} {time} appointment via the receptionist.",
            )
        print(f"  TOOL -> cancel_appointment({date!r}, {time!r}) [biz={business_id}] ok={ok}")
        return {"status": "cancelled" if ok else "not_found", "date": date, "time": time}

    def reschedule_appointment(
        patient_name: str, old_date: str, old_time: str, new_date: str, new_time: str,
        phone_last4: str = "",
    ) -> dict:
        """Move a caller's appointment to a new slot (the new slot must be free).
        Verify identity with the last 4 digits of their booking mobile number.

        Args:
            patient_name: The caller's full name.
            old_date: The current appointment date.
            old_time: The current appointment time.
            new_date: The desired new date.
            new_time: The desired new time.
            phone_last4: Last 4 digits of the mobile number used when booking.

        Returns:
            A dict with status "rescheduled", "unavailable" (new slot taken),
            "not_found", or "verification_needed".
        """
        if _verified(patient_name, phone_last4) is False:
            return {"status": "verification_needed", "message": _VERIFY_MSG}
        old_time, new_time = _norm_time(old_time), _norm_time(new_time)
        why = _date_check(new_date)
        if why:
            return {"status": "unavailable", "reason": why}
        if _too_soon(new_date, new_time):
            return {"status": "unavailable", "reason": f"we need at least {min_notice_h} hour(s) notice"}
        # The new slot must be free — using the SAME duration-aware overlap check
        # book_appointment uses (a plain same-start check let a rescheduled trim
        # drop into the middle of a 90-min colour). Recover the moved booking's
        # true length from its stored reason, and exclude it from the check when
        # it's moving within the same day so it can't collide with itself.
        if services:
            duration = slot_minutes
            for r in db.bookings_with_times(business_id, old_date):
                if _norm_time(r.get("time") or "") == old_time:
                    duration = _infer_duration(r.get("reason") or "")
                    break
            exclude = old_time if new_date == old_date else ""
            if _overlaps_existing(new_date, new_time, duration, exclude_time=exclude):
                print(f"  TOOL -> reschedule DENIED (overlap) [biz={business_id}]")
                return {"status": "unavailable", "reason": f"{new_time} on {new_date} is already booked"}
        elif new_time in set(db.booked_times(business_id, new_date)):
            print(f"  TOOL -> reschedule DENIED (new slot taken) [biz={business_id}]")
            return {"status": "unavailable", "reason": f"{new_time} on {new_date} is already booked"}
        ok = db.reschedule_booking(business_id, patient_name, old_date, old_time, new_date, new_time)
        print(
            f"  TOOL -> reschedule_appointment({old_date} {old_time} "
            f"-> {new_date} {new_time}) [biz={business_id}] ok={ok}"
        )
        if ok is None:  # new slot grabbed in the race window (unique index)
            return {"status": "unavailable", "reason": f"{new_time} on {new_date} is already booked"}
        return {"status": "rescheduled" if ok else "not_found", "new_date": new_date, "new_time": new_time}

    return [
        check_availability,
        book_appointment,
        find_my_appointments,
        cancel_appointment,
        reschedule_appointment,
    ]
