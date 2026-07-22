# ReceptionAI — Documentation

**An AI receptionist for Dubai real-estate agencies.** It answers WhatsApp and website
chat instantly 24/7 — qualifying buyers, matching them to real (permit-checked)
listings, booking viewings, and escalating to a licensed human when the law requires it.

**Live:** https://agent-platform-mivq.onrender.com

---

## The document set

Read in order if you're new. Jump straight to the one you need if you're not.

| # | Document | Read it if you want… |
|---|---|---|
| 1 | **[PRD](01-PRD.md)** — Product Requirements | *Why* this exists: the problem, the user, the features, the money, the compliance limits |
| 2 | **[TRD](02-TRD.md)** — Technical Requirements | The architecture, stack, engineering contracts, integrations, security |
| 3 | **[UI/UX Design](03-UI-UX-Design.md)** | Every screen, the design system, interaction + accessibility rules |
| 4 | **[App Flow](04-App-Flow.md)** | Step-by-step journeys: a message → a booked viewing → the follow-up loop |
| 5 | **[Backend Schema](05-Backend-Schema.md)** | Every table, column, constraint — and *why* each guarantee exists |
| 6 | **[Implementation Plan](06-Implementation-Plan.md)** | What's built, what's left, and the path to the first paying client |

**Also here:** [`how-it-works.html`](how-it-works.html) — a 26-slide visual explainer
(open it in a browser; arrow keys to navigate). Plain-English walkthrough plus a
click-by-click WhatsApp setup appendix. Good for onboarding someone non-technical.

---

## The 60-second version

**The problem.** A Dubai brokerage pays the portals AED 45–60k/year for leads, then
loses a chunk of them because nobody answers fast enough. One missed deal ≈ **AED 40k**
in commission.

**The product.** An AI that answers in seconds, any hour — captures the lead, scores
it A/B/C, shortlists from the agency's *real* inventory, books the viewing, and hands
anything legal to a human. Then it keeps the lead warm: reminders before a viewing,
nudges when they go quiet, and a ping when a property matching their requirements
appears.

**The state.** Product complete, 285 tests passing, live. **Zero paying customers** —
so the remaining work is a first pilot, not more features.

---

## Reading the codebase

| Where | What |
|---|---|
| `backend/app/chat_core.py` | The channel-agnostic turn — start here |
| `backend/app/prompt_service.py` | How the AI is told who it is (incl. the permit gate) |
| `backend/app/db.py` | **The only** module that touches SQL |
| `backend/app/whatsapp.py` | Webhook, signature, send text/template |
| `backend/app/tools/` | What the AI can actually *do* |
| `backend/app/*_service.py` | The outbound sweeps (reminders, nurture, review, match) |
| `backend/app/*_html.py` | Landing, widget, dashboard, demo, story pages |
| `backend/tests/` | 285 tests; the fake DB seam lives in `conftest.py` |

## Three rules that keep it safe

1. **`db.py` is the only place SQL lives.**
2. **Every outbound send claims a `UNIQUE` row first** — that's what makes overlapping
   sweeps and restarts safe.
3. **Never blind-retry a tool turn** — a booking may already have committed.
