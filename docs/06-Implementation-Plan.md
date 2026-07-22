# Implementation Plan
### ReceptionAI — what's built, what's left, and the path to the first paying client

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Product complete · **0 paying customers** |
| **Tests** | 285 passing |

> **The honest headline:** the engineering is essentially done. The remaining work is
> **not code** — it's a first customer, and the ~1 hour of setup that unlocks them.

---

## 1. Where we are

### ✅ Phase 1–5 — complete (shipped & live)

| Phase | Delivered |
|---|---|
| **1. Core engine** | Multi-tenant FastAPI + Gemini brain, per-business persona, function-calling tools, durable conversations |
| **2. Booking** | Real availability from the agency's hours, buffers, notice windows; **double-booking impossible**; reschedule/cancel/confirm |
| **3. Channels** | Website widget + **WhatsApp Cloud API** (verified working end-to-end), voice scaffold (off) |
| **4. Real-estate depth** | Portal lead intake · qualification + A/B/C scoring + CRM write-back · permit-gated listing matching · nurture cadence · compliance guardrails |
| **5. Retention & ops** | Reminders · review requests · **requirement-match alerts** · human takeover · calendar feed · owner dashboard · agency profile |

### 🔒 Hardening — complete
API keys hashed · webhook HMAC (fails closed) · SSRF guards · tenant isolation (403) ·
per-conversation locking · monthly quota fuse · PDPL opt-out + erasure ·
persist-only-on-success · CI-gated deploys · 285 tests.

---

## 2. What's actually left

### 🔴 Blocking a real customer — **ops, not code**

| # | Item | Owner | Why it blocks |
|---|---|---|---|
| 1 | **Render always-on plan** ($7/mo) | You | Free tier sleeps → cold start → **Meta's webhook times out and drops the customer's message**. Unacceptable for a paying client. |
| 2 | **Real WhatsApp number + Meta Business Verification** | You + client | The test number only messages **5 pre-approved** phones. Use the **client's trade licence** — you don't need your own. |
| 3 | **Approved message templates** | You (Meta) | Outside the 24h window, only an approved template delivers. Without it, reminders/nurture/match alerts don't reach a cold lead. |
| 4 | `ENVIRONMENT=production` · `WHATSAPP_APP_SECRET` · remove `WHATSAPP_SKIP_SIGNATURE` | You | Prod hygiene + the webhook is currently forgeable |
| 5 | `RESEND_API_KEY` | You | Owner email alerts only *log* without it |
| 6 | **Supabase backups** (Pro or pg_dump) | You | Real customer data must be recoverable |

### 🟠 Remaining code — small and sequenced

| Item | Effort | When |
|---|---|---|
| **Wire template variables** to the approved template's exact shape | ~10 min | The day template #1 is approved — *deliberately deferred*, since Meta dictates the variables and guessing means building twice |
| Turn on `match_alerts_enabled` + tune matching on real inventory | small | Pilot week 1 |
| Sentry DSN | 2 min | Anytime |

### 🟢 Post-first-customer
Billing/subscription · Arabic voice channel · developer/off-plan mode ·
multi-agent routing + SLA dashboards · deeper portal/CRM integrations.

---

## 3. Path to the first customer

```
   Outreach  ──►  reply  ──►  /watch link  ──►  live /demo call  ──►  free 2-week pilot
                                                                            │
                                                     ┌──────────────────────┘
                                                     ▼
                                 setup day (~1hr): Render always-on · their number
                                 + verification · onboard tenant · listings · test
                                                     │
                                                     ▼
                                          pilot runs on real leads
                                                     │
                                                     ▼
                                        convert → AED 1,499/month
```

**Rule: spend nothing until someone says yes.** No permit, no number, no paid plan
bought speculatively. Every 🔴 item above is triggered *by* a signed pilot.

### Setup-day checklist (~1 hour)
1. Flip Render to always-on.
2. Client's WhatsApp number → Meta Business Verification (their trade licence).
3. Onboard the tenant (paste their website → auto-fill → review).
4. Import listings (CSV / sheet / XML / Reelly) — **check permit numbers are present**.
5. Set `whatsapp_phone_id`, subscribe their WABA, point the webhook.
6. Fill the agency profile (areas, focus, languages, ORN), hours, transfer number.
7. Owner alert email, CRM webhook, review link, calendar feed.
8. **End-to-end test** from an outside phone.

---

## 4. Pilot success criteria (2 weeks)

| Metric | Target |
|---|---|
| Enquiries answered | **100%** |
| Median first response | < 30s |
| Leads captured vs enquiries | > 80% |
| Viewings booked by the AI | ≥ 1 (proves the loop) |
| Unpermitted prices quoted | **0** |
| Owner intervention needed | Rare (takeover used, not required) |

**Convert when:** the owner can point to one deal they'd otherwise have missed.

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| **Cold-start drops WhatsApp messages** | Always-on plan (🔴 #1) — non-negotiable before a pilot |
| **Template rejected by Meta** | Templates are configurable per message kind; free-form still works inside 24h |
| **Match alerts feel spammy** | Permit-gated, real-match-only, once-per-property, ~1/day throttle, opt-in flag — and measurable on pilot #1 |
| **Portals ship their own AI** | Go where they won't: the agency's *own* number, their inventory, their CRM |
| **Compliance breach** | Permit gate enforced in the prompt layer (price withheld, not "asked nicely"); escalation rules for negotiation/legal |
| **Single-founder bus factor** | Docs (this set), 285 tests, one storage seam |

---

## 6. Engineering conventions (for anyone picking this up)

- `db.py` is the **only** place SQL lives. Keep it that way.
- Adding a tenant field? Add it to **`_EDITABLE_BUSINESS_FIELDS` *and* the `/manage`
  response whitelist** — otherwise it saves but reads back empty.
- All outbound sends must **claim a UNIQUE row first**. No exceptions.
- Never blind-retry a tool turn (a booking may already have committed).
- Tests swap the DB seam **before** importing `app.main`; never import `conftest`
  from a test.
- Push to `main` deploys. CI gates it.
