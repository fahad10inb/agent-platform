# Reliability: the say-do gap and the deterministic safety net

**Status:** implemented and in production
**Owner:** Fahad
**Scope:** how ReceptionAI guarantees a caller who leaves a phone number is never
silently lost, even when the language model claims it captured them but didn't.

---

## 1. Summary

An LLM agent will sometimes tell a caller *"I've saved your details, an agent will
call you"* — and never actually call the tool that saves them. The reply reads
perfectly; the lead is gone; nobody notices. We call this the **say-do gap**: the
model *says* it did something it did not *do*.

ReceptionAI treats this as a first-class reliability problem, not an edge case. The
approach is three parts:

1. **A deterministic safety net** (`lead_safety.ensure_lead_captured`) that captures
   the lead itself whenever the model skipped the tool. This is the guarantee.
2. **A general say-do verifier** (`say_do_verifier`) that reconciles what every
   reply *claimed* against what the tools *actually did*, and logs any gap. This is
   the always-on signal.
3. **An offline measurement harness** (`scripts/say_do_gap_eval.py`) that quantifies
   the gap and the net's recovery against the real model and the real database.
   This is the evidence.

Guiding principle: **a prompt is a request; code is a guarantee.** We still ask the
model to call the tool, but we never depend on it for anything that must not fail.

---

## 2. The problem

### 2.1 Definition

A **say-do gap** occurs on a turn where:

- the reply **claims** an action was completed (lead saved, viewing booked, handed
  to a human), **and**
- **no tool call** that performs that action fired on that turn.

For lead capture specifically: the reply claims the enquiry was captured, but
neither `capture_lead` nor `qualify_lead` executed.

### 2.2 Why it matters

For a real-estate agency, a captured lead is the product. Lead-generation spend runs
into the tens of thousands of dirhams per qualified buyer. A silently dropped lead is
indistinguishable, from the outside, from a smooth successful conversation — which is
exactly why it is dangerous. A crash is visible. A confident, wrong reply is not.

---

## 3. The request pipeline

A conversation turn flows through one path regardless of channel (web widget or
WhatsApp):

```
inbound message
  -> chat_core.run_turn(business_id, conversation_id, message, schedule, activity?)
       - load business, enforce quota, acquire per-conversation lock
       - build system prompt (prompt_service.build_system_prompt)
       - assemble tools (calendar + memory + leads + handoff [+ qualify])
       - llm_service.generate_reply(system_prompt, history, tools, activity_sink)
            -> Gemini 2.5-flash, automatic function calling
       - empty-reply guard
       - say_do_verifier.detect(reply, activity)         # observability, log-only
       - persist both turns, meter usage
       - schedule(lead_safety.ensure_lead_captured, ...)  # deterministic net, background
       - schedule distiller every N user messages
  -> reply text returned to the channel
```

Tools available to the model (each scoped to the business via its closure):

- **calendar:** `check_availability`, `book_appointment`, `reschedule_appointment`,
  `cancel_appointment`, `confirm_appointment`, `find_my_appointments`
- **leads:** `capture_lead`
- **qualify (real-estate):** `qualify_lead`, `stop_contact`
- **handoff:** `request_human`
- **memory:** `recall_caller`, `remember_about_caller`

---

## 4. How the gap arises

There are two independent causes. Both end in the same state: a claim with no tool
call.

### 4.1 The empty-reply recovery path (dominant)

This is the largest contributor to the measured gap, and it is an **interaction
between two deliberate guardrails**, not a single bug.

1. On the heaviest turn — the caller gives name **and** number, and the model is
   trying to call `capture_lead` and possibly `book_appointment` together — Gemini
   sometimes returns an **empty reply** (no text), or a **leaked** reply where it
   *types* the tool call as text instead of executing it. Part of the cause is that
   `gemini-2.5-flash` spends part of its output-token budget on hidden "thinking";
   too small a budget starves or blanks the reply (see §8).

2. `llm_service.generate_reply` detects this and calls `_recover_empty_reply`: it
   makes **one follow-up call with tools disabled** (`tools=None`). Tools are
   disabled on purpose — so a retry cannot execute a tool a second time and, for
   example, double-book the same slot or double-save the lead.

3. In that follow-up call the model writes a clean, confident reply — *"Got it,
   I've saved your details"* — but it **cannot** call the tool, because tools are
   off. The claim is produced in the exact moment the model is incapable of acting.

**Net effect:** the "never send a blank message" safety and the "never execute a
tool twice" safety, combined, can emit a confident-but-empty promise. This is an
*emergent* behaviour — invisible by reading either guardrail alone, visible only by
measuring the end-to-end outcome.

Relevant code: `llm_service.generate_reply`, `llm_service._recover_empty_reply`,
`llm_service._looks_like_leaked_tool_call`.

### 4.2 Stochastic tool omission

Independently of the blank path, the model sometimes simply narrates *"noted, an
agent will follow up"* on the first pass and does not emit the tool call at all.
This is ordinary LLM non-determinism. No prompt eliminates it entirely; our measured
gap was produced **with** a prompt that instructs the model to always call the tool.

---

## 5. The deterministic safety net

`app/lead_safety.py :: ensure_lead_captured(business, conversation_id) -> bool`

Runs in the **background after every turn** (scheduled by `run_turn`, off the
caller's reply path). It does not care *why* the tool did not fire; it only checks
the outcome and repairs it.

Algorithm:

1. **Applies only where a lead is the goal** — `vertical in ("real_estate",
   "general")`. Clinics/salons book instead (a booking already records the caller).
2. **Read the conversation**, join the caller's messages, and extract the first
   UAE mobile with `_find_phone` (normalised to E.164, `9715XXXXXXXX`). No phone ->
   nothing to capture -> return.
3. **Idempotency check** — if `db.find_recent_lead` already has this number, or
   `db.phone_has_booking` shows they booked, **do nothing**. The tool stays the
   primary path; the net never duplicates a lead.
4. **Capture** — `db.save_lead(bid, name, phone, interest, notes)` where:
   - `name` comes from `_guess_name` (see §5.1), else `"New enquiry (auto)"`.
   - `notes = "auto-captured by the lead safety net"` — the marker that lets both
     the owner and the eval distinguish a net-caught lead from a tool-caught one.
5. **Best-effort** — the whole function is wrapped; it never raises into the
   caller's request. A safety net that can break the turn is not a safety net.

### 5.1 Name extraction (`_guess_name`)

The net extracts a display name from phrases like *"I'm X"* / *"my name is X"*. Two
properties matter:

- It **scans all** such phrases and takes the first whose leading word is not a
  lead-intent stopword (`interested`, `looking`, `keen`, ...). A real thread says
  *"I'm interested in a 2-bed"* **before** *"I'm Omar Haddad"*; naively taking the
  first match stored the intent phrase as the name.
- The captured name is matched **case-sensitively** for any second word, and only
  the lead-in phrase is case-insensitive. Without this, a case-insensitive `[A-Z]`
  swept a trailing lowercase word into the name (turning *"I'm interested in..."*
  into the name *"Interested In"*).

Result: net-caught leads carry the caller's real name (e.g. `Omar Haddad`), not a
generic or malformed placeholder.

---

## 6. The general say-do verifier

`app/say_do_verifier.py :: detect(reply, activity) -> list[gap]`

Generalises the lead net's idea from one action to **every** action. After each
turn, it reconciles what the reply **claimed** against which tools **fired**, across
five claim classes:

| Claim class            | Backed by (any of)                                                |
|------------------------|-------------------------------------------------------------------|
| appointment booked     | `book_appointment`, `reschedule_appointment`, `confirm_appointment` |
| appointment rescheduled| `reschedule_appointment`, `book_appointment`                      |
| appointment cancelled  | `cancel_appointment`, `reschedule_appointment`                    |
| lead / follow-up       | `capture_lead`, `qualify_lead`                                    |
| human handoff          | `request_human`                                                  |

A claim with **no** backing tool call is logged as `SAY-DO GAP` with the business,
conversation, matched phrase, and expected tool.

Properties:

- **Observability only.** It never changes the reply. The deterministic nets do the
  recovering; this is the signal for *when* and *on which action* a gap opened.
- **Wrapped** in the call site so a bug in the verifier can never break a turn.
- **Tight claim patterns, generous backing sets** — a false "gap" is worse than a
  miss, because the value is trustworthy signal.

Wired into `run_turn` via a feature-detected activity sink, so the tool transcript
is captured on every turn while a plain 3-arg `generate_reply` test double keeps
working unchanged.

---

## 7. Measurement

`scripts/say_do_gap_eval.py` — an offline eval against the **real model and real
database**. It is the source of the headline number.

### 7.1 Method

For each of N trials (default 12):

1. Run a real 3-turn conversation through `chat_core.run_turn` against the seeded
   `skyline-realty` tenant. The final turn gives a name and a UAE mobile.
2. Record, independently:
   - `tool_fired` — did any of `{capture_lead, qualify_lead}` appear in the turn's
     tool transcript?
   - `claimed` — did the reply claim capture? (regex by default; a second model via
     `--judge`, see §7.3)
   - `say_do_gap = claimed and not tool_fired`.
3. Fire **only** `lead_safety.ensure_lead_captured` synchronously, then read the DB
   with `db.find_recent_lead`. `net_caught` is true when a lead exists whose notes
   equal the net's marker.
4. Report gap rate, net-recovery rate, and leads lost; write an HTML report to
   `backend/reports/say_do_gap_report.html`.

### 7.2 Flags

- `--trials N` — number of conversations (default 12).
- `--keep` — leave the test leads in the DB (for a live proof query); default
  cleans them up.
- `--judge` — cross-validate the "claim" with a second model (LLM-as-judge, one
  model acts, another verifies), robust to paraphrase the regex never saw. Prints
  the regex/judge agreement rate. The judge call runs with thinking disabled.

Run:

```
cd backend
python scripts/say_do_gap_eval.py --trials 15 --keep --judge
```

### 7.3 Cross-validation (`--judge`)

The "did the reply claim success" decision is, by default, a regex. `--judge` adds a
second model that reads each reply in isolation and rules YES/NO, then reports how
often it agreed with the regex — so the gap number does not hinge on one brittle
pattern.

---

## 8. Results and honest interpretation

A representative run (15 conversations):

- **~60%** of conversations: the model claimed capture and did **not** call the tool.
- **100%** of those: recovered by the deterministic net.
- **0** leads lost.

**Interpretation — read this before quoting the number:**

- The 60% is **this eval's** rate, not a universal production rate. It is inflated
  because the scripted final turn reliably triggers the empty-reply recovery path
  (§4.1). Real, varied production traffic is very likely lower.
- The **mechanism** is real and it is invisible when it happens. The value of the
  system is not the size of the gap; it is that **any** gap, at any rate, is caught
  and verifiable.
- Correct framing: *"the raw model skips the tool on a large fraction of turns; my
  system loses zero leads because a deterministic net catches every one, and I can
  prove it in the database."* Defend the mechanism, not the percentage — the story
  is identical at 40% or 70%.

---

## 9. Configuration

| Setting (`app/config.py`)      | Value                 | Why                                                                 |
|--------------------------------|-----------------------|---------------------------------------------------------------------|
| `gemini_model`                 | `gemini-2.5-flash`    | chat model                                                          |
| `gemini_max_output_tokens`     | `2048`                | raised from 1024: 2.5-flash spends budget on hidden thinking, so token-heavy replies (Arabic especially) were truncated mid-sentence |
| `llm_timeout_seconds`          | `45.0`                | hard ceiling per model call incl. tool round-trips                  |

Language note: for Arabic conversations the prompt requires a fully-Arabic reply —
every word in Arabic script including transliterated area/building names, all listing
features translated, no Latin letters — enforced in `prompt_service.build_system_prompt`.

---

## 10. Design principles

1. **Deterministic guard over stochastic prompt.** Ask the model to do the right
   thing; guarantee the outcome in code. A prompt is a request; code is a guarantee.
2. **Idempotency.** The net no-ops when the tool already captured the lead or the
   caller booked. The primary path stays primary; the net never duplicates.
3. **Verify the outcome, not the model's word.** Correctness is confirmed by reading
   the database, not by trusting the reply text.
4. **Measure emergent behaviour.** The dominant failure is an interaction between two
   correct guardrails. You cannot reason your way to it from either one; you find it
   by measuring the end-to-end result and then engineer around it.
5. **Safety nets must never break the turn.** Every backstop is best-effort and
   wrapped; a failure in the net degrades to the normal path, never to a 500.

---

## 11. File map

| File                                   | Responsibility                                             |
|----------------------------------------|------------------------------------------------------------|
| `app/chat_core.py`                     | one turn: prompt, tools, model call, persist, schedule net |
| `app/llm_service.py`                   | Gemini call + empty/leaked-reply recovery (tools off)      |
| `app/lead_safety.py`                   | deterministic lead-capture net (`ensure_lead_captured`)    |
| `app/say_do_verifier.py`               | general claim-vs-tool reconciler (observability, log-only) |
| `app/prompt_service.py`                | system prompt incl. language rules                         |
| `scripts/say_do_gap_eval.py`           | offline measurement + HTML report                          |
| `tests/test_lead_safety.py`            | net behaviour incl. name extraction                        |
| `tests/test_say_do_verifier.py`        | verifier reconciliation                                    |

---

## 12. Reproducing the result

```
cd backend
# clear any prior test rows in the demo tenant (Supabase SQL editor):
#   delete from leads
#   where notes = 'auto-captured by the lead safety net' and phone like '971501%';

python scripts/say_do_gap_eval.py --trials 15 --keep --judge
# -> console summary + backend/reports/say_do_gap_report.html
# -> verify the caught leads:
#   select name, phone, notes, created_at from leads
#   where notes = 'auto-captured by the lead safety net' order by created_at desc;
```
