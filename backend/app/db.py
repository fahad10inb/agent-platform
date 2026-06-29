"""
The database layer — the ONLY file that knows how data is stored.

It now talks to **Supabase Postgres** (a real cloud database) instead of a local
SQLite file. Notice what did NOT change: every function below keeps the exact
same name and arguments, so main.py, the tools, and the prompt are untouched.
That clean seam is the whole payoff — swapping the database meant editing one file.

Differences from the SQLite version (the Postgres dialect):
  • connect with psycopg using the DATABASE_URL (Supabase connection string)
  • placeholders are %s (not ?)
  • auto-increment id is SERIAL; we get the new id back with RETURNING id
  • created_at default is now() and the type is timestamptz
"""

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


def _connect():
    """Open a Postgres connection to Supabase. `dict_row` makes rows behave like
    dicts (row["date"]). Used with `with _connect() as conn:` which commits on
    success and closes the connection automatically."""
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)


def init_db() -> None:
    """Create our tables if they don't exist. Safe to run on every startup."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id            SERIAL PRIMARY KEY,
                business_id   TEXT,
                date          TEXT NOT NULL,
                time          TEXT NOT NULL,
                patient_name  TEXT NOT NULL,
                phone         TEXT,
                reason        TEXT,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS caller_memory (
                id           SERIAL PRIMARY KEY,
                business_id  TEXT,
                caller       TEXT NOT NULL,
                note         TEXT NOT NULL,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS businesses (
                id           TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                type         TEXT NOT NULL,
                hours        TEXT,
                services     TEXT,
                tone         TEXT,
                open_hour    INTEGER,
                close_hour   INTEGER,
                slot_minutes INTEGER,
                faq          TEXT,
                api_key      TEXT,
                vertical     TEXT
            )
            """
        )
        # Sales leads / enquiries (real estate and general businesses capture these
        # instead of — or alongside — appointments).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id           SERIAL PRIMARY KEY,
                business_id  TEXT,
                name         TEXT,
                phone        TEXT,
                interest     TEXT,
                notes        TEXT,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        # Migrations for tables created before these columns existed.
        # Postgres supports IF NOT EXISTS here, so it's safe to run every startup.
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS faq TEXT")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS api_key TEXT")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS vertical TEXT")
        # Booking now captures mobile number + reason for visit (UAE clinics take both).
        conn.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS phone TEXT")
        conn.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reason TEXT")


# --- bookings ----------------------------------------------------------------
def save_booking(
    business_id: str, date: str, time: str, patient_name: str,
    phone: str = "", reason: str = "",
) -> int:
    """Insert one booking for a business and return its new id.

    Captures mobile number + reason for visit (what UAE front desks take), both
    optional. %s placeholders keep it injection-safe; RETURNING id hands back the
    new row's id.
    """
    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO bookings (business_id, date, time, patient_name, phone, reason) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (business_id, date, time, patient_name, phone, reason),
        ).fetchone()
    return row["id"]


def list_bookings(business_id: str) -> list[dict]:
    """Return one business's bookings, newest first. The WHERE clause is the
    isolation wall — never returns another business's rows."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, date, time, patient_name, phone, reason, created_at FROM bookings "
            "WHERE business_id = %s ORDER BY id DESC",
            (business_id,),
        ).fetchall()
    return rows


def booked_times(business_id: str, date: str) -> list[str]:
    """Times already booked for a business on a date (for availability + no
    double-booking)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT time FROM bookings WHERE business_id = %s AND date = %s",
            (business_id, date),
        ).fetchall()
    return [r["time"] for r in rows]


def find_bookings(business_id: str, patient_name: str) -> list[dict]:
    """Find a patient's bookings at a business (case-insensitive name match)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, date, time, patient_name FROM bookings "
            "WHERE business_id = %s AND LOWER(patient_name) = LOWER(%s) ORDER BY date, time",
            (business_id, (patient_name or "").strip()),
        ).fetchall()
    return rows


def cancel_booking(business_id: str, patient_name: str, date: str, time: str) -> bool:
    """Delete a specific booking. Returns True if a row was actually removed."""
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM bookings WHERE business_id = %s AND LOWER(patient_name) = LOWER(%s) "
            "AND date = %s AND time = %s",
            (business_id, (patient_name or "").strip(), date, time),
        )
        removed = cur.rowcount
    return removed > 0


def reschedule_booking(
    business_id: str, patient_name: str, old_date: str, old_time: str, new_date: str, new_time: str
) -> bool:
    """Move a booking to a new date/time. Returns True if a row was updated."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE bookings SET date = %s, time = %s "
            "WHERE business_id = %s AND LOWER(patient_name) = LOWER(%s) AND date = %s AND time = %s",
            (new_date, new_time, business_id, (patient_name or "").strip(), old_date, old_time),
        )
        updated = cur.rowcount
    return updated > 0


# --- caller memory -----------------------------------------------------------
def _norm(name: str) -> str:
    """Normalize a caller name for matching ('Sarah Lee' == 'sarah lee ')."""
    return (name or "").strip().lower()


def save_caller_memory(business_id: str, name: str, note: str) -> None:
    """Remember one fact about a caller of a specific business."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO caller_memory (business_id, caller, note) VALUES (%s, %s, %s)",
            (business_id, _norm(name), note),
        )


def get_caller_memory(business_id: str, name: str) -> list[str]:
    """What we remember about a caller — scoped to ONE business, so the same
    name at a different business is a separate person."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT note FROM caller_memory WHERE business_id = %s AND caller = %s ORDER BY id",
            (business_id, _norm(name)),
        ).fetchall()
    return [r["note"] for r in rows]


# --- businesses (multi-tenancy) ----------------------------------------------
def upsert_business(b: dict) -> None:
    """Insert a business, or update it if its id already exists ('upsert').
    EXCLUDED refers to the values we tried to insert."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO businesses
                (id, name, type, hours, services, tone, open_hour, close_hour, slot_minutes, faq, api_key, vertical)
            VALUES
                (%(id)s, %(name)s, %(type)s, %(hours)s, %(services)s, %(tone)s,
                 %(open_hour)s, %(close_hour)s, %(slot_minutes)s, %(faq)s, %(api_key)s, %(vertical)s)
            ON CONFLICT (id) DO UPDATE SET
                name=EXCLUDED.name, type=EXCLUDED.type, hours=EXCLUDED.hours,
                services=EXCLUDED.services, tone=EXCLUDED.tone,
                open_hour=EXCLUDED.open_hour, close_hour=EXCLUDED.close_hour,
                slot_minutes=EXCLUDED.slot_minutes, faq=EXCLUDED.faq,
                api_key=COALESCE(EXCLUDED.api_key, businesses.api_key),
                vertical=EXCLUDED.vertical
            """,
            {
                "id": b["id"],
                "name": b["name"],
                "type": b["type"],
                "hours": b.get("hours", ""),
                "services": b.get("services", ""),
                "tone": b.get("tone", ""),
                "open_hour": b.get("open_hour", 9),
                "close_hour": b.get("close_hour", 17),
                "slot_minutes": b.get("slot_minutes", 30),
                "faq": b.get("faq", ""),
                "api_key": b.get("api_key"),
                "vertical": b.get("vertical", "general"),
            },
        )


_EDITABLE_BUSINESS_FIELDS = {
    "name", "type", "hours", "services", "tone", "faq",
    "open_hour", "close_hour", "slot_minutes", "vertical",
}


def save_lead(business_id: str, name: str, phone: str, interest: str, notes: str = "") -> int:
    """Insert a sales lead / enquiry for a business; return its new id."""
    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO leads (business_id, name, phone, interest, notes) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (business_id, name, phone, interest, notes),
        ).fetchone()
    return row["id"]


def list_leads(business_id: str) -> list[dict]:
    """Return one business's captured leads, newest first (scoped by business_id)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, phone, interest, notes, created_at FROM leads "
            "WHERE business_id = %s ORDER BY id DESC",
            (business_id,),
        ).fetchall()
    return rows


def update_business_settings(business_id: str, fields: dict) -> None:
    """Update only the editable columns of a business (never id or api_key).

    Column names come from a fixed whitelist (not user input), so building the
    SET clause is safe; values are still passed as parameters.
    """
    cols = {k: v for k, v in fields.items() if k in _EDITABLE_BUSINESS_FIELDS}
    if not cols:
        return
    set_clause = ", ".join(f"{k} = %({k})s" for k in cols)
    params = {**cols, "_bid": business_id}
    with _connect() as conn:
        conn.execute(f"UPDATE businesses SET {set_clause} WHERE id = %(_bid)s", params)


def get_business(business_id: str) -> dict | None:
    """Return one business's config by id, or None if there's no such business."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM businesses WHERE id = %s", (business_id,)
        ).fetchone()
    return row  # dict_row gives a dict (or None)


def list_businesses() -> list[dict]:
    """Return all businesses (for an overview / testing)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, type FROM businesses ORDER BY name"
        ).fetchall()
    return rows
