# Feature roadmap — 2026-07-08 (research-backed)

Market read: the receptionist/voice incumbents (Rosie, Smith.ai, Goodcall, Vapi, Retell)
win the **conversation**; the vertical booking platforms (Fresha, Simplybook, Zenoti) win
**retention** — reminders, deposits, reviews, loyalty, reactivation. We've built a strong
conversation layer. **Our gap and our moat are the retention layer**, and it's mostly
cron + WhatsApp + Resend + Supabase — squarely in solo-dev reach.

## Shipped (2026-07-10)
- ✅ **Appointment reminders + two-way confirm** (#1) — the 24h/2h sweep is live.
- ✅ **Post-visit Google review requests** (roadmap #2). `review_service.py` sweep +
  per-business `google_review_url` + `/admin/send-review-requests`. Timed per vertical
  (salon 2h, clinic 24h), once per booking, skips no-link / opted-out / cancelled.
- ✅ **Human takeover / supervised mode** (roadmap #5, "do #3" in the working list).
  Owner replies from the inbox → the AI pauses for that thread (`ai_pauses`), delivers
  over WhatsApp, "Hand back to AI" resumes. Endpoints: `/manage/{id}/conversations/{cid}/`
  `reply` · `resume` · `status`.
- 🟡 **Arabic voice channel — SCAFFOLD** (working-list #1). Arabic *text* was already
  live (prompt mirrors the caller's language). The phone channel's server side is now
  built + tested behind `VOICE_ENABLED` (default off) — see VOICE-PLAN-2026-07.md "Build
  status". Going live needs Twilio/Deepgram/ElevenLabs accounts + a real call to verify.
- **Next up:** deposits/payment links (#3), Google Calendar sync (#4), and the working
  list's #2 (developer/off-plan mode). Finish voice when the accounts are ready.

## TOP 5 — build next (one coherent "retention core": show up → pay → get reviewed → stay booked → owner in control)
1. **Appointment reminders + two-way confirm/reschedule** (quick win). Cron → WhatsApp
   utility template (+ Resend fallback) at 24h/2h; reply 1=confirm, 2=reschedule routes
   into the existing booking engine. No-shows eat 15-20% of weekly revenue at UAE salons;
   reminders+deposits cut them 30-40%. Utility msgs are cheap / free in the 24h window.
   Needs: `scheduled_messages` table + a Render cron worker + one approved template.
2. **Post-service review-request → Google** (quick win). On booking "completed", fire a
   WhatsApp/SMS with the business's Google review deep link (1-2h salons, 24-48h clinics).
   95-98% open; 2-3x more reviews; the most *visible* owner ROI; feeds the digest.
   Needs: a trigger + template + per-business review-link field.
3. **Deposits / payment links — Ziina-first, Stripe fallback** (medium). Ziina is UAE-native
   (Payment Intent API, links, SVF-licensed, can send pay requests in WhatsApp). Confirm
   booking only on paid. The other half of no-show reduction; turns "nice bot" into "saves
   me money". TRAP: do NOT use Tabby/Tamara BNPL for deposits — wrong instrument.
4. **Google Calendar two-way sync** (medium). OAuth per business; push bookings, read busy
   blocks so the AI never books over their real calendar. The #1 *adoption/trust* unblocker.
5. **Supervised mode (AI drafts → owner approves)** (medium). Auto-send high-confidence
   reversible replies; queue pricing/medical/complaints for one-tap approval. Unlocks
   clinics and cautious owners; a genuine differentiator vs fully-autonomous rivals.

## Also strong (medium)
- **Waitlist / cancellation auto-fill** — convert empty chairs; reuse the no-double-book lock.
- **WhatsApp Flows** — native in-chat date/slot picker (55-80% completion vs external forms).
- **Reactivation / win-back** for lapsed clients — 25-40% reactivation. TRAP: this is
  *marketing*, so TDRA/PDPL bites hard — needs a real consent ledger + opt-out + quiet hours
  (no promo 21:00-07:00) + marketing templates. Fines up to AED 150k-400k/message. The
  compliance plumbing is the actual project; build it before any outbound marketing.
- **Instagram DM** — same Meta Graph stack; TRAP: 24h window + IG API rate limits cut ~96%.
- **Daily-check analytics** — a glanceable daily snapshot tied to AI-attributed recovered
  revenue; the number an owner opens every morning = the anti-churn.

## Big bets (defer until the retention core is banking)
- **Voice channel** (see VOICE-PLAN-2026-07.md) — the shiny incumbent category; the only item
  that can consume a solo dev whole. Do it after reminders/deposits/reviews are live.
- **Outbound AI voice**, **deep POS/CRM integrations** (TRAP: those platforms are competitors'
  booking engines — be the AI front door and push out via Calendar + webhook/Zapier instead),
  **AI review-reply drafts** (TRAP: needs allowlisted Google Business Profile API; Google is
  shipping its own).

Recommendation: ship #1 and #2 first (days each, highest visible ROI), then #3/#4/#5.
