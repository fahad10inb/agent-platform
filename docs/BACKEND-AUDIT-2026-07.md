# Backend audit + next-phase plan — 2026-07-08

Three parallel read-only audits (correctness/concurrency, security, production-readiness)
over `backend/` after the chat-core / WhatsApp / listings work. Findings de-duplicated and
ranked below. Confidence is highest where two audits found the same thing independently.

## The one live P0
**Committed demo-tenant API keys, seeded onto the live system.** `bizkey_*_demo` for the
four demo tenants are git-tracked (repo + test files) and seeded live. Anyone with the repo
can read those tenants' stored names/phones via `/bookings` `/leads`, and overwrite their
settings via `/manage` (redirect `notify_email` / `transfer_number` to themselves). And there
was **no product path to rotate a leaked key**. Real paying tenants use random keys and are
unaffected — but `/chat` defaults `business_id=bright-smile`, so real demo-widget users' data
sits in an exposed tenant. Remediation = add a rotation endpoint + rotate the four live demo
keys + stop the bleeding in the repo.

## P1 — user-visible / cost (fix before first paying customer)
1. **`/chat/history` leaks WhatsApp transcripts** (security + correctness both found it). Route
   is unauthenticated; the WhatsApp path sets `conversation_id = wa-<phone>`, which is
   guessable. Anyone with a phone number + public `business_id` reads the full transcript.
   Fix: reject `wa-*` ids on the public route (one line). ✅ batch 1
2. **Double-booking class** (correctness): a turn that times out *after* a tool executed gets
   blind-retried → booking commits, caller sees an error, re-books; concurrent turns in one
   conversation aren't serialized; WhatsApp webhook has **no duplicate-delivery dedup** (Meta
   redelivers → same message runs twice). Fix: don't retry when AFC history shows executed
   calls; per-conversation `asyncio.Lock`; wamid dedup set/table.
3. **Sync psycopg on the async event loop** (correctness): ~150–300ms loop stall per turn;
   tail case = pool exhaustion freezes the whole process up to 30s. Fix: `asyncio.to_thread`
   around run_turn's DB block + explicit small pool-checkout timeout.
4. **WhatsApp webhook spoofable when `APP_SECRET` unset** (security): forged messages burn
   tokens + poison memory + relay through the tenant's number. Fix: require the secret whenever
   the channel is live — fail closed. ✅ batch 1
5. **No per-business Gemini quota** (all three): per-IP limits only, none on the WhatsApp path;
   one abused `business_id` drains the whole Gemini bill. Also the founding-plan prerequisite.
   Fix: `plan` + monthly cap, checked in `run_turn`, 80% warn → over-cap polite decline.
6. **Prod INFO logs are dropped entirely** (production): no `logging.basicConfig` → every
   `logger.info` breadcrumb never reaches Render logs. Fix: one line. ✅ batch 1

## P2 — correctness / hardening
7. **`reschedule` skips the overlap check** `book` enforces → impossible overlapping bookings.
8. **Lead dedup race**: no unique index on `(business_id, phone_digits)`; duplicate webhook or
   concurrent capture → two rows + two owner emails (the dup it shipped to prevent) or a
   lost-update on enrichment. Fix: unique index + `ON CONFLICT` upsert.
9. **Distillation stops after 40 stored messages**: capped window always holds 20 user turns,
   `20+1 % 6 != 0` forever → WhatsApp regulars stop being learned from. Fix: `COUNT(*)`.
10. **SSRF in the importer**: `_fetch_raw` follows redirects, no host allow-list → an onboarded
    URL can 302 to `169.254.169.254`/localhost. Admin-gated (P2). Fix: block private ranges,
    disable redirects. ✅ batch 1
11. **Prompt injection via imported facts** (owner-trust): mitigated by human review; wrap
    imported facts as unverified.
12. **`phone_last4` gate auto-passes when a booking has no stored phone** → name-only reveal.
13. **Usage day boundary is UTC not Dubai** → first 4h of each day mis-billed / mis-shown.
14. **`uq_booking_slot` failure is silently swallowed** — the actual double-booking guarantee
    could be absent with no log. Fix: log at ERROR. ✅ batch 1
15. **`conversation_id` defaults to `"default"`** → non-widget API callers share one thread.
16. **Import Gemini call has no timeout**; module-level httpx client; unbounded WhatsApp
    fan-out (no per-sender limit, unreferenced tasks can be GC'd). ✅ import timeout in batch 1

## User-action items (I can't do these; they need dashboards / money / accounts)
- **Gate deploys**: Render → Auto-Deploy "After CI Checks Pass" (today CI is post-hoc; red is
  already live). Commit a `render.yaml`. Add ruff to CI.
- **Backups**: Supabase Free has none. Supabase Pro ($25/mo, 7 daily) or a nightly `pg_dump`
  cron. Non-optional at first paying customer.
- **Render Starter** ($7/mo, always-on): fixes WhatsApp cold-start webhook timeouts + the
  sleeping digest scheduler.
- **Sentry free** + **UptimeRobot free** on `/health`.

## Batches (code, by me)
- **Batch 1 — security holes (this phase):** history `wa-*` guard, WhatsApp fail-closed
  signature, admin key-rotation endpoint, SSRF guard + import timeout, `basicConfig(INFO)`,
  un-swallow the booking-index failure. Then rotate the four live demo keys.
- **Batch 2 — reliability:** retry-after-tool guard + per-conversation lock + wamid dedup
  (kills the double-booking class); `to_thread` the DB block; reschedule overlap; lead unique
  index; distillation COUNT(*); Dubai day boundary.
- **Batch 3 — billing/ops floor:** `plan` + per-business quota with grace; token/cost tracking
  into `usage_daily`; PDPL "forget this caller" endpoint + messages retention prune; lock file
  + declare httpx; request-id middleware.
