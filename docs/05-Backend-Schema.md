# Backend Schema
### ReceptionAI — data model (Supabase Postgres)

| | |
|---|---|
| **Version** | 1.0 |
| **Engine** | Postgres (Supabase) |
| **Migrations** | `db.init_db()` runs idempotent DDL on **every boot** — `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. No migration tool needed. |
| **Access** | `app/db.py` is the **only** module that touches SQL. |

**Tenancy rule:** every table carries `business_id` and every query filters on it.

---

## 1. `businesses` — the tenant

The agency's whole configuration. One row per client.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT **PK** | URL-safe slug (`skyline-realty`) — appears in widget links |
| `name`, `type` | TEXT | "Skyline Realty", "real estate agency" |
| `vertical` | TEXT | `real_estate` \| `clinic` \| `salon` \| `general` — drives behaviour |
| `tone` | TEXT | Persona voice |
| `hours` | TEXT | Human-readable, as customers should hear it |
| `open_hour`, `close_hour`, `slot_minutes` | INTEGER | Drive the **real** slot grid |
| `min_notice_hours`, `max_advance_days`, `buffer_min` | INTEGER | Booking hygiene |
| `services`, `faq` | TEXT | Descriptive copy + extra knowledge |
| `staff`, `location`, `policies` | TEXT | First-class personalisation (not buried in FAQ) |
| **`areas_covered`** | TEXT | Communities served — grounds "do you cover X?" |
| **`deal_focus`** | TEXT | Sale / rent / off-plan / commercial |
| **`languages`** | TEXT | What the team speaks |
| **`orn`** | TEXT | **RERA Office Registration Number** — the trust signal |
| `api_key` | TEXT | **SHA-256 hash** (`sha256:…`); legacy plaintext still verifiable |
| `notify_email` | TEXT | Owner alerts (empty = off) |
| `transfer_number`, `after_hours_mode` | TEXT | Escalation + closed-hours behaviour |
| `whatsapp_phone_id` | TEXT | Meta Cloud API phone id → tenant routing |
| `google_review_url` | TEXT | Post-visit review ask (empty = off) |
| `crm_webhook_url`, `crm_type` | TEXT | Qualified-lead write-back |
| `lead_ingest_token`, `calendar_token` | TEXT | Token-gated public endpoints (rotatable) |
| `plan`, `monthly_msg_quota`, `quota_notice_month` | TEXT/INT | Billing fuse — **admin-set only** |
| `last_digest_at` | TIMESTAMPTZ | Weekly digest marker |

> `monthly_msg_quota` is deliberately **not** tenant-editable — a client must not be
> able to raise its own cap.

---

## 2. Conversation & booking core

### `messages` — durable conversation history
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `business_id`, `conversation_id` | TEXT | `wa-<E.164>` \| `web-…` \| `call-<E.164>` |
| `role` | TEXT | `user` \| `model` |
| `text` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

> Was in RAM once — a deploy wiped live chats. Now durable, and
> **persist-only-on-success** means a failed turn never half-writes.

### `bookings` — viewings / appointments
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `business_id` | TEXT | |
| `date`, `time` | TEXT | Dubai date + slot label ("4:00 PM"), normalised |
| `patient_name`, `phone`, `reason` | TEXT | |
| `status` | TEXT | `booked` \| `confirmed` \| `cancelled` |
| `created_at` | TIMESTAMPTZ | |

🔒 **`UNIQUE (business_id, date, time)`** — double-booking is impossible **at the
database**, not by prompt discipline.

### `leads` — captured enquiries
`id · business_id · name · phone · interest · notes · created_at`
Deduped on phone within 48h (same caller = one lead, enriched).

### `caller_memory` — what we remember about a person
`id · business_id · caller · note · created_at` — powers "welcome back" recognition.

---

## 3. Real-estate tables

### `listings` — the agency's live inventory
| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `business_id` | TEXT | |
| `title`, `area`, `bedrooms`, `price`, `purpose`, `notes` | TEXT | **All TEXT on purpose** — owners write "1.2M", "60k/yr", "studio" |
| **`permit_number`** | TEXT | **Trakheesi/DLD permit — the compliance key** |
| `reference` | TEXT | Agency's own ref; dedup key across import sources |

> The prompt quotes **only** these rows, so the AI can shortlist without ever
> inventing a property. If `permit_number` is empty, the **price and purpose are
> withheld from the model entirely** — it cannot advertise a number it never saw.

### `qualifications` — the lead's stated requirements
| Column | Type | Notes |
|---|---|---|
| `business_id`, `phone` | TEXT | **UNIQUE together** — re-qualifying updates, never dupes |
| `name` | TEXT | |
| `fields` | TEXT (JSON) | budget, area, bedrooms, purpose, timeline, pay_method… |
| `score` | TEXT | `A` \| `B` \| `C` |
| `updated_at` | TIMESTAMPTZ | |

This is what the **requirement-match** sweep reads to find "the right property."

### `services` — bookable service menu (non-RE verticals)
`id · business_id · name · duration_min · price · category · bookable`
Duration drives the real slot grid per service.

---

## 4. Outbound & compliance tables

Each outbound sweep **claims a UNIQUE row before sending** — that's the send-once
guarantee that makes overlapping sweeps and restarts safe.

| Table | Key | Guarantee |
|---|---|---|
| `reminders` | `UNIQUE (booking_id, stage)` | One reminder per booking per stage (24h / 2h) |
| `nurture_log` | `UNIQUE (business_id, phone, stage)` | One nurture touch per stage (day2/7/30) |
| `review_requests` | `UNIQUE (booking_id)` | A client is asked for a review at most once |
| **`match_alerts`** | `UNIQUE (business_id, phone, listing_key)` | A lead hears about a given **property** at most once. `listing_key` = the permit number, so it survives listing re-imports (which change row ids) |

### `opt_outs` — PDPL
`PK (business_id, phone)`, keyed on **E.164** so `05x`, `+971…` and `971…` all agree.
Every sweep checks it.

### `ai_pauses` — human takeover
`(business_id, conversation_id, paused_at)` — the AI stays silent on that thread.

### `usage_daily` — the billing fuse
Per-business message counts by **Dubai** day (not UTC), feeding the monthly quota.

---

## 5. Cross-cutting conventions

### Phone matching
UAE numbers are compared on their **significant last 9 digits**:
```sql
RIGHT(regexp_replace(COALESCE(phone,''), '\D', '', 'g'), 9) = RIGHT(%s, 9)
```
So `0501234567`, `+971 50 123 4567` and `971501234567` are one person. Thread ids and
opt-out keys use `to_wa_number()` E.164 — these two had drifted once and caused
nurture to message already-booked clients.

### Time
Dates and slot labels are stored as **TEXT in Dubai local time**. Dubai is UTC+4 with
no DST, so the `.ics` feed emits plain UTC (`…Z`) — the most portable form.

### Settings writes
`update_business_settings()` filters against a fixed `_EDITABLE_BUSINESS_FIELDS`
whitelist — column names are never user input, values are always parameters.

### Reads
`get_business()` is `SELECT *`, but **`/manage` returns a fixed field whitelist** and
`list_businesses_full()` is deliberately digest-only (4 columns) — so a new column is
not automatically exposed. ⚠️ Adding a tenant field means adding it to the whitelist
too, or the UI reads it back empty.
