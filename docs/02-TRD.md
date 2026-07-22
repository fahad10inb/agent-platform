# Technical Requirements Document (TRD)
### ReceptionAI — architecture, stack, and engineering contracts

| | |
|---|---|
| **Version** | 1.0 |
| **Runtime** | Python 3.11+ · FastAPI (async) |
| **Deploy** | Render (push-to-`main` auto-deploy) |
| **Repo** | `fahad10inb/agent-platform` |

---

## 1. Architecture at a glance

```
   WhatsApp (Meta Cloud API)  ─┐
   Website widget  ────────────┼──►  FastAPI app  ──►  chat_core.run_turn  ──►  Gemini
   Voice (Twilio, scaffolded) ─┘         │                     │
                                         │                     ├─► function-calling TOOLS
                                         │                     │   (calendar · leads · qualify
                                         │                     │    · memory · handoff · compliance)
                                         ▼                     ▼
                                   Supabase Postgres  ◄── all state (single seam: db.py)
                                         │
        background sweeps (in-process) ──┴──► reminders · nurture · reviews · match alerts
                                         └──► Resend (owner email) · CRM webhook
```

**Design principle:** one brain, many channels. WhatsApp, web widget, demo and voice
all funnel into the **same** `chat_core.run_turn()`, so behaviour can never drift
between channels.

---

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| API | **FastAPI** (async) | Async I/O for LLM + Graph API calls |
| LLM | **google-genai**, `gemini-2.5-flash` | Quality/cost balance; strong Arabic |
| LLM (background) | `gemini-2.5-flash-lite` | Cheap distillation/consolidation |
| DB | **Supabase Postgres** via `psycopg` + `ConnectionPool` | Managed, SQL, RLS-capable |
| Hosting | **Render** | Zero-ops; push-to-main deploy |
| Email | **Resend** (HTTP API) | Owner alerts |
| Frontend | **Server-rendered HTML strings** (no build step) | One deploy, no separate frontend |

⚠️ `prepare_threshold=None` on the pool — the Supabase **pooler does not support
prepared statements** (caused `DuplicatePreparedStatement` in production).

---

## 3. Module map

| Module | Responsibility |
|---|---|
| `main.py` | Routes, middleware, schedulers, admin endpoints |
| `chat_core.py` | **Channel-agnostic turn** — pause gate → quota → lock → LLM → persist |
| `llm_service.py` | Gemini calls, tool loop, retries, empty/leaked-reply recovery |
| `prompt_service.py` | System-prompt assembly (persona, facts, listings, compliance) |
| `db.py` | **The only storage seam.** All SQL lives here |
| `whatsapp.py` | Webhook (verify + HMAC), inbound parse, send text/template |
| `tools/` | Function-calling tools: calendar, leads, qualify, memory, handoff |
| `reminder_service` `nurture_service` `review_service` `matcher_service` | Outbound sweeps |
| `lead_intake.py` | Portal-email parsing → lead → instant outreach |
| `listing_import.py` | CSV / XML / Reelly listing import + normalisation |
| `ics.py` | iCalendar feed + per-booking invite |
| `*_html.py` | Landing, widget, dashboard, demo, story pages |

---

## 4. Core contracts

### 4.1 `chat_core.run_turn(business_id, conversation_id, message, schedule, activity=None)`
The single turn. Order is deliberate:
1. **Human-takeover gate** — if the owner took the thread, save the customer's message and return `""` (silent).
2. **Monthly quota fuse** — over cap → graceful decline, **no LLM call**.
3. **Per-(business, conversation) `asyncio.Lock`** — serialises rapid messages in one thread.
4. Load history (capped) → build prompt → LLM with tools → **persist only on success**.

### 4.2 Multi-tenancy
- Every row is keyed by `business_id`. Every query filters on it.
- Auth: per-business API key (**SHA-256 hashed**, legacy plaintext still verifiable).
- Cross-tenant access → **403**. Admin key is separate and constant-time compared.

### 4.3 Idempotency (all outbound)
Every sweep **claims before sending** via a `UNIQUE` row:

| Sweep | Claim key |
|---|---|
| Reminders | `UNIQUE(booking_id, stage)` |
| Nurture | `UNIQUE(business_id, phone, stage)` |
| Reviews | `UNIQUE(booking_id)` |
| Match alerts | `UNIQUE(business_id, phone, listing_key)` |

Overlapping sweeps and restarts can therefore never double-send.

### 4.4 No double-booking
A `UNIQUE` index on `(business_id, date, time)` — enforced **at the database**, not by
prompt discipline. A race resolves to `unavailable`.

⚠️ A tool turn **never blind-retries** on timeout: the booking may have committed in
the thread, and a retry could book a *different* slot.

---

## 5. Integrations

| Integration | Notes |
|---|---|
| **WhatsApp Cloud API** | Webhook `GET` verify + `POST` with **HMAC signature** (fails closed when `APP_SECRET` set). `wamid` dedup against Meta redelivery. Per-tenant routing via `whatsapp_phone_id`. Outside the **24h window**, only an **approved template** delivers. |
| **Gemini** | Hard timeout; tool loop; recovery for empty or leaked-tool-call replies. |
| **Resend** | Owner alerts; logs-only without a key (graceful). |
| **CRM webhook** | Bitrix24-shaped or generic JSON POST, daemon thread. |
| **Reelly / CSV / XML** | Listing import, SSRF-guarded fetch. |
| **Twilio ConversationRelay** | Voice scaffold, default **off**. |

---

## 6. Non-functional requirements

### Security
- API keys hashed (SHA-256), never logged. Admin key constant-time compared.
- WhatsApp webhook **fails closed** without an app secret.
- SSRF guard on all URL fetches (blocks private/loopback/metadata, re-validates redirects).
- PII kept out of logs. Dashboard `frame-ancestors 'none'`; HSTS; `nosniff`.
- `/docs` disabled outside development.

### Reliability
- Persist-only-on-success (a failed turn rolls back, never half-writes).
- Every sweep survives a bad pass (`try/except` per business).
- Durable conversations in Postgres (a deploy must not wipe live chats).
- ⚠️ **Render free tier sleeps** → a cold start makes Meta's webhook time out and
  **drop the message**. Always-on plan is required for a real customer.

### Cost control
- Per-business **monthly message quota** with an owner warning at 80% and a graceful
  decline over cap. Cacheable prompt prefix ordering; cheap model for background work.

### Performance
- Target first response **< 30s** end-to-end (LLM-bound).
- All business context is loaded **once per turn**; no mid-turn lookups.

---

## 7. Environment

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase Postgres |
| `GEMINI_API_KEY` | LLM |
| `ADMIN_API_KEY` | Admin endpoints |
| `WHATSAPP_ACCESS_TOKEN` / `_VERIFY_TOKEN` / `_APP_SECRET` | WhatsApp channel |
| `WHATSAPP_TEMPLATE_*` | Approved template names per message kind |
| `RESEND_API_KEY` | Owner email |
| `ENVIRONMENT` | `production` disables `/docs` |
| `SENTRY_DSN` | Optional error monitoring |
| `*_ENABLED` | Kill switches: digest, reminders, nurture, reviews, match alerts |

---

## 8. Testing

- **285 tests**, `pytest`. CI gates deploy.
- `tests/conftest.py` swaps `db.*` for an **in-memory fake before `app.main` import** —
  the whole suite runs with no database.
- ⚠️ Never `import tests.conftest` from a test (re-runs the seam swap → mass failures).
