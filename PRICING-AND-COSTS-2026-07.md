# Pricing, WhatsApp setup & running costs (2026-07-08)

USD ≈ AED 3.67. Confirm current Gemini/WhatsApp rates before quoting a customer — they change.

# PART 1 — WHAT YOU CHARGE (pricing)

Model: **subscription SaaS** — one product, each agency pays monthly. Flat per agency (not
per-seat, not per-minute). Anchor against the AED 45–60k/yr agencies already pay Bayut/PF, and
against one missed deal a year.

| Plan | Who | Price | Included |
|---|---|---|---|
| **Founding pilot** | first customers | **Free 2 weeks → AED 500–750/mo** | Full product, 1 WhatsApp number + widget, capped volume — so the pilot is real |
| **Starter** | solo–4 agents | **~AED 749/mo (~$205)** | Widget + WhatsApp, EN/AR, qualify + score + listing-match + book + reminders + inbox, fair lead cap |
| **Pro** | 5–15 agents | **~AED 1,499/mo (~$410)** | Higher volume, multi-agent alerts, priority support |
| **Developer / large brokerage** | off-plan developers, 50+ agent firms | **AED 60k–200k/yr, or per-launch AED 15–40k** | Everything + higher volume + (as built) voice/integrations/dashboards |

Rules: bundle the WhatsApp message fees (most inbound is free — see Part 3), quote a flat number,
add overage only above the cap. The "obviously yes": *priced below one part-time coordinator and
below one missed deal a year.*

# PART 2 — WHATSAPP SETUP (the guide)

The platform is READY (webhook wired, `whatsapp_phone_id` field live). You plug in 4 things.

## Phase A — free test number (for demos; ~30 min, no cost, no SIM)
1. **developers.facebook.com** → create app → type **Business**.
2. Add the **WhatsApp** product. Meta gives you: a free **test number**, a temporary **access
   token**, and a **phone_number_id**.
3. On **Render → Environment**, add:
   - `WHATSAPP_ACCESS_TOKEN` = the token
   - `WHATSAPP_VERIFY_TOKEN` = any string you invent (e.g. `sky-verify-8842`)
   - `WHATSAPP_APP_SECRET` = Meta app → Settings → Basic → App Secret
4. In the app's **WhatsApp → Configuration → Webhook**:
   - Callback URL: `https://agent-platform-mivq.onrender.com/whatsapp/webhook`
   - Verify token: the same string from step 3
   - **Subscribe to the "messages" field.**
5. **Dashboard → Settings → WhatsApp field:** paste the **phone_number_id**.
6. Add your own phone as a **test recipient** (up to 5), message the test number → the AI replies.
   Read the thread in the **Conversations tab**. Done.

Note: the test token expires in 24h — for anything lasting, generate a "System User" token (Meta
walks you through it).

## Phase B — outbound delivery (reminders/nurture/auto-outreach)
Business-initiated messages outside the 24h window need a **pre-approved utility template**:
**Meta Business Manager → WhatsApp Manager → Message Templates → new Utility template → submit**
(approved in ~1–2 days). Inbound demos DON'T need this.

## Phase C — going live for a real agency
- **Get a number:** the number must NOT be on the normal WhatsApp app. Use a **fresh SIM** (cheap
  spare Du/Etisalat) or the agency's dedicated number.
- **Business verification** with the agency's trade license (2–5 days). Done when you sign them.

# PART 3 — WHAT IT COSTS YOU TO RUN

## Fixed monthly (regardless of customers)
| Item | Cost | Notes |
|---|---|---|
| Render **Starter** | **~$7/mo (AED 26)** | Always-on — kills the demo cold-start. Get this. |
| Supabase | **$0** free tier → **$25/mo** Pro | Pro when you need daily backups (first paying customer) |
| Domain | **~AED 50/yr** (~AED 4/mo) | one-time-ish |
| Resend (owner emails) | **$0** free (3k/mo) → $20/mo | free tier covers early |
| **Fixed total** | **~$10–55/mo (AED 40–200)** | tiny until real scale |

## Per-use (the variable costs)
**Gemini 2.5 Flash** (the AI replies): $0.30 / 1M input tokens, $2.50 / 1M output.
- One chat turn ≈ **$0.0015** (persona + listings + history in, short reply out; prompt-cached).
- A full lead conversation (~10 turns) ≈ **$0.02**.
- So **1,000 lead conversations ≈ $20 (AED ~75)/month.** Background jobs run on cheaper Flash-Lite
  — negligible. **Gemini is cheap.**

**WhatsApp (Meta)** — the cost to actually WATCH:
- **Inbound** (customer messages first, 24h window): **FREE** — until **Oct 1 2026**, then ~AED
  0.15–0.20. Most receptionist traffic is inbound, so this is your friend.
- **Outbound utility templates** (reminders/nurture/outreach): **~AED 0.15–0.20 each.**
- **Marketing templates** (blasts — avoid): ~AED 1.20–1.45 each.

## Cost to serve ONE agency (so you know your margin)
| Agency size | Gemini | WhatsApp outbound | **All-in cost/mo** | Pays | Margin |
|---|---|---|---|---|---|
| **Small** (~200 leads/mo) | ~AED 15 | ~AED 40–80 | **~AED 55–95** | AED 749 | **very healthy** |
| **Busy** (~1,500 leads/mo) | ~AED 90 | ~AED 300–500 | **~AED 400–600** | AED 749 | thin → raise price or cap |
| **Developer** (huge volume) | ~AED 500+ | ~AED 1,500+ | **~AED 2,000+** | AED 5k–17k/mo | healthy |

Takeaway: **outbound WhatsApp templates are the main variable cost**, and they scale with volume.
A small agency is cheap to serve (great margin on AED 749); a very busy one needs Pro/volume
pricing so cost doesn't eat the flat fee.

## MAXIMUM cost — the worst case, and why it can't run away
- **Per customer, capped by design:** the per-business **monthly quota** (already built) stops any
  one tenant — abused, viral, or just huge — from blowing up your Gemini bill. Over the cap it
  declines gracefully. So **your cost per customer is bounded** by whatever cap you set on their plan.
- **Realistic max per busy agency:** ~**AED 500–800/mo** (Gemini + heavy outbound). That's the
  number that says "a very high-volume client must be on Pro or a volume plan, not Starter."
- **Your total exposure at, say, 20 small agencies:** fixed ~AED 200 + ~20 × ~AED 75 ≈ **~AED
  1,700/mo (~$460)** to serve, against ~20 × AED 749 ≈ **AED 15,000/mo revenue.** Comfortable.
- **The one thing that could spike it:** WhatsApp **marketing** blasts (AED 1.2–1.45 each) — so
  keep outbound to **utility** templates and opt-in nurture, never mass marketing. That, plus the
  Gemini quota, means there is **no realistic runaway** cost.

## Bottom line
Cheap to run, especially at your target (small agencies): **~AED 55–95/month to serve, on AED 749
revenue.** The costs to watch are outbound WhatsApp (keep it utility/opt-in) and Gemini on an
abused tenant (already fused by the quota). Fixed infra is ~$10–55/month total. You are not
exposed to a big bill you can't cap.
