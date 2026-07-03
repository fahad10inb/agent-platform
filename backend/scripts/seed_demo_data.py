"""Seed REALISTIC demo data for the 4 demo tenants, so the dashboard and the
agent's memory feel like a live business, not an empty shell.

Run:  cd backend && .venv/Scripts/python -m scripts.seed_demo_data
Idempotent: wipes ONLY the demo tenants' rows first, then reseeds. Never touches
any real (non-demo) business.
"""

import datetime
import zoneinfo

from app import db

TZ = zoneinfo.ZoneInfo("Asia/Dubai")
TODAY = datetime.datetime.now(TZ).date()
DEMO = ["bright-smile", "velvet-hair", "skyline-realty", "handy-home"]


def d(days: int) -> str:
    """A date N days from today (negative = past), as the YYYY-MM-DD the tools use."""
    return f"{TODAY + datetime.timedelta(days=days):%Y-%m-%d}"


def wipe():
    with db._connect() as conn:
        for t in ("bookings", "caller_memory", "leads"):
            conn.execute(f"DELETE FROM {t} WHERE business_id = ANY(%s)", (DEMO,))  # noqa: S608


def seed():
    # ── bright-smile (dental clinic) ─────────────────────────────────────────
    B = "bright-smile"
    for date, time, name, phone, reason in [
        (d(-21), "10:00 AM", "Mariam Al Mansoori", "0501234567", "scaling and polishing"),
        (d(-14), "5:30 PM", "Ahmed Khan", "0529876543", "root canal follow-up"),
        (d(-7), "11:30 AM", "Priya Nair", "0554443322", "teeth whitening"),
        (d(-3), "9:30 AM", "Fatima Al Zaabi", "0567891234", "braces consultation"),
        (d(1), "10:00 AM", "Mariam Al Mansoori", "0501234567", "6-month checkup"),
        (d(1), "4:30 PM", "Daniel Murphy", "0508765432", "wisdom tooth pain"),
        (d(2), "2:00 PM", "Ahmed Khan", "0529876543", "crown fitting"),
        (d(5), "12:30 PM", "Aisha Rahman", "0543216789", "kids' first checkup"),
    ]:
        db.save_booking(B, date, time, name, phone, reason)
        db.save_caller_memory(B, name, f"came in for {reason} ({date})")
    for name, note in [
        ("Mariam Al Mansoori", "prefers morning appointments before work"),
        ("Mariam Al Mansoori", "sensitive teeth — uses the gentle polish"),
        ("Ahmed Khan", "anxious about needles, appreciates extra reassurance"),
        ("Priya Nair", "asked about invisible aligners pricing"),
        ("Daniel Murphy", "insurance: Daman Enhanced"),
        ("Fatima Al Zaabi", "prefers Arabic"),
    ]:
        db.save_caller_memory(B, name, note)

    # ── velvet-hair (salon) ──────────────────────────────────────────────────
    V = "velvet-hair"
    for date, time, name, phone, reason in [
        (d(-10), "6:00 PM", "Layla Hassan", "0502223344", "blow-dry"),
        (d(-6), "3:30 PM", "Elena Petrova", "0556667788", "balayage retouch"),
        (d(-2), "7:00 PM", "Noor Al Shamsi", "0523334455", "keratin treatment"),
        (d(1), "6:00 PM", "Layla Hassan", "0502223344", "blow-dry"),
        (d(3), "5:00 PM", "Sara Haddad", "0587654321", "bridal hair trial"),
        (d(4), "2:30 PM", "Elena Petrova", "0556667788", "trim and gloss"),
    ]:
        db.save_booking(V, date, time, name, phone, reason)
        db.save_caller_memory(V, name, f"came in for {reason} ({date})")
    for name, note in [
        ("Layla Hassan", "prefers Rana as her stylist"),
        ("Layla Hassan", "usual: blow-dry every two weeks, Thursday evenings"),
        ("Noor Al Shamsi", "prefers Arabic"),
        ("Elena Petrova", "allergic to ammonia dyes — use the organic line"),
        ("Sara Haddad", "wedding on the 20th — trial before final decision"),
    ]:
        db.save_caller_memory(V, name, note)

    # ── skyline-realty (real estate) ─────────────────────────────────────────
    S = "skyline-realty"
    for name, phone, interest, notes in [
        ("Omar Farooq", "0501112233", "rent 2BR in Dubai Marina, budget 120k/yr", "wants sea view, moving in September"),
        ("Jessica Tan", "0559998877", "buy townhouse in Dubai Hills, budget 2.8M", "pre-approved with Emirates NBD"),
        ("Khalid Al Nuaimi", "0526665544", "rent studio in JVC, budget 55k/yr", "student, needs it furnished"),
        ("Anna Kowalska", "0583332211", "buy 1BR off-plan in Business Bay", "asked about payment plans and handover dates"),
        ("Ravi Menon", "0547778899", "rent villa in Arabian Ranches, budget 220k/yr", "family of five, school proximity matters"),
    ]:
        db.save_lead(S, name, phone, interest, notes)
    for date, time, name, phone, reason in [
        (d(1), "11:00 AM", "Omar Farooq", "0501112233", "viewing: 2BR Marina Gate II"),
        (d(2), "4:00 PM", "Jessica Tan", "0559998877", "viewing: Dubai Hills townhouse"),
    ]:
        db.save_booking(S, date, time, name, phone, reason)
        db.save_caller_memory(S, name, f"viewing arranged: {reason} ({date})")

    # ── handy-home (general services) ────────────────────────────────────────
    H = "handy-home"
    for date, time, name, phone, reason in [
        (d(-5), "9:00 AM", "Bilal Sheikh", "0504445566", "AC deep clean, 2 units"),
        (d(1), "10:30 AM", "Grace Obi", "0551237894", "kitchen sink leak"),
        (d(2), "1:00 PM", "Bilal Sheikh", "0504445566", "AC gas top-up"),
    ]:
        db.save_booking(H, date, time, name, phone, reason)
        db.save_caller_memory(H, name, f"came in for {reason} ({date})")
    db.save_caller_memory(H, "Bilal Sheikh", "villa in Mirdif, gate code 4412, has two cats")
    db.save_lead(H, "Tom Becker", "0509871234", "full villa painting quote", "wants it done before Eid")


if __name__ == "__main__":
    wipe()
    seed()
    for biz in DEMO:
        print(f"{biz}: {len(db.list_bookings(biz))} bookings, {len(db.list_leads(biz))} leads")
    print("Seeded realistic demo data (Dubai-time dates).")
