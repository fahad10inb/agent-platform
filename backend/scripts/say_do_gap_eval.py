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
    python scripts/say_do_gap_eval.py --trials 15 --keep   # leave leads for a live demo query
    python scripts/say_do_gap_eval.py --trials 12 --judge  # cross-validate the claim with a 2nd model
"""

import argparse
import asyncio
import datetime
import html
import os
import re
import sys
import uuid

from google.genai import types

# backend/ on sys.path so `import app...` resolves when run as scripts/<file>.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, lead_safety  # noqa: E402
from app.chat_core import run_turn  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.llm_service import _get_client  # noqa: E402

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


async def _judge_claimed(reply: str) -> bool | None:
    """Cross-validation: a SECOND model reads the reply in isolation and rules on
    whether it told the caller the enquiry was captured / someone will follow up —
    the same "say" the regex approximates, but robust to paraphrase the regex has
    never seen. Returns True/False, or None if the judge call itself failed (the
    caller then falls back to the regex verdict). LLM-as-judge — one model acts,
    another only verifies."""
    prompt = (
        "You are auditing a receptionist AI. A customer just gave their name and "
        "phone number and asked to be contacted. Here is the AI's reply:\n\n"
        f'"""\n{reply}\n"""\n\n'
        "Does the reply tell the customer their enquiry was captured, or that "
        "someone will follow up / call / be in touch? Answer with ONE word: "
        "YES or NO."
    )
    cfg_kwargs: dict = {"temperature": 0, "max_output_tokens": 16}
    thinking = getattr(types, "ThinkingConfig", None)
    if thinking is not None:  # 2.5-flash thinks by default; a yes/no needs none
        cfg_kwargs["thinking_config"] = thinking(thinking_budget=0)
    try:
        resp = await _get_client().aio.models.generate_content(
            model=get_settings().gemini_model,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
        ans = (resp.text or "").strip().upper()
        if ans.startswith("Y"):
            return True
        if ans.startswith("N"):
            return False
        return None
    except Exception as e:  # noqa: BLE001 — judge is best-effort; fall back to regex
        print(f"  (judge call failed: {str(e)[:100]})")
        return None


# Realistic UAE buyer names so the auto-captured rows read like a real lead board
# in the demo (kept to two words — the net's name extractor stores at most two).
_DEMO_NAMES = (
    "Omar Haddad",
    "Fatima Nasser",
    "Rashid Khan",
    "Layla Mansour",
    "Yusuf Rahman",
    "Aisha Siddiqui",
    "Karim Darwish",
    "Noor Farooqi",
    "Hassan Ali",
    "Mariam Saleh",
    "Bilal Ahmed",
    "Zainab Hussain",
    "Tariq Aziz",
    "Hind Sultan",
    "Faisal Habib",
)


async def _run_one(i: int, judge: bool = False) -> dict:
    """One lead conversation ending in a name + number; returns the verdict."""
    conv = f"saydo-{uuid.uuid4().hex[:10]}"
    name = _DEMO_NAMES[i % len(_DEMO_NAMES)]
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
    claimed_regex = bool(_CLAIM.search(reply or ""))
    # LLM-judge is authoritative when it returns a verdict; regex is the fallback.
    claimed_judge = await _judge_claimed(reply) if judge else None
    claimed = claimed_regex if claimed_judge is None else claimed_judge

    # Fire ONLY the deterministic net (skip anything else deferred), synchronously,
    # so we can read the DB the instant it's done.
    for fn, fn_args in deferred:
        if fn is lead_safety.ensure_lead_captured:
            fn(*fn_args)

    lead = db.find_recent_lead(BUSINESS_ID, phone)
    net_caught = (
        bool(lead) and lead.get("notes") == "auto-captured by the lead safety net"
    )
    return {
        "conv": conv,
        "phone": phone,
        "reply": reply,
        "tool_fired": tool_fired,
        "claimed": claimed,
        "claimed_regex": claimed_regex,
        "claimed_judge": claimed_judge,
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


_REPORT_CSS = """<style>
  :root{--ink:#0c1a24;--card:#152a37;--card2:#193140;--line:#254152;--text:#e9eff2;
    --soft:#9db0bb;--faint:#6f8492;--brass:#d1a24d;--brass2:#e6bd6f;--ok:#5fbf8a;--warn:#e88f6a;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;}
  *{box-sizing:border-box} body{margin:0;background:var(--ink);color:var(--text);
    font-family:var(--sans);line-height:1.5} .wrap{max-width:860px;margin:0 auto;padding:44px 22px 80px}
  .kick{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--brass);font-weight:700}
  h1{font-family:var(--serif);font-size:clamp(28px,5vw,40px);margin:10px 0 6px}
  .meta{color:var(--soft);font-size:14px;margin-bottom:26px}
  .num{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0 26px}
  .cell{flex:1;min-width:150px;background:var(--card2);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
  .cell b{display:block;font-size:40px;font-weight:800;color:var(--brass2);line-height:1;font-variant-numeric:tabular-nums}
  .cell.warn b{color:var(--warn)} .cell span{display:block;font-size:12.5px;color:var(--soft);margin-top:8px}
  table{width:100%;border-collapse:collapse;margin:6px 0 24px;font-size:13.5px}
  th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
  th{color:var(--faint);font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.08em}
  .gap{color:var(--warn);font-weight:700} .okk{color:var(--ok);font-weight:700}
  .lbl{font-size:11px;letter-spacing:.16em;text-transform:uppercase;font-weight:700;color:var(--brass2);margin:24px 0 8px}
  .ev{background:var(--card);border-left:3px solid var(--brass);border-radius:0 10px 10px 0;
    padding:10px 16px;margin:8px 0;font-family:var(--serif);font-size:16px;color:#fbf3e4}
  .xval{background:#5fbf8a12;border:1px dashed #5fbf8a66;border-radius:12px;padding:12px 16px;
    margin:20px 0;color:#dff0e7;font-size:14.5px}
  .head{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);
    border-radius:16px;padding:20px 22px;margin-top:26px;font-size:16px;line-height:1.6}
  .head b{color:var(--brass2)}
</style>"""


def _write_report(results: list[dict], judge: bool) -> str:
    """Write a self-contained HTML report of this run — the demo-ready view of the
    number, nicer than a terminal screenshot. Returns the path it wrote."""
    n = len(results)
    gaps = [r for r in results if r["say_do_gap"]]
    recovered = [r for r in gaps if r["net_caught"]]
    landed = [r for r in results if r["lead_in_db"]]
    via_tool = [r for r in results if r["lead_in_db"] and not r["net_caught"]]

    def pct(a, b):
        return f"{a / b * 100:.0f}%" if b else "—"

    rows = []
    for i, r in enumerate(results, 1):
        verdict = (
            '<span class="gap">SAY-DO GAP</span>'
            if r["say_do_gap"]
            else ("tool ok" if r["tool_fired"] else "no claim")
        )
        outcome = (
            '<span class="okk">recovered</span>'
            if r["net_caught"]
            else ("tool" if r["lead_in_db"] else '<span class="gap">LOST</span>')
        )
        rows.append(
            f"<tr><td>{i}</td><td>{'Y' if r['tool_fired'] else 'N'}</td>"
            f"<td>{'Y' if r['claimed'] else 'N'}</td><td>{verdict}</td><td>{outcome}</td></tr>"
        )

    evidence = (
        "".join(
            f'<div class="ev">“{html.escape((r["reply"] or "").strip()[:220])}…”</div>'
            for r in gaps[:3]
        )
        or '<div class="ev">(no say-do gaps in this run)</div>'
    )

    xval = ""
    if judge:
        checked = [r for r in results if r["claimed_judge"] is not None]
        agree = [r for r in checked if r["claimed_judge"] == r["claimed_regex"]]
        xval = (
            f'<div class="xval"><b>Cross-validation:</b> a 2nd model re-judged the '
            f"“claim” on {len(checked)}/{n} replies and agreed with the regex on "
            f"{len(agree)}/{len(checked)} ({pct(len(agree), len(checked))}). "
            f"The gap number doesn’t hinge on one brittle regex.</div>"
        )

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        "<title>Say-Do Gap — Eval Report</title>"
        + _REPORT_CSS
        + "</head><body><div class=wrap>"
        '<div class="kick">ReceptionAI · reliability eval</div>'
        "<h1>The say-do gap, measured</h1>"
        f'<div class="meta">{n} real lead conversations · {stamp} · '
        "the model claims it saved the lead; the deterministic net catches when it didn’t</div>"
        '<div class="num">'
        f'<div class="cell"><b>{pct(len(gaps), n)}</b><span>of conversations, the model '
        "claimed it saved the lead &amp; never called the tool</span></div>"
        f'<div class="cell"><b>{pct(len(recovered), len(gaps))}</b><span>of those recovered '
        "by the deterministic net</span></div>"
        f'<div class="cell warn"><b>{n - len(landed)}</b><span>leads lost, out of '
        f"{n}</span></div></div>"
        "<table><thead><tr><th>#</th><th>tool fired</th><th>reply claimed</th>"
        "<th>verdict</th><th>lead →</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        f"<p style='color:var(--soft);font-size:13.5px'>Captured: {len(landed)}/{n} "
        f"(via tool {len(via_tool)} · via net {len(recovered)}).</p>"
        + xval
        + '<div class="lbl">The model’s own words the moment it skipped the tool</div>'
        + evidence
        + '<div class="head">Headline: the agent claimed it captured the lead but skipped '
        f"the tool on <b>{len(gaps)}/{n}</b> conversations ({pct(len(gaps), n)}). The "
        f"deterministic net recovered <b>{pct(len(recovered), len(gaps))}</b> of them — "
        f"net result <b>{len(landed)}/{n}</b> captured, {n - len(landed)} lost.</div>"
        "</div></body></html>"
    )

    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(backend, "reports")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "say_do_gap_report.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path


async def main(trials: int, keep: bool = False, judge: bool = False) -> None:
    # Read the key the SAME way the app does (pydantic-settings loads backend/.env);
    # os.getenv alone would miss it. Run this from the backend/ folder.
    if not (get_settings().gemini_api_key or "").strip():
        sys.exit(
            "No Gemini key found. This eval calls the real model — set gemini_api_key "
            "in backend/.env and run from the backend/ folder."
        )
    print(f"Running {trials} real lead conversations through '{BUSINESS_ID}'…\n")

    results = []
    for i in range(trials):
        r = await _run_one(i, judge=judge)
        results.append(r)
        verdict = (
            "SAY-DO GAP"
            if r["say_do_gap"]
            else ("tool ok" if r["tool_fired"] else "no claim")
        )
        landed = (
            "recovered"
            if r["net_caught"]
            else ("tool" if r["lead_in_db"] else "LOST ✗")
        )
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
    print(
        f"  model called the tool itself ..... {sum(r['tool_fired'] for r in results)}"
    )
    print(
        f"  SAY-DO GAP (claimed, no tool) .... {len(gaps)}   ({pct(len(gaps), n)} of conversations)"
    )
    print(
        f"  ↳ recovered by the net ........... {len(recovered)}/{len(gaps)}   ({pct(len(recovered), len(gaps))})"
    )
    print(
        f"  leads captured (tool OR net) ..... {len(landed)}/{n}   ({pct(len(landed), n)})"
    )
    print(f"    · via the tool ................. {len(via_tool)}")
    print(f"    · via the deterministic net .... {len(recovered)}")
    print(f"  leads LOST ....................... {n - len(landed)}")
    print("=" * 60)

    if judge:
        checked = [r for r in results if r["claimed_judge"] is not None]
        agree = [r for r in checked if r["claimed_judge"] == r["claimed_regex"]]
        print(
            f"\n  Cross-validation — a 2nd model re-judged the 'claim' on "
            f"{len(checked)}/{n} replies;"
            f"\n  it agreed with the regex on {len(agree)}/{len(checked)} "
            f"({pct(len(agree), len(checked))}) — the gap number doesn't hinge on "
            f"one brittle regex."
        )

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

    try:
        report_path = _write_report(results, judge)
        print(
            f"\n  📄 Report saved → {report_path}"
            "\n     (open it full-screen for the demo — nicer than a terminal screenshot)"
        )
    except Exception as e:  # noqa: BLE001 — a failed report must never fail the run
        print(f"  (report not saved: {str(e)[:120]})")

    if keep:
        print(
            "\n  (--keep: test leads LEFT in the DB — your live proof query will show them)"
        )
    else:
        _cleanup(results)
        print(
            "\n  (throwaway test leads cleaned up — pass --keep to leave them for a demo)"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Measure the say-do gap + net recovery.")
    ap.add_argument(
        "--trials", type=int, default=12, help="how many lead conversations to run"
    )
    ap.add_argument(
        "--keep",
        action="store_true",
        help="don't delete the test leads — leave them so a live demo DB query shows them",
    )
    ap.add_argument(
        "--judge",
        action="store_true",
        help="cross-validate the 'claim' with a 2nd model (LLM-as-judge), not the "
        "regex alone — slower (one extra call per trial) but paraphrase-proof",
    )
    args = ap.parse_args()
    asyncio.run(main(args.trials, keep=args.keep, judge=args.judge))
