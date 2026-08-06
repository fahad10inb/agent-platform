#!/usr/bin/env python
"""
say_do_gap_eval.py — MEASURE the "say-do gap" and the deterministic net's recovery.

The say-do gap: an LLM agent tells the caller it did something — "I've got your
details, an agent will reach out" — without actually calling the tool. The lead
is silently lost, and nobody knows. This is the exact failure the deterministic
lead-capture safety net (app/lead_safety.py) exists to catch.

This script measures it HONESTLY against the real model + real DB:
  1. Run N real lead conversations through the agent (each ends with a name+number).
  2. On that final turn, check two things independently:
       - did the model actually call a lead-creating tool?   (the tool feed)
       - did its reply CLAIM the lead was handled?            (claim phrases)
     A "say-do gap" = it CLAIMED but did NOT call the tool.
  3. Fire the deterministic net and read the DB: did the lead land anyway?
  4. Print the number: gap rate + net-recovery rate — the figure for the talk.

Offline eval — it does NOT touch the live demo path. It writes throwaway leads to
the skyline-realty demo tenant and deletes them again at the end.

Run from backend/ (venv active, .env with GEMINI_API_KEY + DATABASE_URL):
    python scripts/say_do_gap_eval.py --trials 12
"""

import argparse
import asyncio
import os
import re
import sys
import uuid

# backend/ on sys.path so `import app...` resolves when run as scripts/<file>.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, lead_safety  # noqa: E402
from app.chat_core import run_turn  # noqa: E402

BUSINESS_ID = "skyline-realty"  # the seeded real-estate tenant

# Either of these creates/updates a lead for the caller — so "the tool fired".
_LEAD_TOOLS = {"capture_lead", "qualify_lead"}

# The "say" half: the reply CLAIMS the enquiry was captured / will be followed up.
_CLAIM = re.compile(
    r"(noted|saved|got your details|have your details|passed (it|your|this) on|"
    r"an agent will|our team will|we'?ll (be in touch|reach out|call you|contact you)|"
    r"someone will (call|reach|contact|be in touch)|reached out|forwarded your|"
    r"will (be in touch|reach out|contact you|call you))",
    re.I,
)


async def _run_one(i: int) -> dict:
    """One lead conversation ending in a name + number; returns the verdict."""
    conv = f"saydo-{uuid.uuid4().hex[:10]}"
    name = f"Test Buyer {i}"
    phone = f"0501{i:06d}"  # unique UAE-shaped mobile per trial (e.g. 0501000007)
    deferred: list = []

    def schedule(fn, *args):
        deferred.append((fn, args))

    turns = [
        "Hi, I'm interested in a 2-bedroom in Marina — is anything available?",
        "My budget is around 1.5M, paying cash, hoping to move next month.",
        f"I'm {name}, my number is {phone}. Can an agent reach out to me?",
    ]
    reply, activity = "", []
    for t in turns:
        activity = []  # fresh per turn → holds THIS turn's tool calls
        reply = await run_turn(BUSINESS_ID, conv, t, schedule, activity)

    tool_fired = any(a.get("name") in _LEAD_TOOLS for a in activity)
    claimed = bool(_CLAIM.search(reply or ""))

    # Fire ONLY the deterministic net (skip anything else deferred), synchronously,
    # so we can read the DB the instant it's done.
    for fn, args in deferred:
        if fn is lead_safety.ensure_lead_captured:
            fn(*args)

    lead = db.find_recent_lead(BUSINESS_ID, phone)
    net_caught = bool(lead) and lead.get("notes") == "auto-captured by the lead safety net"
    return {
        "conv": conv,
        "phone": phone,
        "reply": reply,
        "tool_fired": tool_fired,
        "claimed": claimed,
        "say_do_gap": claimed and not tool_fired,
        "lead_in_db": bool(lead),
        "net_caught": net_caught,
    }


def _cleanup(results: list[dict]) -> None:
    """Delete the throwaway leads/messages/qualifications by last-9-digit match
    (the tool stores 05x…, the net stores 9715x… — both share the last 9)."""
    last9 = [re.sub(r"\D", "", r["phone"])[-9:] for r in results]
    convs = [r["conv"] for r in results]
    try:
        with db._connect() as conn:
            conn.execute(
                "DELETE FROM leads WHERE business_id = %s "
                "AND right(regexp_replace(phone, '\\D', '', 'g'), 9) = ANY(%s)",
                (BUSINESS_ID, last9),
            )
            conn.execute(
                "DELETE FROM qualifications WHERE business_id = %s "
                "AND right(regexp_replace(phone, '\\D', '', 'g'), 9) = ANY(%s)",
                (BUSINESS_ID, last9),
            )
            conn.execute(
                "DELETE FROM messages WHERE business_id = %s AND conversation_id = ANY(%s)",
                (BUSINESS_ID, convs),
            )
    except Exception as e:  # noqa: BLE001 — cleanup is best-effort
        print(f"  (cleanup skipped: {str(e)[:120]})")


async def main(trials: int) -> None:
    if not os.getenv("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set — this eval calls the real model.")
    print(f"Running {trials} real lead conversations through '{BUSINESS_ID}'…\n")

    results = []
    for i in range(trials):
        r = await _run_one(i)
        results.append(r)
        verdict = (
            "SAY-DO GAP" if r["say_do_gap"] else ("tool ok" if r["tool_fired"] else "no claim")
        )
        landed = "recovered" if r["net_caught"] else ("tool" if r["lead_in_db"] else "LOST ✗")
        print(
            f"  {i + 1:2d}. tool={'Y' if r['tool_fired'] else 'N'} "
            f"claim={'Y' if r['claimed'] else 'N'}  {verdict:11s}  lead→ {landed}"
        )

    n = len(results)
    gaps = [r for r in results if r["say_do_gap"]]
    recovered = [r for r in gaps if r["net_caught"]]
    landed = [r for r in results if r["lead_in_db"]]
    via_tool = [r for r in results if r["lead_in_db"] and not r["net_caught"]]

    def pct(a, b):
        return f"{a / b * 100:.0f}%" if b else "—"

    print("\n" + "=" * 60)
    print(f"  conversations run ................ {n}")
    print(f"  model called the tool itself ..... {sum(r['tool_fired'] for r in results)}")
    print(f"  SAY-DO GAP (claimed, no tool) .... {len(gaps)}   ({pct(len(gaps), n)} of conversations)")
    print(f"  ↳ recovered by the net ........... {len(recovered)}/{len(gaps)}   ({pct(len(recovered), len(gaps))})")
    print(f"  leads captured (tool OR net) ..... {len(landed)}/{n}   ({pct(len(landed), n)})")
    print(f"    · via the tool ................. {len(via_tool)}")
    print(f"    · via the deterministic net .... {len(recovered)}")
    print(f"  leads LOST ....................... {n - len(landed)}")
    print("=" * 60)

    if gaps:
        print("\n  Evidence — the model's own words the moment it skipped the tool:")
        for r in gaps[:2]:
            print(f'   • "{r["reply"][:170].strip()}…"')

    print(
        f"\n  >>> Headline: the agent claimed it captured the lead but skipped the tool"
        f"\n      on {len(gaps)}/{n} conversations ({pct(len(gaps), n)}). "
        f"The deterministic net recovered {pct(len(recovered), len(gaps))} of them."
        f"\n      Net result: {len(landed)}/{n} leads captured — {n - len(landed)} lost."
    )

    _cleanup(results)
    print("\n  (throwaway test leads cleaned up)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Measure the say-do gap + net recovery.")
    ap.add_argument("--trials", type=int, default=12, help="how many lead conversations to run")
    args = ap.parse_args()
    asyncio.run(main(args.trials))
