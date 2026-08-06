"""
say_do_verifier.py — a general "say-do gap" detector (observability, log-only).

Generalizes the lead-capture safety net from ONE action to EVERY action. After a
turn, it reconciles what the reply CLAIMED the agent did — "you're booked", "I've
noted your details", "connecting you to an agent" — against which tools ACTUALLY
fired that turn. A claim with no backing tool call is a say-do gap: the model told
the caller something happened when nothing did.

This only LOGS — it never changes the reply. The deterministic safety nets
(lead_safety, llm_service's empty-reply recovery) do the recovering; this is the
always-on signal for WHEN, and on WHICH action, the gap opened. It's wired into
run_turn wrapped in try/except so a bug in here can never break a turn.

Design bias: a false "gap" is worse than a miss — the whole value is trustworthy
signal — so the claim patterns are kept TIGHT and every backing set is GENEROUS
(any related tool satisfies the claim).
"""

import re

# Each claim class: (action label, phrase pattern, the tool names that back it).
# A claim is a gap only when NONE of its backing tools fired this turn.
_CLAIMS: tuple[tuple[str, "re.Pattern[str]", frozenset[str]], ...] = (
    (
        "appointment booked",
        re.compile(
            r"\b(booked|reserved|scheduled you|you'?re (all )?(booked|set)|"
            r"your (appointment|viewing|booking|slot) is (booked|set|confirmed)|"
            r"see you (on|at|then))\b",
            re.I,
        ),
        frozenset(
            {"book_appointment", "reschedule_appointment", "confirm_appointment"}
        ),
    ),
    (
        "appointment rescheduled",
        re.compile(
            r"\b(rescheduled|moved your (appointment|viewing|booking)|"
            r"changed (it|your (appointment|viewing|booking)) to)\b",
            re.I,
        ),
        frozenset({"reschedule_appointment", "book_appointment"}),
    ),
    (
        "appointment cancelled",
        re.compile(
            r"\b(cancell?ed your (appointment|viewing|booking)|"
            r"your (appointment|viewing|booking) (is|has been) cancell?ed)\b",
            re.I,
        ),
        frozenset({"cancel_appointment", "reschedule_appointment"}),
    ),
    (
        "lead / follow-up",
        re.compile(
            r"\b(noted your details|saved your details|got your details|"
            r"have your details|passed (it|your (details|enquiry|number)|this) on|"
            r"an agent will (be in touch|reach out|call|contact)|"
            r"(our team|someone) will (be in touch|reach out|call|contact)|"
            r"we'?ll (be in touch|reach out|call you|contact you))\b",
            re.I,
        ),
        frozenset({"capture_lead", "qualify_lead"}),
    ),
    (
        "human handoff",
        re.compile(
            r"\b(connecting you (to|with) (a|an|our) "
            r"(human|agent|colleague|team member|person)|"
            r"a (human|colleague|team member|person) will "
            r"(call|contact|be in touch|take over)|"
            r"passing you (to|over to) (a|an|our))\b",
            re.I,
        ),
        frozenset({"request_human"}),
    ),
)


def detect(reply: str, activity: list | None) -> list[dict]:
    """Return the say-do gaps this turn: each claim the reply made whose backing
    tool never fired. Pure and read-only — safe to call anywhere, on anything.

    `activity` is the turn's executed-tool transcript (llm_service's activity
    sink): a list of {"name": <tool>, ...} dicts. Returns [] when everything the
    reply claimed is backed by a real tool call (the healthy case).
    """
    text = reply or ""
    fired = {(a or {}).get("name") for a in (activity or [])}
    gaps: list[dict] = []
    for action, pattern, backing in _CLAIMS:
        m = pattern.search(text)
        if m and fired.isdisjoint(backing):
            gaps.append(
                {
                    "action": action,
                    "claim": m.group(0),
                    "expected_tool": " / ".join(sorted(backing)),
                }
            )
    return gaps
