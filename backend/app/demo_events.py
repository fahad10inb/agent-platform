"""
The demo's "what the AI just did" feed.

The chat widget shows a conversation; it hides the work. An owner watching a demo
sees a chat bubble and thinks "a chatbot" — they never see that the agent QUALIFIED
the buyer, SCORED them, matched real inventory, withheld an unpermitted price, and
booked a viewing. That invisible work is the entire product.

This module turns the raw tool calls the model actually executed (scraped by
llm_service._tool_calls from the SDK's function-calling transcript) into an
operator-facing feed. Nothing here is scripted: if the model didn't run the tool,
no event appears.
"""


def _s(value) -> str:
    """A short, printable form of a tool argument."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip()


def _joined(args: dict, keys: tuple[str, ...]) -> str:
    """The present values of `keys`, in order, as a '·'-separated line."""
    parts = [_s(args.get(k)) for k in keys]
    return " · ".join(p for p in parts if p)


def _unwrap(result) -> dict:
    """A tool's own return value, out of the SDK's envelope.

    google-genai reports a function response as {"result": <what the tool
    returned>}. Reading the envelope instead of the payload silently loses every
    field — which is exactly how the A/B/C grade and the free-slot count went
    missing from the feed. Tolerates both shapes."""
    if isinstance(result, dict):
        if set(result.keys()) == {"result"} and isinstance(result["result"], dict):
            return result["result"]
        return result
    return {}


def _grade(result) -> str:
    """The A/B/C grade a qualification returned. qualify_lead returns it as
    `score`; the other keys are defensive."""
    payload = _unwrap(result)
    for key in ("score", "grade", "rating", "tier"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip().upper() in {"A", "B", "C"}:
            return value.strip().upper()
    return ""


def humanize(calls: list[dict]) -> list[dict]:
    """Raw tool calls → the demo feed.

    Each event is {kind, title, detail, tone, badge}. `tone` drives the colour:
    ok (something was captured/booked), hot (an A-grade lead), warn (compliance /
    escalation — the moments that reassure a cautious owner), info (routine).
    """
    events: list[dict] = []
    for call in calls or []:
        name = (call.get("name") or "").strip()
        args = call.get("args") or {}
        result = call.get("result")

        if name == "capture_lead":
            events.append({
                "kind": name, "tone": "ok", "badge": "",
                "title": "Lead captured",
                "detail": _joined(args, ("name", "phone", "interest")) or "new enquiry",
            })
        elif name == "qualify_lead":
            grade = _grade(result)
            events.append({
                "kind": name, "tone": "hot" if grade == "A" else "ok", "badge": grade,
                "title": "Qualified & scored",
                "detail": _joined(
                    args, ("budget", "area", "bedrooms", "purpose", "timeline", "pay_method")
                ) or "buyer details captured",
            })
        elif name == "check_availability":
            slots = _unwrap(result).get("available_slots")
            detail = _s(args.get("date"))
            if isinstance(slots, list):
                detail = f"{detail} — {len(slots)} slots free".strip(" —")
            events.append({
                "kind": name, "tone": "info", "badge": "",
                "title": "Checked the calendar", "detail": detail,
            })
        elif name == "book_appointment":
            ok = _unwrap(result).get("status") != "unavailable"
            events.append({
                "kind": name, "tone": "ok" if ok else "warn", "badge": "",
                "title": "Viewing booked" if ok else "Slot unavailable — no double-booking",
                "detail": _joined(args, ("date", "time", "patient_name", "reason")),
            })
        elif name == "reschedule_appointment":
            events.append({
                "kind": name, "tone": "ok", "badge": "",
                "title": "Appointment moved", "detail": _joined(args, ("new_date", "new_time")),
            })
        elif name == "cancel_appointment":
            events.append({
                "kind": name, "tone": "info", "badge": "",
                "title": "Appointment cancelled", "detail": _joined(args, ("date", "time")),
            })
        elif name == "confirm_appointment":
            events.append({
                "kind": name, "tone": "ok", "badge": "",
                "title": "Appointment confirmed", "detail": _joined(args, ("date", "time")),
            })
        elif name == "recall_caller":
            payload = _unwrap(result)
            returning = bool(payload.get("returning_caller"))
            visits = payload.get("visit_count")
            events.append({
                "kind": name, "tone": "ok" if returning else "info", "badge": "",
                "title": "Recognised the caller" if returning else "Checked caller history",
                "detail": (f"returning · {visits} previous visit(s)" if returning
                           else "no history on file — new contact"),
            })
        elif name == "remember_about_caller":
            events.append({
                "kind": name, "tone": "info", "badge": "",
                "title": "Remembered for next time", "detail": _joined(args, ("note", "caller_name")),
            })
        elif name == "find_my_appointments":
            events.append({
                "kind": name, "tone": "info", "badge": "",
                "title": "Looked up their appointments", "detail": _s(args.get("caller_name")),
            })
        elif name == "request_human":
            events.append({
                "kind": name, "tone": "warn", "badge": "",
                "title": "Handed to a human", "detail": _joined(args, ("reason", "name", "phone")),
            })
        elif name == "stop_contact":
            events.append({
                "kind": name, "tone": "warn", "badge": "PDPL",
                "title": "Do-not-contact recorded", "detail": _s(args.get("phone")),
            })
        elif name:
            # An unmapped tool still shows — better an honest generic row than a
            # silent gap that makes the feed look like it missed something.
            events.append({
                "kind": name, "tone": "info", "badge": "",
                "title": name.replace("_", " ").capitalize(), "detail": "",
            })
    return events
