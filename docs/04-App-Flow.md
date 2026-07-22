# App Flow
### ReceptionAI — end-to-end journeys, step by step

| | |
|---|---|
| **Version** | 1.0 |
| **Note** | Every channel funnels into the same `chat_core.run_turn()` |

---

## 1. The master flow

```
Customer message (WhatsApp / widget)
        │
        ▼
  Webhook / API  ──►  signature + dedup  ──►  chat_core.run_turn
        │                                          │
        │                            ┌─────────────┼─────────────┐
        │                            ▼             ▼             ▼
        │                     human-paused?    over quota?   conversation lock
        │                       (silent)        (decline)     (serialise)
        │                                          │
        │                                          ▼
        │                            build prompt (persona + profile + listings
        │                              + permit gate + compliance rules)
        │                                          │
        │                                          ▼
        │                                  Gemini + TOOLS
        │                     (capture_lead · qualify_lead · check_availability
        │                      · book_appointment · request_human · stop_contact)
        │                                          │
        ▼                                          ▼
   reply delivered  ◄──────────────────  persist (only on success)
                                                   │
                                                   ▼
                                   owner email · CRM push · thread saved
```

---

## 2. Inbound message → reply (the hot path)

1. **Meta delivers** the message to `POST /whatsapp/webhook`.
2. **Verify HMAC signature** — fails closed if the app secret is set. Reject if invalid.
3. **Dedup on `wamid`** — Meta redelivers; a repeat is ACKed and dropped.
4. **Route to tenant** by `phone_number_id` → `business_id`. `conversation_id = wa-<E.164>`.
5. **ACK Meta fast** (they retry on slow responses); do the work in the background.
6. `run_turn`:
   a. **Paused?** (owner took over) → save the customer's message, reply nothing.
   b. **Quota?** over cap → graceful decline, no LLM call.
   c. **Lock** on `(business, conversation)` — two fast messages can't interleave.
   d. Load history → assemble prompt → call Gemini with tools.
   e. **Persist only on success.**
7. **Send the reply** via Graph API (free-form — we're inside the 24h window).

---

## 3. Lead → qualified → booked (the value flow)

| Step | The AI does | System effect |
|---|---|---|
| 1 | Buyer asks about a property | — |
| 2 | Answers **only from real listings**; withholds price if no DLD permit | Permit gate applied at prompt build |
| 3 | Gets name + mobile | `capture_lead` → `leads` row (deduped within 48h) → **owner emailed** |
| 4 | Gathers budget, area, bedrooms, purpose, timeline, payment | `qualify_lead` → `qualifications` upsert + **A/B/C score** → **CRM push** |
| 5 | Offers a genuinely free slot | `check_availability` (hours − booked − buffer − notice) |
| 6 | Books it | `book_appointment` → `bookings` (UNIQUE slot) → **owner emailed** |
| 7 | Buyer asks to negotiate / for paperwork | `request_human` → owner notified, handoff message |

**Scoring:** budget +1 · area +1 · urgent timeline +2 · ready payment +2 →
**A ≥ 4 · B ≥ 2 · C < 2.**

---

## 4. Human takeover

1. Owner opens **Conversations** → a thread → types a reply.
2. `POST /manage/{id}/conversations/{cid}/reply`:
   - saves the message as the business's turn,
   - **pauses the AI** for that conversation (`ai_pauses`),
   - delivers it to the customer via WhatsApp.
3. While paused, `run_turn` returns `""` — the AI stays silent but still records
   whatever the customer says.
4. Owner clicks **Hand back to AI** → `resume` → the AI answers again.

> Known residual: a ~1–3s window where the owner replies *while* a turn is already
> generating — both may answer once. Accepted.

---

## 5. The follow-up loop (background sweeps)

A single in-process scheduler wakes **every 15 minutes**. No cron, no queue. Each
sweep is independently flag-gated and **claims before sending**.

| Sweep | Trigger | Message |
|---|---|---|
| **Reminders** | 24h and 2h before a booking | "Reminder about your viewing tomorrow at 4 PM — reply to confirm or reschedule" |
| **Nurture** | Lead silent at day **2 / 7 / 30** | "Still on the hunt for a 2BR in JVC?" |
| **Review** | After a viewing settles (vertical-timed) | "How did it go? A quick Google review would mean a lot" |
| **Match alerts** | A **permitted listing matches** the lead's stored requirements | "A new 2BR in JVC matching what you were after just came up — want a viewing?" |

**Every sweep skips** a lead who already booked or opted out. All are delivered by
**approved template** outside the 24-hour window.

### Match-alert logic (the "we found you something" flow)
1. For each real-estate tenant, load **permitted** listings only.
2. For each recent qualified lead: skip if booked, opted out, or alerted in the last ~20h.
3. Match on **area** (required, substring both ways) + bedrooms + purpose + budget
   (within ~10%), when the lead specified them.
4. **Claim** `(business, phone, permit_number)` → send **one** best new match.
5. Seed the message into the `wa-` thread so their reply re-qualifies normally.

---

## 6. Portal lead intake (speed-to-lead)

1. Agency forwards Bayut / Property Finder / Dubizzle lead emails to
   `leads+<token>@<domain>`.
2. Their email provider POSTs it to `POST /leads/ingest` (token-gated).
3. `parse_portal_lead` detects the source and pulls name / mobile / message.
4. Dedup on phone → save or enrich the lead → **owner alerted instantly**.
5. **Instant outreach** to the buyer, and the opener is seeded as the model's turn so
   their reply flows through normal qualification.

---

## 7. Bookings → the owner's real calendar

- **Per booking:** "+ Calendar" downloads a one-off `.ics` → opens in any calendar. *Instant.*
- **Whole calendar:** a token-gated `.ics` **feed URL** pasted into Google Calendar
  ("From URL") stays updated.

⚠️ Google polls subscribed feeds **slowly (hours)** with no manual refresh — the
per-booking invite is what makes a fresh viewing appear immediately.
⚠️ The feed must **not** carry a UTF-8 BOM: Google's parser silently drops the whole
calendar if the body doesn't start with `BEGIN:VCALENDAR`.

---

## 8. Onboarding a new agency (~15 min)

1. **Dashboard → Add a business** — or paste their **website URL** and the importer
   auto-fills the form (name, type, hours, services, team, areas, focus, languages, ORN).
2. Review → **Create** → their API key is shown **once**.
3. Fill: listings (paste or CSV/XML/Reelly import), hours & booking rules, transfer
   number, after-hours mode, owner alert email.
4. Connect **WhatsApp**: set their `whatsapp_phone_id`, subscribe their WABA to the app.
5. Optional: CRM webhook, Google review link, calendar feed.
6. **Test end-to-end**: message the number → AI replies, captures, books; owner alerted.
