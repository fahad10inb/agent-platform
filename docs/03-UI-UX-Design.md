# UI / UX Design
### ReceptionAI — surfaces, design system, and interaction rules

| | |
|---|---|
| **Version** | 1.0 |
| **Approach** | Server-rendered HTML modules, no build step, no framework |

---

## 1. Surfaces

| Surface | Route | Audience | Job |
|---|---|---|---|
| **Landing** | `/` | Brokerage owner (cold) | Sell the leak → the fix → the price |
| **Story / trailer** | `/watch` | Cold prospect in a DM | 60-second auto-playing proof, phone-first |
| **Live demo** | `/demo` | Prospect on a call | Let them *talk to it* and watch the work |
| **Widget** | `/widget` | The agency's customers | The actual chat |
| **Dashboard** | `/dashboard` | The agency owner | Bookings, leads, conversations, settings |
| **Privacy** | `/privacy` | Anyone | Compliance |

**Rule: no dead ends.** Every page links onward; a nav test enforces this
(`test_site_navigation.py`) — each page serves, every internal link resolves.

---

## 2. Design system

### Palette — "ink & brass"
Deliberately **not** the default AI purple/gradient. It reads premium, Gulf, and
serious about money — because it's sold to property people.

| Token | Value | Use |
|---|---|---|
| `--ink` | `#0d1b26` | Primary dark, headers, buttons |
| `--ink-3` | `#12252f` | Raised dark surfaces |
| `--brass` / `--brass-hi` | `#b8863b` / `#d5a24c` | Accent, CTAs, highlights |
| `--canvas` / `--card` | `#faf9f6` / `#ffffff` | Light grounds |
| `--hairline` | `#e6e1d8` | Borders |
| `--muted` / `--body` | `#7a8892` / `#46565f` | Secondary text |
| `--ok` / `--hot` / `--warn` | `#3fcf7f` / `#ff9a52` / `#d5a24c` | Semantic state |

Semantic colour is kept **separate from the accent** — a green "confirmed" chip never
competes with a brass CTA.

### Type
- **Inter** (web) for UI; **JetBrains Mono / system mono** for data, timestamps, IDs.
- Numeric columns use `font-variant-numeric: tabular-nums` so digits align.
- Headings get `text-wrap: balance`; body copy `text-wrap: pretty`.

### Motion
Restrained. Message bubbles ease in; the ops feed slides in; nothing bounces.
`prefers-reduced-motion` disables all animation globally.

---

## 3. Key screens

### 3.1 Landing (`/`)
**Real-estate only** — the salon/clinic switcher was removed. A multi-vertical page
diluted the pitch, and advertising "Clinic" promised something we can't legally serve.

Narrative order: **the leak** (you paid for the lead, nobody answered) → **the money**
(AED 45–60k portal spend · ~40k commission · 18k/yr for this) → proof → price.
No fake logos, no invented metrics, no testimonials we don't have.

### 3.2 Live demo (`/demo`) — the sales weapon
A **split screen**:
- **Left — the buyer's chat.** The real `/chat` brain.
- **Right — the operations console.** A live feed of what the agent *actually did*
  that turn: lead captured, qualified + graded, calendar checked, viewing booked.

> The widget shows a conversation and *hides the work*. An owner watching it sees "a
> chatbot." This page makes the invisible work visible — that work **is** the product.

**Interaction rules:**
- **▶ Watch it run** — an auto-tour plays an 8-turn enquiry hands-free, so it demos
  itself on a call instead of the seller typing.
- **Synchronised panels** — the work streams on the right *while the typing dots are
  still showing*, then the reply lands. The console is seen to **drive** the answer.
- **EN / العربية toggle** — flips the *entire* customer side, including RTL layout.
- **Mobile** — a **Chat / Activity tab switcher** (a 50/50 split makes both panels
  unusable slivers on a phone). The Activity tab carries a live action count and
  pulses when work arrives while you're on Chat.

### 3.3 Story (`/watch`) — the shareable trailer
Phone-first, **auto-playing**, and **API-free on purpose**: a cold prospect taps a DM
link, and a spinner on a cold-starting server loses them in 3 seconds. Committed dark
"11 PM" scene. Ends by handing off to `/demo`.

### 3.4 Dashboard (`/dashboard`)
- **KPI row** — chats, questions answered, bookings, leads, hours saved.
- **Business Profile card** (real estate) — ORN badge, areas as chips, focus,
  languages, agents. This is *the AI's understanding of the agency, surfaced*.
- **Bookings** — a **day-grouped diary**, not a spreadsheet. Answers "can I see my
  calendar?" and demos far better. Each slot: time · avatar + name · reason · phone ·
  "+ Calendar".
- **Leads / Conversations** — tables. Vertical-centred cells; one flexible column
  truncates with an ellipsis so **every row stays 52px** and columns align; counts are
  right-aligned, shrink-to-fit.
- **Conversations → thread** — read the whole chat; **replying takes the thread over**
  and pauses the AI, with a banner + "Hand back to AI".
- **Settings** — everything the receptionist knows; changes apply to the *next* message.

---

## 4. Bilingual & RTL

- The AI mirrors the customer's language automatically (English ⇄ Arabic, mid-chat).
- In the demo, choosing **العربية** switches chat, chips, greeting, framing, console
  labels and event titles, and sets the customer panel to **RTL**.
- The operator console stays LTR (mixed technical strings/numbers) but its labels
  are translated — a deliberate split.

---

## 5. Accessibility

- Visible `:focus-visible` on every interactive element.
- Chat logs use `role="log"` + `aria-live="polite"`; toasts use `role="status"`.
- Tabs carry `role="tab"` + `aria-selected`.
- All animation respects `prefers-reduced-motion`.
- ⚠️ Icon contrast is state-driven — a white arrow on an inactive tan button reads as
  *broken*, not *waiting*; the send icon changes fill with state.

---

## 6. Responsive

Every surface is `width=device-width` with real breakpoints.

| Surface | Mobile behaviour |
|---|---|
| `/watch` | **Mobile-first** (it's opened in DMs on phones) |
| `/demo` | ≤900px → Chat / Activity **tabs**, each full-screen |
| Landing | Stacks at 860 / 640 / 560px |
| Dashboard | KPIs wrap, tables scroll; usable on phone, best on tablet+ |

---

## 7. Copy principles

- Speak the owner's language: **commission, viewings, leads** — never "LLM", "agent
  framework", "tokens".
- Name the money in dirhams.
- Never claim what we can't do (no RERA endorsement, no "data stays in the UAE").
- Errors say what happened and what to do — no apologies, no vagueness.
