# ReceptionAI — Design System & UX Rationale

Scope: the three server-rendered surfaces (`backend/app/landing_html.py`,
`dashboard_html.py`, `widget_html.py`). Audience: business owners, not
developers. First-10-seconds goal: *"software I'd trust with my business"*,
not *"another AI chatbot"*. Quality bar: Stripe / Linear / Vercel / Clerk.

---

## 1. UX audit (before this pass)

### Already at the bar
- **Live demo in the hero.** Show-don't-tell is the single strongest trust
  device an unknown product has (evidence > claims; "demo as social proof").
- **Honest content discipline.** No fake logos/metrics anywhere — rare, and it
  compounds: one detected lie poisons every other claim (halo/horns effect).
- **One accent, light canvas, Inter, hairline cards.** Restrained palette reads
  "financial software", not "AI toy".
- **Widget fundamentals:** XSS-safe `textContent` rendering, conversation
  restore, typing indicator, reduced-motion support, `aria-live` log.
- **Dashboard fundamentals:** session restore, readable 422 errors, empty
  states with next actions, sticky table headers, value KPIs (hours saved).

### Below the bar (and why it mattered)
| Issue | Principle violated | Fix shipped |
|---|---|---|
| Hero listed *what it is*, demo showed one industry only | Self-relevance: owners bounce if they can't see *their* business ("this is for salons, not my clinic") | Industry selector (Salon/Clinic/Real estate) swapping the live demo + benefit line |
| "Remembers every caller" was *claimed*, never *demonstrated* | Concreteness beats abstraction; contrast frames value (loss aversion) | Before/after chat vignettes: generic bot vs "Welcome back, Layla — your usual with Rana?" |
| Booking was a bullet, not a story | Owners buy outcomes, not features | Chat→dashboard "booking beat": conversation on the left, the confirmed row landing in the dashboard on the right |
| No pricing section at all | Missing pricing reads as "enterprise call-us" or "not a real product"; kills scent of information | Honest founding-customer pricing (structure without invented numbers) |
| No social proof surface | Testimonials are the #2 conversion lever; absence is a visible hole | Founder's-promise card — explicitly honest placeholder that converts on candor |
| Security copy was developer-speak (`X-API-Key · one per business`) | Speak the user's language (Nielsen #2) | Trust trio in benefit language: "Your data is yours alone", "Identity before information", "Double-booking is impossible" |
| Login didn't submit on Enter; tabs/list items were `div`s | Keyboard parity, WCAG 2.1.1 | Real `<form>`, tabs and business list as `<button role="tab">` with `aria-selected` |
| "Loading…" text flash in tabs | Perceived performance: skeletons read ~30% faster than spinners/text | Shimmer skeleton rows (+ SR-only "Loading…") |
| Onboarding = 14 unstructured fields | Chunking (Miller); long flat forms feel like tax returns | 5 numbered groups, each with a one-line "why this matters" |
| Dashboard said "clinic/patient" everywhere | The platform is multi-vertical; wrong words = wrong product | "Business / customer" language throughout (admin still means the same) |
| `--muted:#8a8798` on white ≈ 3.5:1 for 13px text | WCAG AA 1.4.3 (needs 4.5:1) | `--muted:#716e80` (≈ 5.2:1) across all three surfaces |

---

## 2. Information architecture

**Landing = one argument, in order** (each section earns the next scroll):
1. **Hero** — differentiator headline (*remembers* — also test-asserted) + live
   demo with industry selector. Primary CTA: "See it answer your customers."
2. **Ribbon** — four scannable guarantees (24/7, EN+AR, no double-booking, memory).
3. **Problem** — "A missed message is a lost booking" (loss framing).
4. **Memory proof** — before/after vignettes (the differentiator, demonstrated).
5. **Booking proof** — chat → confirmed dashboard row + DB-lock note.
6. **How it works** — 3 steps, "live in an afternoon" (effort objection).
7. **Product bento** — 8 benefit-first capability cards.
8. **Trust trio** — isolation, identity verification, double-booking constraint.
9. **Founder's promise** — honest stand-in for testimonials.
10. **Pricing** — founding-customer framing, Starter/Growth.
11. **FAQ** — 7 objection-handling answers. 12. **Final CTA** — urgency without fake scarcity.

**Dashboard:** login → (owner: straight into their business | admin: sidebar of
businesses + add-new) → KPI value band → Bookings / Leads / Settings / Widget
tabs. The KPI band leads because retention = the owner seeing value weekly.

**Widget:** header (identity + online status) → log → composer → powered-by
backlink. No change to flow — it was right.

## 3. Design tokens (shared by all three files)

```css
--canvas:#fdfdff  --surface:#f7f6fb  --surface-2:#f1effa  --card:#ffffff
--hairline:#e9e7f2  --hairline-2:#dcd8ea            /* borders: decorative / interactive */
--ink:#16141d  --body:#4c4a58  --muted:#716e80      /* 3-step text ramp, all AA on card */
--accent:#7c5cff  --accent-deep:#6847e6 (AA for text)  --accent-soft:#efeaff
--ok:#147a3d / --ok-soft:#e8f7ee   --danger:#c02543
--focus:rgba(124,92,255,.35)       /* every interactive element gets :focus-visible */
--shadow-card / --shadow-float     /* two elevations only */
```

**Type:** Inter (`cv11`,`ss01`), 16px base / 1.55. Scale: 11.5 (labels-caps) ·
13 (micro) · 14.5 (UI) · 16 (body) · 19–20 (h3) · clamp(28–42) h2 ·
clamp(38–64) h1. Negative tracking above 19px. `tabular-nums` for every number
(KPIs, times, phones). **Rules:** one accent; gradients only as the blurred
hero glow and chat-bubble fill; radius 8 (inputs) / 12 (cards) / 16 (frames) /
999 (pills); borders are hairline + shadow, never heavy.

## 4. Component standards

- **Buttons:** pill, 600 weight; primary = accent w/ inset highlight, hover
  `-1px` lift; secondary = white + `--hairline-2`. Never two primaries in view.
- **Cards:** `--card` bg + hairline + `--shadow-card`; float shadow reserved
  for hero demo, login, featured tier.
- **Segmented tabs** (landing industry selector, dashboard tabs): pill track on
  `--surface`, active = white pill + card shadow + 600; `role="tab"` +
  `aria-selected`, real `<button>`s.
- **Tables:** sticky uppercase 12.5px header, 52px rows, hover wash, initials
  avatar (deterministic hue from name), status chips (dot + tint: violet=new,
  green=confirmed).
- **Chat vignettes:** `.convo` card with labeled header — `plain` (grey, the
  "before") vs `ours` (violet, the "after"); bubbles 13.5px, max 82%.
- **Forms:** grouped `fieldset`-style blocks with numbered header + one-line
  "why"; labels 13px/500 in `--body`, hints in `.soft`; every label `for=`-bound.
- **KPI band:** one card, six hairline-divided cells (6 → 3 → 2 columns).

## 5. Microcopy guide — benefit-first rewrites

Formula: *capability → what the owner gets, in their own words.* Feature nouns
lose to receptionist verbs.

| Was (feature-speak) | Now (benefit-speak) |
|---|---|
| Long-term memory | Greets returning customers like a real receptionist |
| Real bookings | Real appointments, not callback requests |
| DB uniqueness constraint | Double-booking is impossible — it's a constraint, not a promise |
| Per-business isolation / `X-API-Key` | Your data is yours alone — never shared, never mixed |
| Identity verification (anti-IDOR) | Identity before information — nobody can fish for your customers' visits |
| Staff field | Recommends the right person — "someone good with balayage" gets Rana |
| Policies field | Applies your house rules, so your staff never has to be the bad guy |
| Bilingual (EN/AR) | Speaks your customers' language — and switches the moment they switch |
| Usage metering | Shows you what it's worth — bookings, leads, staff hours saved |
| "Wrong Business ID or key." | "That Business ID and key don't match. Check both and try again." |
| "Saved ✓" | "Settings saved — live from the next conversation" |
| Onboard new clinic | Set up a new business — "this one form is the whole onboarding" |

Voice: plain, warm, confident; contractions yes, hype no ("revolutionary",
"supercharge" banned); honesty is a feature ("we're new, and we won't pretend
otherwise"); numbers only when real.

## 6. Empty / loading / error states

- **Empty = onboarding:** icon chip + title + *what fills this and how*
  ("Share your chat link — every appointment lands here, in real time").
- **Loading:** skeleton rows (shimmer, `aria-hidden`) + visually-hidden
  "Loading…" `role="status"`. KPIs show "–" until data lands (never fake zeros
  — a real 0 must be meaningful).
- **Errors:** say what happened + what to do; toasts for transient
  ("Couldn't save — please try again"), inline `aria-live` for login; raw API
  details only via `apiErr()` formatting, never `[object Object]`.

## 7. Motion

- Durations 150–200ms UI, 600ms scroll-reveal; ease `cubic-bezier(.16,1,.3,1)`.
- Only cheap properties (opacity/transform). One IntersectionObserver,
  unobserve after entry.
- Everything gated by `prefers-reduced-motion` (reveals render visible,
  shimmer/typing dots stop). `<noscript>` forces reveals visible.
- No parallax, no marquees, no animated gradients.

## 8. Mobile & accessibility

- Breakpoints 960/640 (landing), 1100/860/640 (dashboard); single-column
  stacks, demo iframe 440px, safe-area padding in widget composer.
- Keyboard: login submits on Enter; tabs/list items are buttons; visible
  `:focus-visible` ring everywhere; FAQ = native `<details>`.
- ARIA: `role="tablist/tab"` + `aria-selected`, `aria-live` chat log and
  toast/status, labeled iframes, decorative vignettes `aria-hidden`, `dir="rtl"
  lang="ar"` on Arabic samples.
- Contrast: text ramp ≥ 4.5:1; chips/labels checked; selection tint on brand.

## 9. Conversion levers (ranked)

1. **Interactive demo in hero + industry selector** — self-qualification and
   proof in one; the visitor sells themselves. (shipped)
2. **Differentiator demonstrated, not claimed** — memory before/after. (shipped)
3. **Outcome proof** — chat→dashboard booking beat; hours-saved KPI. (shipped)
4. **Risk reversal** — trust trio, founder promise, "no long-term contracts",
   pricing honesty. (shipped)
5. **Real social proof** — named testimonials with faces. (needs humans)
6. **Friction cuts** — self-serve signup instead of manual onboarding; a real
   "talk to us" channel (email/WhatsApp/Calendly). (needs humans/product)
7. **Retention loop** — weekly "your receptionist booked X, saved Y hours"
   email. (needs product)

## 10. SaaS best-practices checklist

| Practice | Status |
|---|---|
| Benefit-first hero w/ single primary CTA | ✅ |
| Live product proof above the fold | ✅ |
| Industry/persona self-selection | ✅ |
| Transparent pricing page | ✅ structure; ❌ real numbers |
| Social proof | ⚠️ honest placeholder (founder promise) |
| Security/trust section | ✅ (grounded in real architecture) |
| Objection-handling FAQ | ✅ |
| Empty/loading/error states designed | ✅ |
| Keyboard + SR basics | ✅ |
| Reduced motion | ✅ |
| Mobile-first responsive | ✅ |
| Self-serve signup / billing / custom domain / analytics / favicon+OG image | ❌ needs humans (below) |

## 11. Implemented vs. needs-the-human

**Implemented in this pass:** everything in sections 2–9 marked shipped —
landing rebuilt around the conversion story (industry selector, memory duo,
booking beat, trust trio, founder promise, founding pricing, expanded FAQ,
skyline-realty demo link); dashboard elevated (KPI band, button tabs +
aria, Enter-to-sign-in, label bindings, skeletons, grouped stepped onboarding
with per-group "why", grouped settings, copy-key button, business-not-clinic
microcopy, kinder errors); widget consistency polish (tokens, footer backlink,
"Online — replies in seconds"). All JS/API contracts, element IDs, and the
hero "remembers" assertion preserved; 41/41 tests green.

**Needs the human (top items):**
1. **Real pricing numbers + a contact channel** (email, WhatsApp, or Calendly
   link) — the pricing section and founder card currently route to the demo.
2. **Real testimonials** (name, business, photo) to replace the founder-promise
   card — 2–3 founding customers is enough.
3. **Brand collateral:** favicon, OG/social-share image, logo mark, custom
   domain (bare Render URL undermines the trust story).
4. **Analytics + event tracking** (demo opened, industry switched, pricing
   viewed, dashboard sign-in) — conversion levers can't be tuned blind.
5. **Self-serve signup** ("Create your receptionist" flow with billing) — the
   biggest structural friction cut; today onboarding is admin-mediated.
