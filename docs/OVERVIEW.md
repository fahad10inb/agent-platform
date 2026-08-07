# ReceptionAI (agent-platform) — The Complete Explainer
*Everything you need to explain this product to anyone — investor, customer, or engineer. Updated 2026-07-06.*

---

## 1 · What it is, in one sentence

**A production SaaS platform that gives any service business — salon, clinic, real-estate agency —
its own AI receptionist that answers customers 24/7, books real appointments, and remembers
returning customers like a human front desk would.**

Live at: https://agent-platform-mivq.onrender.com (landing / dashboard / widget all served from one backend).

---

## 2 · The problem it solves

Small service businesses lose money in three ways:
- **Missed calls = missed bookings** (after hours, during a haircut, on Fridays)
- **Staff time burned** answering the same questions: prices, hours, parking, "can I move my appointment?"
- **Regulars treated like strangers** by generic booking tools — no memory, no warmth

One person can't answer the phone at 11pm. This can.

---

## 3 · What the customer's customers experience (the widget)

A chat bubble on the business's website (or a direct link / iframe embed). It:
- **Answers instantly, 24/7,** in English or Arabic — mirrors whichever the customer uses
- **Knows the business**: services, prices, hours, directions/parking, house policies — because the owner typed them once at onboarding
- **Recommends the right staff member**: "my beard's a mess" → "Tony's your man — he's a wizard with beards"
- **Books real appointments**: real slots computed from working hours, collects name + mobile + reason (UAE front-desk standard)
- **Remembers returning customers**: next visit, "Welcome back, Karim — another fade + beard combo with Marwan?" Every booking becomes memory automatically
- **Verifies identity before revealing anything**: appointment details only after the caller confirms the last-4 digits of the number on file — you can't impersonate someone by knowing their name
- **Survives page reloads** — the conversation restores where it left off
- **Captures leads** when the caller isn't booking (real estate: budget, area, buy/rent)

## 4 · What the business owner experiences (the dashboard)

Sign in with their key and see:
- **The value-proof row**: chats today, chats + questions answered (30 days), bookings, leads, and **estimated staff-hours saved** — the numbers that justify the subscription every time they log in
- **Bookings table** — who, when, phone, reason, live
- **Leads table** — captured enquiries ready for follow-up
- **Settings** — edit everything: tone, services, team & specialties, location, policies, FAQ; changes are live from the next conversation
- **Widget tab** — their shareable link + embed snippet

Onboarding a new business (admin): one 2-minute form in 5 friendly steps — who you are, your hours,
your team ("so the AI can recommend the right person automatically"), where you are, your rules.
Instantly generates the business's private API key (shown once, copy button).

## 5 · How it works (plain-language architecture)

- **One brain, many faces**: a single backend assembles a different persona per business from its
  onboarding data — name, tone, services, staff, policies. Same engine, every tenant sounds like *their* front desk.
- **The pipeline per message**: customer message → load that business's config + that conversation's
  history (from the database — conversations survive server restarts) → build the persona prompt →
  Gemini (Google's LLM) answers, calling *tools* when needed → reply goes back, both turns are saved,
  usage is metered.
- **Tools = real actions, safely scoped**: check availability, book, find/cancel/reschedule
  appointments, remember/recall customers, capture leads. Every tool is locked to one business —
  the AI physically cannot touch another tenant's data.
- **Double-booking is impossible by construction**: a database uniqueness constraint on
  (business, date, time) — two people clicking the same second, exactly one wins. A constraint, not a promise.
- **Memory is automatic**: bookings write memory without the AI having to remember to; notes deduplicate;
  recall powers the "welcome back" moment.

**Stack (if asked):** FastAPI (Python) + Gemini 2.5 Flash with function-calling + Supabase Postgres
(pooled connections) + all three UIs (landing/dashboard/widget) served as self-contained pages from
the same backend. Deployed on Render, auto-deploy from GitHub main.

## 6 · Security & trust (the diligence answers)

- **Multi-tenant isolation**: every row keyed by business; every query scoped; tools closure-bound per tenant
- **Identity before information** (anti-impersonation, above)
- **Auth**: per-business API keys + admin key, constant-time comparison, brute-force throttling on sign-in,
  business IDs can't be enumerated
- **No PII in server logs**; errors never leak internals in production; HSTS everywhere; dashboard
  protected against clickjacking; XSS-safe rendering throughout
- **Cost/abuse guards**: rate limiting, message length caps, LLM timeout/retry/token caps, history caps
- **Metering**: per-business daily usage — the raw material for billing and quotas

## 7 · Engineering discipline (why it won't fall over)

- **41 automated tests** run in CI on every push — auth matrix, tenant isolation, booking races,
  identity verification, metrics, pagination
- Conversations, memory, leads, usage: all durable in Postgres; the platform survives deploys mid-conversation
- Real-world tested: a full simulated company ("The Fade Lab") was onboarded and driven through a
  complete customer journey — which caught and fixed two real bugs (silent booking, empty reply) before any real customer could hit them
- A full industry-standards audit was run; the top items are shipped, the rest are a ranked roadmap

## 8 · Business model (current thinking)

- **Subscription per business** (founding-customer rate-lock framing on the site; final numbers TBD)
- Costs scale gently: roughly $2–3/month of AI cost for a moderately busy business — healthy margin at
  typical SaaS pricing ($49–149/mo range for this category)
- The hours-saved metric on the dashboard is the retention engine: the product re-justifies itself monthly

## 9 · What's honestly not done yet

- **Self-serve signup + billing** (today: admin onboards each business; Stripe integration pending)
- **WhatsApp channel** (the dominant UAE channel; architecture is ready — conversations are durable and
  the chat logic is one extraction away from webhook reuse)
- **Appointment reminders** (needs the send channel above)
- Real testimonials, brand collateral (domain, logo, OG image), analytics
- Key hashing at rest + rotating the committed demo keys; CI-gated deploys; date-typed booking columns
- **Compliance positioning**: UAE health-data localization means clinics need UAE hosting eventually —
  salons and real estate are the compliant first verticals today

## 10 · The one-breath pitch

*"Businesses lose customers every time a call goes unanswered. ReceptionAI gives a salon or clinic its
own receptionist that never sleeps — it answers in English or Arabic, books appointments into real
slots that can't double-book, and greets regulars by name because it actually remembers them. Owners
open their dashboard and see the hours it saved them this month. One form to set up, two minutes,
live on their website the same day."*
