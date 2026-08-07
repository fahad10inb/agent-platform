# WhatsApp message templates — submit these to Meta

**Why this exists.** A WhatsApp reply *inside* the 24-hour window after a customer
messages you can be free-form text. A message the business *starts* outside that
window (a reminder, a nurture follow-up, a review request, a portal-lead outreach,
a listing match) can **only** be delivered as a **pre-approved template** — Meta
rejects free-form business-initiated sends with error `131047`.

The code is fully wired for this. Each of the five business-initiated message
kinds passes structured variables to the exact template shape below. **Until a
template name is set for a kind, that kind sends free-form text** (correct within
24h / on the Meta test number) — so nothing breaks; sends just won't deliver
*outside* the window until the template is approved and its name is configured.

> **Important:** submit each body **exactly** as written. The `{{1}}`, `{{2}}`, …
> positions are the contract the code fills, in order. If you change the wording
> that's fine, but **do not add, remove, or reorder the variables** — the code
> sends a fixed number of them per kind (see the count on each). A mismatch is
> caught in code and safely falls back to free-form text (it won't send a broken
> template), but then the out-of-window delivery won't happen.

---

## How to submit (Meta Business Manager, ~5 min each)

1. **WhatsApp Manager** → **Account tools → Message templates** → **Create template**.
2. **Category:** use the one noted per template below (`Utility` or `Marketing`).
   - `reminder`, `review`, `outreach`, `match` → **Utility** (transactional, cheaper, faster approval).
   - `nurture` → **Marketing** (it's a re-engagement nudge; Utility will get rejected).
3. **Name:** must be lowercase + underscores. Suggested names are below — whatever
   you pick, put the **same** name in the matching config field (step 5).
4. **Language:** English (US) `en_US` unless you set `whatsapp_template_lang` to
   something else. Add an Arabic version later as a separate language on the same
   template name.
5. **Body:** paste the body exactly. Meta shows `{{1}}`, `{{2}}`… as variables and
   asks for a **sample value** for each — use the samples listed.
6. Submit. Approval is usually minutes to a few hours.
7. When approved, set the template **name** in the business's config field
   (env var on Render, or wherever config is loaded):

   | kind | config field | suggested name |
   |------|--------------|----------------|
   | reminder | `whatsapp_template_reminder` | `booking_reminder` |
   | nurture  | `whatsapp_template_nurture`  | `enquiry_followup` |
   | review   | `whatsapp_template_review`   | `review_request` |
   | outreach | `whatsapp_template_outreach` | `lead_outreach` |
   | match    | `whatsapp_template_match`    | `listing_match` |

   Language code lives in `whatsapp_template_lang` (default `en_US`).

That's it — the moment the name is set, that kind switches from free-form text to
the approved template for out-of-window sends. No code change needed.

---

## The five templates

### 1. reminder — **Utility** — 5 variables
Config: `whatsapp_template_reminder`

**Body (paste exactly):**
```
Hi {{1}}, a reminder about {{2}} at {{3}} — {{4}} at {{5}}. Reply CONFIRM to keep it, or reply here if you'd like a different time.
```
| var | meaning | sample |
|-----|---------|--------|
| {{1}} | customer first name | Sam |
| {{2}} | what ("your viewing" / "your appointment") | your viewing |
| {{3}} | business name | Skyline Realty |
| {{4}} | when ("today" / "tomorrow" / weekday) | tomorrow |
| {{5}} | time | 4:00 PM |

### 2. nurture — **Marketing** — 3 variables
Config: `whatsapp_template_nurture`

**Body (paste exactly):**
```
Hi {{1}}, it's {{2}} following up on your enquiry. {{3}} Reply here whenever suits you — no rush.
```
| var | meaning | sample |
|-----|---------|--------|
| {{1}} | lead first name | Sam |
| {{2}} | business name | Skyline Realty |
| {{3}} | the stage line (changes per touch) | Still looking? I can line up a couple of options or a viewing whenever suits you. |

### 3. review — **Utility** — 3 variables
Config: `whatsapp_template_review`

**Body (paste exactly):**
```
Hi {{1}}, thanks for choosing {{2}}! If you have a moment, we'd really appreciate a quick Google review: {{3}} — it genuinely helps others find us. Thank you!
```
| var | meaning | sample |
|-----|---------|--------|
| {{1}} | customer first name | Sam |
| {{2}} | business name | Skyline Realty |
| {{3}} | Google review URL | https://g.page/r/abc/review |

### 4. outreach — **Utility** — 2 variables
Config: `whatsapp_template_outreach`

**Body (paste exactly):**
```
Hi {{1}}, thanks for your enquiry — this is the assistant at {{2}}. I can get you property details and set up a viewing fast. What's your budget range and which area are you focused on?
```
| var | meaning | sample |
|-----|---------|--------|
| {{1}} | lead first name | Sam |
| {{2}} | business name | Skyline Realty |

### 5. match — **Utility** — 4 variables
Config: `whatsapp_template_match`

**Body (paste exactly):**
```
Hi {{1}}, a new {{2}} matching what you were after just came up at {{3}} — {{4}}. Want me to arrange a viewing?
```
| var | meaning | sample |
|-----|---------|--------|
| {{1}} | lead first name | Sam |
| {{2}} | what ("2BR in Marina" / "property") | 2BR in Marina |
| {{3}} | business name | Skyline Realty |
| {{4}} | listing (title + price) | 2BR Marina View, 1.6M |

---

## Notes

- **Arabic:** add each template's Arabic translation as a second **language** under
  the *same template name*, then set `whatsapp_template_lang` to `ar` (or per-send
  language selection later). The variable positions must match the English version.
- **Test number caveat:** the free Meta test number only delivers to 5 verified
  recipients and its templates are for testing — a real pilot needs a real number
  on a Meta-verified WABA (use the client's trade license).
- **Where the shapes are defined in code:** `backend/app/whatsapp.py` →
  `_TEMPLATE_SPECS` (the single source of truth for body + variable count). Each
  sender's `*_params()` builder (in `reminder_service`, `nurture_service`,
  `review_service`, `lead_intake`, `matcher_service`) fills them in order. A test
  (`test_every_template_spec_body_matches_its_declared_var_count` +
  `test_sender_param_builders_match_their_spec_var_counts`) keeps code and this doc
  in lockstep.
