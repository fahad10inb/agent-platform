# Product Requirements Document (PRD)
### ReceptionAI — AI Receptionist for Dubai Real-Estate Agencies

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Built — pre-first-customer |
| **Owner** | Fahad |
| **Live** | https://agent-platform-mivq.onrender.com |

---

## 1. Summary

An AI receptionist that answers a real-estate agency's WhatsApp and website chat
**instantly, 24/7** — qualifying buyers, matching them to real listings, booking
viewings, and escalating to a human when the law requires it.

**One-line pitch:** *You pay the portals AED 45–60k a year for leads, then lose half
of them because nobody answered fast enough. This makes sure you never lose a lead
you already paid for.*

---

## 2. The problem

A Dubai brokerage buys leads from Bayut / Property Finder / Dubizzle at
**AED 45–60k per year**. Those leads arrive at all hours. But:

- An enquiry at 11pm sits until morning. By then the buyer has messaged four other
  agencies — **the first to reply usually wins the deal**.
- Agents are on viewings, driving, or handling three chats at once.
- Junior staff answer inconsistently, quote prices on unpermitted listings
  (a **DLD compliance breach**), or forget to follow up.
- A single lost deal is **~AED 40,000** in commission on a 2M sale at 2%.

The loss isn't "we didn't get leads." It's **"we didn't answer the leads we bought."**

---

## 3. Target user

### Primary persona — "The Principal Broker"
- Owner / MD of a **10–50 agent** independent Dubai brokerage.
- Buys portal leads, feels the waste, but can't justify a night receptionist.
- Decides alone. No procurement, no IT department.
- Cares about: **commission saved**, not "AI".

### Secondary
- **Larger brokerages (50–500 agents)** — longer sales cycle, more stakeholders.
- **Off-plan / developer master-agencies** — highest value (launch days generate
  thousands of leads in hours), but a longer, more bespoke sale.

### Not the user (deliberately)
- Walk-in retail businesses, restaurants, anyone without a lead-response problem.
- **Clinics/dental** — held back: UAE health-data localization would require
  in-country hosting we don't have. (See §7.)

---

## 4. Goals & success metrics

| Goal | Metric | Target |
|---|---|---|
| Never lose a paid lead | % of enquiries answered | **100%**, any hour |
| Answer before competitors | Median first-response time | **< 30 seconds** |
| Turn enquiries into pipeline | % of enquiries captured as a lead | > 80% |
| Save agent time | Hours/month not spent on first-touch | measurable in dashboard |
| Stay legal | Unpermitted listings quoted | **0** (hard-enforced) |
| Commercial | Paying agencies | **1** (first pilot) → 10 |

---

## 5. Scope

### P0 — Built and shipped
| Feature | What it does |
|---|---|
| **Instant answering** | WhatsApp + website widget, same brain, 24/7 |
| **Lead capture** | Name + number saved the moment intent appears; deduped |
| **Qualification & scoring** | Budget, area, bedrooms, purpose, timeline, payment → **A/B/C grade** |
| **Real-inventory matching** | Shortlists from the agency's *actual* listings — never invents a property |
| **Permit gate (DLD)** | An unpermitted listing's price is **withheld from the AI entirely** |
| **Viewing booking** | Real free slots from the agency's hours; **double-booking impossible** (DB constraint) |
| **Bilingual** | English + Arabic, switches mid-conversation |
| **Human handoff** | Price negotiation, paperwork, legal → routed to a licensed agent |
| **Human takeover** | Owner replies in a thread → AI pauses for that conversation |
| **Owner dashboard** | Bookings (calendar view), leads, conversations, settings, KPIs |
| **Calendar feed** | `.ics` subscription + per-booking invite → bookings land in their real calendar |
| **Follow-up loop** | Reminders (24h/2h), nurture (day 2/7/30), **requirement-match alerts** |
| **Review requests** | Post-viewing Google review ask |
| **CRM write-back** | Qualified leads pushed to Bitrix24 / Zoho / any webhook |
| **Portal lead intake** | Forwarded Bayut/PF emails → parsed → instant outreach |
| **Agency profile** | Areas covered, sale/rent/off-plan focus, languages, **RERA ORN** |

### P1 — Next
- WhatsApp **approved message templates** wired to exact variables (delivery outside 24h).
- Arabic **voice** channel (scaffolded, off).
- Billing / subscription.

### P2 — Later
- Developer / off-plan launch mode (high-value).
- Multi-agent routing + SLA dashboards.
- Deeper portal/CRM integrations.

### Non-goals
- Replacing licensed agents (legally impossible, and not the pitch).
- Being a CRM. We're the **front door**; we push out to their CRM.
- Cold outbound marketing blasts (TDRA/PDPL risk).

---

## 6. Key user stories

1. *As a buyer,* I message at 11pm and get a real answer in seconds, so I don't
   message a competitor.
2. *As a buyer,* I'm asked a few natural questions and offered a viewing time that
   actually exists.
3. *As an owner,* every enquiry becomes a named, scored lead I can see the next morning.
4. *As an owner,* I get an email the instant a lead or booking arrives.
5. *As an owner,* I can take over a conversation myself and the AI steps aside.
6. *As an owner,* bookings appear in my normal calendar without me copying anything.
7. *As an owner,* a lead who went quiet gets nudged, and gets told when a matching
   property appears — without me remembering.
8. *As a compliance-conscious owner,* the AI never quotes a price on a listing
   without a valid permit.

---

## 7. Constraints & compliance

| Constraint | Implication |
|---|---|
| **DLD / Trakheesi permits** | Advertising a property without a permit is illegal → hard permit gate in the prompt layer |
| **Licensed-activity boundary** | No negotiation, no legal/tax advice, no mortgage qualification → escalate to human |
| **UAE PDPL** | Opt-out honoured (`stop_contact`); data-erasure endpoint |
| **WhatsApp 24-hour rule** | Business-initiated messages outside 24h require an **approved template** |
| **Health-data localization** | Blocks the clinic vertical until in-country hosting |
| **TDRA** | No cold marketing blasts; follow-ups are service follow-ups to inbound leads |

**Claims we must never make:** RERA/DLD endorsement, "data stays in the UAE",
"native Emirati Arabic", partnership with Bayut/Meta, or outcome statistics as our own.

---

## 8. Commercial

- **Pricing:** AED 1,499/month. Free 2-week pilot on their real leads, no card.
- **Anchor:** vs AED 45–60k/yr portal spend, and ~AED 40k commission on one saved deal.
- **Motive:** one saved deal pays for the year twice over.

---

## 9. Open questions

1. Which template wording will Meta approve (dictates the follow-up copy)?
2. Does the requirement-match alert convert, or annoy? (Measure on pilot #1.)
3. Is AED 1,499 under-priced for agencies where one deal = AED 40k?
