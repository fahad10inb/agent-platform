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

import logging

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

logger = logging.getLogger("agent-platform.db")

# One shared pool per process. Before this, EVERY db call opened a fresh TLS
# connection to Supabase (a full handshake per query — the dominant latency tax
# on every tool call). The pool keeps warm connections and validates them on
# checkout, so an idle-dropped connection is replaced instead of erroring.
_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().database_url,
            min_size=1,
            max_size=8,
            # prepare_threshold=None: Supabase's pooler (pgbouncer, transaction
            # mode) doesn't support prepared statements — psycopg auto-prepares
            # any query on its 5th use, which then crashes with
            # DuplicatePreparedStatement under real load (found by the QA bot).
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
            # Supabase's pooler kills idle connections quickly; recycle ours
            # FIRST so a query never lands on a half-dead socket ("server
            # closed the connection unexpectedly" — also found by the QA bot).
            max_idle=45,
            max_lifetime=600,
            check=ConnectionPool.check_connection,
            open=True,
        )
    return _pool


def _connect():
    """A pooled Postgres connection as a context manager — a drop-in for the old
    per-call connect: `with _connect() as conn:` still commits on success and
    returns the connection (to the pool) automatically."""
    return _get_pool().connection()


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
        # Structured personalization fields (what competitors collect as first-
        # class data, not buried in an FAQ blob): the team and who's-good-at-what
        # ("with Marwan?"), where to find/park, and the house rules.
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS staff TEXT")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS location TEXT")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS policies TEXT")
        # Booking hygiene (Fresha-style): how much notice a booking needs, how
        # far ahead the calendar opens, and breathing room between appointments.
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS min_notice_hours INTEGER")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS max_advance_days INTEGER")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS buffer_min INTEGER")
        # Where to email the owner when a booking or lead lands (empty = off).
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS notify_email TEXT")
        # Escalation + after-hours behavior: a number to hand a frustrated
        # caller (empty = take a message instead), and what the agent should do
        # outside opening hours ('take_message' | 'book_only' | 'info_only').
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS transfer_number TEXT")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS after_hours_mode TEXT")
        # WhatsApp channel: the Cloud API phone_number_id whose webhooks belong
        # to this business (empty = WhatsApp not connected).
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_phone_id TEXT")
        # Plan + monthly message quota (the founding plan's fair-use fuse and the
        # billing prerequisite). NULL quota = uncapped (the current founding
        # default). quota_notice_month = the 'YYYY-MM' we last warned the owner,
        # so the approaching/over-limit email fires at most once per month.
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS plan TEXT")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS monthly_msg_quota INTEGER")
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS quota_notice_month TEXT")
        # When the weekly ROI digest last went out — the idempotency marker that
        # lets the scheduler re-check hourly without ever double-sending.
        conn.execute("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS last_digest_at TIMESTAMPTZ")
        # Booking now captures mobile number + reason for visit (UAE clinics take both).
        conn.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS phone TEXT")
        conn.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reason TEXT")
        # Two-way reminders: confirmation state a caller sets by replying to the
        # reminder ('booked' | 'confirmed'; a cancel deletes the row entirely).
        conn.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'booked'")
        # Conversations are DURABLE (were in-process RAM: every deploy wiped all
        # active chats mid-sentence, and it could never scale past one server).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id              SERIAL PRIMARY KEY,
                business_id     TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL,
                text            TEXT NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        # Structured service menu — one row per bookable service. Duration is a
        # first-class column (it drives real slot math per service) and price is
        # TEXT on purpose: owners write "80 AED", "from 150", "free consult".
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                id           SERIAL PRIMARY KEY,
                business_id  TEXT NOT NULL,
                name         TEXT NOT NULL,
                duration_min INTEGER NOT NULL,
                price        TEXT DEFAULT '',
                category     TEXT DEFAULT '',
                bookable     BOOLEAN DEFAULT TRUE
            )
            """
        )
        # Property listings — one row per property a real-estate business has
        # live. All TEXT on purpose: owners write "1.2M", "60k/yr", "2", "studio".
        # The prompt quotes ONLY these, so the bot can shortlist without ever
        # inventing a property.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id           SERIAL PRIMARY KEY,
                business_id  TEXT NOT NULL,
                title        TEXT NOT NULL,
                area         TEXT DEFAULT '',
                bedrooms     TEXT DEFAULT '',
                price        TEXT DEFAULT '',
                purpose      TEXT DEFAULT '',
                notes        TEXT DEFAULT ''
            )
            """
        )
        # Reminder log — one row per (booking, stage) actually sent. The UNIQUE
        # constraint is the send-once guarantee: the sweep INSERTs to CLAIM a
        # reminder, so two overlapping sweeps (or a restart mid-pass) can never
        # message the same caller twice for the same stage.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id           SERIAL PRIMARY KEY,
                business_id  TEXT NOT NULL,
                booking_id   INTEGER NOT NULL,
                stage        TEXT NOT NULL,
                sent_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (booking_id, stage)
            )
            """
        )
        # Usage metering per business per day — the raw material for billing,
        # quotas and "your month at a glance". Without it even manual invoicing
        # has no data to stand on.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_daily (
                business_id  TEXT NOT NULL,
                day          DATE NOT NULL,
                messages     INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (business_id, day)
            )
            """
        )
        # Every hot query filters on these — without indexes each is a full
        # table scan that grows linearly with every tenant's data combined.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bookings_biz_date ON bookings (business_id, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_caller_memory_biz ON caller_memory (business_id, caller)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_biz ON leads (business_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_services_biz ON services (business_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_listings_biz ON listings (business_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages (business_id, conversation_id, id)")
    # One slot = one booking, enforced by the DATABASE — the tool's check-then-
    # insert has a race window (two simultaneous callers both pass the check);
    # this unique index is what actually guarantees no double-booking. Separate
    # connection + best-effort: if legacy duplicate rows block index creation,
    # the app still starts (the tool-level check still applies).
    try:
        with _connect() as conn:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_slot "
                "ON bookings (business_id, date, time)"
            )
    except Exception:
        # This index IS the double-booking guarantee — if it can't be created
        # (e.g. legacy duplicate rows), the app must still boot, but we can't let
        # the loss of the guarantee be invisible. Log LOUD so it's noticed and
        # the duplicates cleaned up; the tool-level check still applies meanwhile.
        logger.exception("CRITICAL: could not create uq_booking_slot — double-booking guard is OFF")


# --- bookings ----------------------------------------------------------------
def save_booking(
    business_id: str, date: str, time: str, patient_name: str,
    phone: str = "", reason: str = "",
) -> int | None:
    """Insert one booking for a business and return its new id — or None if the
    slot was taken in the race window between the tool's check and this insert
    (the unique index is the real no-double-booking guarantee).

    Captures mobile number + reason for visit (what UAE front desks take), both
    optional. %s placeholders keep it injection-safe; RETURNING id hands back the
    new row's id.
    """
    try:
        with _connect() as conn:
            row = conn.execute(
                "INSERT INTO bookings (business_id, date, time, patient_name, phone, reason) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (business_id, date, time, patient_name, phone, reason),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        return None
    return row["id"]


def list_bookings(business_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """Return one business's bookings, newest first, paginated (a busy salon's
    500th booking must not turn every dashboard load into a full dump). The
    WHERE clause is the isolation wall — never returns another business's rows."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, date, time, patient_name, phone, reason, created_at FROM bookings "
            "WHERE business_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
            (business_id, limit, offset),
        ).fetchall()
    return rows


# --- conversations (durable chat history) --------------------------------------
def save_message(business_id: str, conversation_id: str, role: str, text: str) -> None:
    """Append one turn to a conversation's durable history."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (business_id, conversation_id, role, text) VALUES (%s, %s, %s, %s)",
            (business_id, conversation_id, role, text),
        )


def get_history(business_id: str, conversation_id: str, limit: int = 40) -> list[dict]:
    """The last `limit` turns of one conversation, oldest first — exactly the
    shape the LLM layer expects. Scoped by business_id so the same
    conversation_id at two businesses can never share context."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, text FROM messages "
            "WHERE business_id = %s AND conversation_id = %s ORDER BY id DESC LIMIT %s",
            (business_id, conversation_id, limit),
        ).fetchall()
    return list(reversed(rows))


def count_user_messages(business_id: str, conversation_id: str) -> int:
    """Total caller messages EVER in a conversation — the distiller's cadence
    counter. Counting the durable total (not the capped history window) keeps
    the 'every 6th message' trigger firing on long WhatsApp threads that would
    otherwise saturate the window at 20 forever."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM messages "
            "WHERE business_id = %s AND conversation_id = %s AND role = 'user'",
            (business_id, conversation_id),
        ).fetchone()
    return int(row["n"])


# --- usage metering -------------------------------------------------------------
def bump_usage(business_id: str, messages: int = 1) -> None:
    """Count one (or more) handled messages against today's usage row."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO usage_daily (business_id, day, messages) "
            "VALUES (%s, (now() AT TIME ZONE 'Asia/Dubai')::date, %s) "
            "ON CONFLICT (business_id, day) DO UPDATE SET messages = usage_daily.messages + EXCLUDED.messages",
            (business_id, messages),
        )


def get_metrics(business_id: str) -> dict:
    """The owner's value-proof numbers: today + last 30 days, in one round trip.
    Conversations = distinct chat threads; messages = every question handled.

    Fair-billing rule: a conversation only COUNTS once the caller sent a second
    message — spam and one-line drive-bys are never counted (the landing page
    pledges this in writing, so the metric must actually behave that way).
    messages_30d stays raw on purpose: it answers "how busy was the agent",
    not "what would you be billed for"."""
    with _connect() as conn:
        m = conn.execute(
            # ::int on the SUM: SUM(bigint) is numeric in Postgres, which psycopg
            # hands back as Decimal — the old COUNT(*) was an int, keep it one.
            "SELECT COUNT(*) FILTER (WHERE user_msgs >= 2) AS convs_30d, "
            "COALESCE(SUM(user_msgs), 0)::int AS msgs_30d, "
            "COUNT(*) FILTER (WHERE user_msgs >= 2 AND last_day = CURRENT_DATE) AS convs_today "
            "FROM (SELECT conversation_id, COUNT(*) AS user_msgs, MAX(created_at::date) AS last_day "
            "      FROM messages WHERE business_id = %s AND role = 'user' "
            "      AND created_at > now() - interval '30 days' "
            "      GROUP BY conversation_id) per_conv",
            (business_id,),
        ).fetchone()
        b = conn.execute(
            "SELECT COUNT(*) AS n FROM bookings WHERE business_id = %s "
            "AND created_at > now() - interval '30 days'",
            (business_id,),
        ).fetchone()
        led = conn.execute(
            "SELECT COUNT(*) AS n FROM leads WHERE business_id = %s "
            "AND created_at > now() - interval '30 days'",
            (business_id,),
        ).fetchone()
    return {
        "conversations_today": m["convs_today"],
        "conversations_30d": m["convs_30d"],
        "messages_30d": m["msgs_30d"],
        "bookings_30d": b["n"],
        "leads_30d": led["n"],
    }


def get_week_stats(business_id: str) -> dict:
    """One business's last-7-days numbers for the weekly owner digest.
    Same fair-billing rule as get_metrics: a conversation counts only once the
    caller sent a second message (drive-bys aren't value, so they aren't news)."""
    with _connect() as conn:
        m = conn.execute(
            # Same ::int cast as get_metrics: SUM(bigint) would come back Decimal.
            "SELECT COUNT(*) FILTER (WHERE user_msgs >= 2) AS convs_7d, "
            "COALESCE(SUM(user_msgs), 0)::int AS msgs_7d "
            "FROM (SELECT conversation_id, COUNT(*) AS user_msgs "
            "      FROM messages WHERE business_id = %s AND role = 'user' "
            "      AND created_at > now() - interval '7 days' "
            "      GROUP BY conversation_id) per_conv",
            (business_id,),
        ).fetchone()
        b = conn.execute(
            "SELECT COUNT(*) AS n FROM bookings WHERE business_id = %s "
            "AND created_at > now() - interval '7 days'",
            (business_id,),
        ).fetchone()
        led = conn.execute(
            "SELECT COUNT(*) AS n FROM leads WHERE business_id = %s "
            "AND created_at > now() - interval '7 days'",
            (business_id,),
        ).fetchone()
    return {
        "conversations_7d": m["convs_7d"],
        "messages_7d": m["msgs_7d"],
        "bookings_7d": b["n"],
        "leads_7d": led["n"],
    }


def set_last_digest(business_id: str) -> None:
    """Stamp 'the weekly digest went out now' — the 6-day rule reads this back."""
    with _connect() as conn:
        conn.execute(
            "UPDATE businesses SET last_digest_at = now() WHERE id = %s", (business_id,)
        )


def get_usage(business_id: str, days: int = 30) -> list[dict]:
    """Per-day message counts for the last `days` days, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT day, messages FROM usage_daily "
            "WHERE business_id = %s AND day > CURRENT_DATE - %s::int ORDER BY day DESC",
            (business_id, days),
        ).fetchall()
    return rows


def get_month_usage(business_id: str) -> int:
    """Messages handled for this business so far THIS calendar month (Dubai) —
    the number a monthly quota is checked against."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(messages), 0) AS n FROM usage_daily "
            "WHERE business_id = %s "
            "AND day >= date_trunc('month', (now() AT TIME ZONE 'Asia/Dubai'))::date",
            (business_id,),
        ).fetchone()
    return int(row["n"])


def claim_quota_notice(business_id: str, month: str) -> bool:
    """Atomically claim the right to send THIS month's quota email. Returns True
    to exactly one caller per (business, month); every later call returns False,
    so concurrent turns crossing the threshold can't spam the owner."""
    with _connect() as conn:
        row = conn.execute(
            "UPDATE businesses SET quota_notice_month = %s "
            "WHERE id = %s AND (quota_notice_month IS DISTINCT FROM %s) RETURNING id",
            (month, business_id, month),
        ).fetchone()
    return row is not None


def forget_caller(business_id: str, phone: str = "", name: str = "") -> dict:
    """Erase one caller's data across every table (PDPL / GDPR erasure right).

    Matches by phone digits where a phone column exists, and by name for
    name-keyed rows (caller_memory) and web conversations. WhatsApp threads are
    keyed `wa-<digits>`, so those message rows are matched by conversation_id.
    Returns per-table delete counts."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    counts: dict[str, int] = {}
    with _connect() as conn:
        if digits:
            counts["bookings"] = conn.execute(
                "DELETE FROM bookings WHERE business_id = %s "
                "AND regexp_replace(COALESCE(phone,''), '\\D', '', 'g') = %s",
                (business_id, digits),
            ).rowcount
            counts["leads"] = conn.execute(
                "DELETE FROM leads WHERE business_id = %s "
                "AND regexp_replace(COALESCE(phone,''), '\\D', '', 'g') = %s",
                (business_id, digits),
            ).rowcount
            counts["whatsapp_messages"] = conn.execute(
                "DELETE FROM messages WHERE business_id = %s AND conversation_id = %s",
                (business_id, f"wa-{digits}"),
            ).rowcount
        if name:
            counts["caller_memory"] = conn.execute(
                "DELETE FROM caller_memory WHERE business_id = %s AND lower(caller) = lower(%s)",
                (business_id, name),
            ).rowcount
    return counts


def booked_times(business_id: str, date: str) -> list[str]:
    """Times already booked for a business on a date (for availability + no
    double-booking)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT time FROM bookings WHERE business_id = %s AND date = %s",
            (business_id, date),
        ).fetchall()
    return [r["time"] for r in rows]


def future_bookings() -> list[dict]:
    """Every not-yet-past booking across ALL businesses — the reminder sweep's
    input. `date` is ISO TEXT ('YYYY-MM-DD'), so a lexicographic >= today's ISO
    date is a correct date filter; the small result set is refined (24h/2h) in
    Python, where the '2:00 PM' times are easy to parse."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, business_id, date, time, patient_name, phone, reason, "
            "COALESCE(status, 'booked') AS status FROM bookings "
            "WHERE date >= (now() AT TIME ZONE 'Asia/Dubai')::date::text "
            "ORDER BY date, time",
        ).fetchall()
    return rows


def claim_reminder(business_id: str, booking_id: int, stage: str) -> bool:
    """Atomically claim the right to send this (booking, stage) reminder. Returns
    True to exactly one caller; the UNIQUE(booking_id, stage) constraint makes
    every later attempt a no-op (returns False), so a reminder is sent once."""
    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO reminders (business_id, booking_id, stage) VALUES (%s, %s, %s) "
            "ON CONFLICT (booking_id, stage) DO NOTHING RETURNING id",
            (business_id, booking_id, stage),
        ).fetchone()
    return row is not None


def set_booking_status(business_id: str, patient_name: str, date: str, time: str, status: str) -> bool:
    """Mark a caller's booking confirmed (the two-way reminder reply). Scoped by
    business_id + name + slot so it can only ever touch that caller's row."""
    with _connect() as conn:
        row = conn.execute(
            "UPDATE bookings SET status = %s WHERE business_id = %s "
            "AND lower(patient_name) = lower(%s) AND date = %s AND time = %s RETURNING id",
            (status, business_id, patient_name, date, time),
        ).fetchone()
    return row is not None


def bookings_with_times(business_id: str, date: str) -> list[dict]:
    """Each booking on a date as {time, reason} — the reason is what lets the
    calendar infer an existing booking's true length (it names the service),
    so overlap checks can block a new slot that would cut into it."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT time, reason FROM bookings WHERE business_id = %s AND date = %s",
            (business_id, date),
        ).fetchall()
    return rows


def find_bookings(business_id: str, patient_name: str) -> list[dict]:
    """Find a patient's bookings at a business (case-insensitive name match)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, date, time, patient_name, phone FROM bookings "
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
) -> bool | None:
    """Move a booking to a new date/time. Returns True if a row was updated,
    False if no matching booking exists, or None if the new slot was grabbed
    in the race window (unique index)."""
    try:
        with _connect() as conn:
            cur = conn.execute(
                "UPDATE bookings SET date = %s, time = %s "
                "WHERE business_id = %s AND LOWER(patient_name) = LOWER(%s) AND date = %s AND time = %s",
                (new_date, new_time, business_id, (patient_name or "").strip(), old_date, old_time),
            )
            updated = cur.rowcount
    except psycopg.errors.UniqueViolation:
        return None
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


def replace_caller_memory(business_id: str, name: str, notes: list[str]) -> None:
    """Swap ALL of one caller's notes for a new (consolidated) set — atomically.

    DELETE + INSERTs happen inside ONE connection context, i.e. one transaction:
    if any insert fails the delete rolls back too, so a crash mid-replace can
    never leave the caller with an empty memory. That guarantee is why this
    lives here and not as delete+save calls in the consolidation code."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM caller_memory WHERE business_id = %s AND caller = %s",
            (business_id, _norm(name)),
        )
        for note in notes:
            conn.execute(
                "INSERT INTO caller_memory (business_id, caller, note) VALUES (%s, %s, %s)",
                (business_id, _norm(name), note),
            )


# --- services (structured menu) ------------------------------------------------
def list_services(business_id: str) -> list[dict]:
    """One business's service menu, in the order the owner wrote it."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, duration_min, price, category, bookable FROM services "
            "WHERE business_id = %s ORDER BY id",
            (business_id,),
        ).fetchall()
    return rows


def replace_services(business_id: str, services: list[dict]) -> None:
    """Swap a business's WHOLE service menu for a new one — atomically.

    DELETE + INSERTs share ONE connection context (one transaction), the same
    guarantee as replace_caller_memory: a crash mid-replace can never leave the
    business with a half-empty menu."""
    with _connect() as conn:
        conn.execute("DELETE FROM services WHERE business_id = %s", (business_id,))
        for s in services:
            conn.execute(
                "INSERT INTO services (business_id, name, duration_min, price, category, bookable) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (business_id, s["name"], s["duration_min"], s.get("price", ""),
                 s.get("category", ""), s.get("bookable", True)),
            )


def list_listings(business_id: str) -> list[dict]:
    """One business's live property listings, in the order the owner wrote them."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, area, bedrooms, price, purpose, notes FROM listings "
            "WHERE business_id = %s ORDER BY id",
            (business_id,),
        ).fetchall()
    return rows


def replace_listings(business_id: str, listings: list[dict]) -> None:
    """Swap a business's WHOLE listings sheet for a new one — atomically, same
    guarantee as replace_services: never a half-empty sheet."""
    with _connect() as conn:
        conn.execute("DELETE FROM listings WHERE business_id = %s", (business_id,))
        for row in listings:
            conn.execute(
                "INSERT INTO listings (business_id, title, area, bedrooms, price, purpose, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (business_id, row["title"], row.get("area", ""), row.get("bedrooms", ""),
                 row.get("price", ""), row.get("purpose", ""), row.get("notes", "")),
            )


def rotate_api_key(business_id: str, new_key: str) -> bool:
    """Set a business's api_key to a freshly generated value. `api_key` is
    deliberately absent from _EDITABLE_BUSINESS_FIELDS (settings can never touch
    it), so this is the ONLY path that changes it — the revoke button for a
    leaked key. Returns False if the business doesn't exist."""
    with _connect() as conn:
        row = conn.execute(
            "UPDATE businesses SET api_key = %s WHERE id = %s RETURNING id",
            (new_key, business_id),
        ).fetchone()
    return row is not None


def get_business_by_whatsapp(phone_number_id: str) -> dict | None:
    """Which tenant owns this WhatsApp number? Routes inbound webhooks."""
    if not phone_number_id:
        return None
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM businesses WHERE whatsapp_phone_id = %s LIMIT 1",
            (phone_number_id,),
        ).fetchone()


# --- businesses (multi-tenancy) ----------------------------------------------
def upsert_business(b: dict) -> None:
    """Insert a business, or update it if its id already exists ('upsert').
    EXCLUDED refers to the values we tried to insert."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO businesses
                (id, name, type, hours, services, tone, open_hour, close_hour, slot_minutes, faq, api_key, vertical,
                 staff, location, policies, min_notice_hours, max_advance_days, buffer_min,
                 transfer_number, after_hours_mode, notify_email)
            VALUES
                (%(id)s, %(name)s, %(type)s, %(hours)s, %(services)s, %(tone)s,
                 %(open_hour)s, %(close_hour)s, %(slot_minutes)s, %(faq)s, %(api_key)s, %(vertical)s,
                 %(staff)s, %(location)s, %(policies)s,
                 %(min_notice_hours)s, %(max_advance_days)s, %(buffer_min)s,
                 %(transfer_number)s, %(after_hours_mode)s, %(notify_email)s)
            ON CONFLICT (id) DO UPDATE SET
                name=EXCLUDED.name, type=EXCLUDED.type, hours=EXCLUDED.hours,
                services=EXCLUDED.services, tone=EXCLUDED.tone,
                open_hour=EXCLUDED.open_hour, close_hour=EXCLUDED.close_hour,
                slot_minutes=EXCLUDED.slot_minutes, faq=EXCLUDED.faq,
                api_key=COALESCE(EXCLUDED.api_key, businesses.api_key),
                vertical=EXCLUDED.vertical,
                staff=EXCLUDED.staff, location=EXCLUDED.location, policies=EXCLUDED.policies,
                min_notice_hours=EXCLUDED.min_notice_hours,
                max_advance_days=EXCLUDED.max_advance_days, buffer_min=EXCLUDED.buffer_min,
                transfer_number=EXCLUDED.transfer_number,
                after_hours_mode=EXCLUDED.after_hours_mode,
                notify_email=EXCLUDED.notify_email
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
                "staff": b.get("staff", ""),
                "location": b.get("location", ""),
                "policies": b.get("policies", ""),
                "min_notice_hours": b.get("min_notice_hours", 1),
                "max_advance_days": b.get("max_advance_days", 60),
                "buffer_min": b.get("buffer_min", 0),
                "transfer_number": b.get("transfer_number", ""),
                "after_hours_mode": b.get("after_hours_mode", "take_message"),
                "notify_email": b.get("notify_email", ""),
            },
        )


_EDITABLE_BUSINESS_FIELDS = {
    "name", "type", "hours", "services", "tone", "faq",
    "open_hour", "close_hour", "slot_minutes", "vertical",
    "staff", "location", "policies",
    "min_notice_hours", "max_advance_days", "buffer_min",
    "notify_email", "transfer_number", "after_hours_mode", "whatsapp_phone_id",
    # Admin-set only (no tenant-editable model exposes these) — the usage cap a
    # business must not raise on itself, plus its once-a-month notice marker.
    "plan", "monthly_msg_quota", "quota_notice_month",
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


def find_recent_lead(business_id: str, phone: str, within_hours: int = 48) -> dict | None:
    """The same caller re-captured within a couple of days is ONE lead, not two —
    matched on the phone's digits so '050 123 4567' equals '0501234567'."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, phone, interest, notes FROM leads "
            "WHERE business_id = %s AND regexp_replace(phone, '\\D', '', 'g') = %s "
            "AND created_at > now() - make_interval(hours => %s) "
            "ORDER BY id DESC LIMIT 1",
            (business_id, digits, within_hours),
        ).fetchone()
    return row


def update_lead(lead_id: int, interest: str, notes: str = "") -> None:
    """Enrich an existing lead in place (the dedup path — see find_recent_lead)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE leads SET interest = %s, notes = %s WHERE id = %s",
            (interest, notes, lead_id),
        )


def list_leads(business_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """Return one business's captured leads, newest first, paginated."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, phone, interest, notes, created_at FROM leads "
            "WHERE business_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
            (business_id, limit, offset),
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


def list_businesses_full() -> list[dict]:
    """The digest sender's view of every business: who to email and when they
    last got one. Deliberately NOT api_key or the whole row — the digest loop
    only needs these four columns, so that's all it can ever leak."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, notify_email, last_digest_at FROM businesses ORDER BY id"
        ).fetchall()
    return rows
