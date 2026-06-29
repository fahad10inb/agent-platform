"""
Scheduling tools — built per request, BOUND to one business.

Now a REAL (if simple) calendar owned by our own database:
  • slots are generated from the business's open/close hours + slot length,
  • times already booked are subtracted, so we only offer FREE slots,
  • booking refuses a slot that's already taken (no double-booking).

Still a closure factory (make_calendar_tools) so each tool acts only on its own
business's data without the AI ever handling the business_id.
"""

from app import db


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

    def check_availability(date: str) -> dict:
        """Check which appointment times are still FREE on a given date.

        Args:
            date: The day to check, as a concrete date (e.g. "2026-07-01").

        Returns:
            A dict with the date and the list of free time slots.
        """
        taken = set(db.booked_times(business_id, date))
        free = [s for s in _all_slots(open_hour, close_hour, slot_minutes) if s not in taken]
        print(f"  TOOL -> check_availability(date={date!r}) [biz={business_id}] free={len(free)}")
        return {"date": date, "available_slots": free}

    def book_appointment(date: str, time: str, patient_name: str) -> dict:
        """Book an appointment in a specific slot, if it's still free.

        Only call this once you know all three details — ask for any missing first.

        Args:
            date: The day of the appointment (a concrete date like "2026-07-01").
            time: The exact slot (must match an available one, e.g. "2:00 PM").
            patient_name: The caller's full name.

        Returns:
            A confirmation dict, or status "unavailable" if that slot is taken.
        """
        if time in set(db.booked_times(business_id, date)):
            print(f"  TOOL -> book_appointment DENIED (taken) date={date!r} time={time!r} [biz={business_id}]")
            return {"status": "unavailable", "reason": f"{time} on {date} is already booked", "date": date, "time": time}

        print(f"  TOOL -> book_appointment(date={date!r}, time={time!r}, name={patient_name!r}) [biz={business_id}]")
        booking_id = db.save_booking(business_id, date, time, patient_name)
        return {
            "status": "confirmed",
            "booking_id": booking_id,
            "date": date,
            "time": time,
            "patient_name": patient_name,
        }

    return [check_availability, book_appointment]
