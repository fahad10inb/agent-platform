# Real-estate AI operator — strategy & build blueprint (2026-07-08)

Two research passes (workflow map + competitive/pricing), de-duplicated. Real estate is the
flagship vertical to go deep on; home-services is the concrete "small business" second;
appointment-salons/spas are a later volume tier; dental (needs UAE hosting) and legal are held.

## The thesis
In Dubai/Abu Dhabi the licence gate is on the **activity** (mediating, representing,
negotiating, advertising) — not the job title. So an AI can legally OWN the entire **top and
middle of the funnel** (intake → qualify → match → schedule → nurture) and must hand the
**transaction/representation** to a licensed human. The biggest ROI beyond "answer the enquiry"
is **speed-to-lead + structured qualification + real-inventory matching + relentless nurture** —
exactly what human agents are provably bad at (avg first response ~42h; ~23% of leads never
answered — HBR 2011).

## Why an agency chooses us (the honest wedge)
NO single feature is a moat — instant bilingual WhatsApp reply is table stakes (SleekFlow, Wati,
Respond.io, Vapi, Retell, GHL setups all claim it). The real, defensible wedge is **productized
fit + packaging + price for the small 3–10 agent agency** that's too small for Salesforce/
PropSpace and too busy to assemble Vapi+GHL+Twilio+CRM themselves: one ready-made, self-serve,
real-estate-aware, bilingual, WhatsApp-native operator that **matches THEIR listings** and plugs
into the CRM they already run — no migration. Market: ~29,577 Dubai brokers, thousands of small
agencies already paying AED 45–60k/yr to Bayut/PF just to GET leads, then responding by hand.

Differentiators, honestly ranked:
- **TRUE EDGE (lead with):** self-serve/live-same-day (no integration project); flat per-agency
  price (vs per-seat/per-minute/per-MAC+WA-fee stacking); the whole loop in one light product;
  no CRM to rip out (integrates, not replaces).
- **VALIDATE, don't overclaim:** Arabic — say "handles Arabic and English naturally, including
  mixed messages"; NEVER "native Emirati Arabic" (Gulf dialect is hard for LLMs; dies in the demo).
- **TABLE STAKES (don't lead with):** "instant response", "WhatsApp-first", "remembers leads".

Sell to the **owner/principal broker** (holds budget; commission-only agents churn). Close with a
**live pilot on their real leads**, not a deck.

## Pricing (flat per-agency, never per-seat/per-minute)
- Founder pilot: free 2 weeks → AED 500–750/mo
- Starter (solo–4 agents): ~AED 749/mo
- Pro (5–15 agents): ~AED 1,499/mo
Anchor against the AED 45–60k/yr portals and one missed ~AED 30k commission ("below one
part-time coordinator and below one missed deal a year"). Bundle WhatsApp fees (most replies fall
in the free 24h window) — kills the "surprise fees" objection agencies have with Wati/SleekFlow.

## The workflow, mapped OWN / ASSIST / HUMAN-ONLY
OWN (AI end-to-end): lead intake (all sources) · <5-min first response · qualification ·
match to permit-valid listings · book viewing · post-viewing follow-up · past-client nurture ·
(rental) same top-funnel + Ejari/Tawtheeq renewal nurture.
ASSIST (AI drafts, human approves): mortgage RULE explainer (route to broker) · snagging/handover
scheduling · seller valuation-request intake + comps prep · Trakheesi/Madhmoun permit application prep.
HUMAN-ONLY (legally gated): conduct viewing · offer/negotiation · Form A/B/F + MOU + deposit ·
NOC/DLD transfer/title · winning a listing + valuation sign-off · signing/registration.

## Qualification schema (the AI's core job — PF Partner Hub mandates BANT+CHAMP)
Buyer/tenant required fields: budget RANGE + pay method (cash vs mortgage + pre-approval status);
purpose (end-use/investment/holiday); 2–3 target areas; type (apt/villa/TH × ready/off-plan ×
primary/secondary); beds + must-haves; timeline/urgency ("what prompted you now?"); decision-makers;
residency/visa (drives LTV — non-resident ~50–60% vs resident 80%). Keep it consultative, not an
interrogation. Score A (hot ~5% conv) / B (early ~2%, but the VOLUME where deals hide → nurture) /
C (nurture, don't force).
Seller/landlord: motivation ("why now"); price expectation; timeline; property status (vacant vs
tenanted/Ejari, mortgage/NOC, title in hand); exclusivity (max 3 brokers).

## Listings data — realistic integration path (ranked)
1. **Google Sheet / CSV** — MVP default; small shops keep inventory here. Add to website-import onboarding.
2. **Agency's existing XML feed URL** — if they syndicate to any portal, their CRM already emits it
   (ref, permit no, price, beds, community, images). Caveat: PF is sunsetting XML for a gated API.
3. **Open CRM API** — Bitrix24 (full REST+webhooks), Pixxi, Behomes, Zoho. Best freshness.
4. **Reelly API** — the one genuinely open data layer: token REST, Swagger+sandbox, 1,800+ off-plan
   projects w/ unit availability + payment plans + DLD history; **free 20-project key** to prototype.
5. **Direct portal API — avoid** (PF Enterprise needs partner app + security audit; Bayut has none).
Architecture: normalize {Sheet, CSV, XML, CRM, Reelly} → one canonical schema keyed on
**permit_number** (also the dedup + compliance key). Corrections: PropSpace was divested by PF in
2024 (independent now); Bayut+Dubizzle share one backend/feed.

## Regulatory lines the AI must NOT cross (build as hard code)
- NEVER publish/send any listing/ad (incl. WhatsApp/social) without an injected valid **Trakheesi
  (Dubai) / Madhmoun (Abu Dhabi, mandatory since Jul 2025) permit number + broker BRN** — hard-block.
  (Fines from AED 50k → AED 1M + licence suspension; DLD fined 22 firms AED 900k in one sweep.)
- NEVER negotiate, quote/commit price or terms, represent a party, fill Form B/F, or accept commission.
- NEVER give legal/contract advice or speculate on escrow/financing/ROI/handover dates.
- NEVER pre-qualify a SPECIFIC person for a mortgage ("you qualify for X") — quote the RULES only
  (80% LTV resident, 50% DBR cap) and route to a broker.
- Claims allowlist: no "guaranteed yield / best deal / handover in 30 days" unless verified from data.
- ALLOWED safe lane: general facts (4% DLD fee, what Ejari is, process steps), FAQ, capture,
  qualification, scheduling, surfacing a PERMITTED listing's price/specs.
- Liability sits with the brokerage (the data controller), not us — but enforce PDPL (opt-in,
  honoured STOP, approved templates, audit logs) and disclose the user is talking to an AI.

## The 5 modules to build first (beyond reception)
1. **Portal lead-intake + instant-qualification pipe** — connect real Bayut/PF/Dubizzle leads
   (universal email-parse fallback + WhatsApp BSP webhook) so the <5-min response fires on ACTUAL
   portal leads, not just widget chats. Highest ROI, moderate effort. The whole speed-to-lead thesis.
2. **Structured qualification schema + A/B/C scoring + CRM write-back** — turn the persona chat into
   a BANT/CHAMP form-filler that scores and writes back to Bitrix24/Zoho. Moderate effort; sticky + measurable.
3. **Real-inventory matching engine (permit-gated)** — normalizer over {Sheet, CSV, XML, Reelly}
   keyed on permit_number. Start with Reelly's free 20-project key for off-plan. Higher effort.
4. **Long-horizon nurture cadence engine** — extend reminders into scored silence-triggered
   sequences (post-viewing → 7-day → monthly market update → Ejari-renewal/anniversary). Low effort,
   high ROI — where B-lead volume converts and referrals come from.
5. **Compliance guardrail layer** — permit-number gate on any listing send + hard-escalation
   triggers (price/negotiation/contract/legal/mortgage-prequal → named licensed human) + claims
   allowlist + PDPL opt-in/out + AI disclosure. Non-negotiable; the licence to operate + a real edge.

## Claims to NOT make
No RERA/DLD compliance/endorsement · no "data stays in the UAE" (we're not UAE-hosted) · no "native
Emirati Arabic" · no proven-outcome stats ("21× / 3× more deals") as OUR result (cite speed-to-lead
as attributed industry research only) · no "replaces your agents" · no implied Meta/Bayut/PF
partnership · no uptime SLA a solo founder can't back.

## Honest hard parts / open items to verify
(a) Getting LIVE accurate inventory from small shops (Sheets go stale, portal APIs gated) — freshness
will be the recurring complaint. (b) Portal lead access without a partnership — email-parse is
brittle. (c) The compliance line is inferred from activity-based law, not an AI-specific statute — be
conservative, keep a human on anything transactional. (d) Crowded field (Ruby CRM, PropCRM ~60s
auto-reply, GHL resellers, portal-native Bayut SmartLeads/PropSpace) — the only durable moat is being
the lightweight operator that integrates with what they already run + the memory/scheduling/bilingual
quality already built. **Verify before quoting publicly:** our actual Gulf-Arabic quality on real
dialect messages; LugarApp pricing/AI depth; PropSpace per-seat pricing.

## Stats provenance (cite the solid, avoid the folklore)
SOLID: MIT/InsideSales 2007 (5-min response ≈ 21× qualify odds); HBR 2011 (42h avg first response,
23% never answered, 1h = 7× vs waiting); Drift 2017 (only 7% respond <5min); Bayut Academy (A ~5%,
B ~2%); PF SLA (respond <5min business hours). AVOID as fact: "80% of sales need 5 follow-ups"
(fake "NSEA" org), "78% work with first responder", "WhatsApp 98% open rate", precise after-hours %.
Direction is bulletproof; many circulated numbers are junk.
