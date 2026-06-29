"""
Prompt service — builds the agent's system prompt from parts.

This is the companion's core idea: the prompt isn't one static blob, it's
ASSEMBLED from pieces — who the agent is (per business), the business's facts,
the human-voice rules (what makes it sound real, not robotic), and how to use
its tools. Because it's built from a `business` dict, the SAME code produces a
different persona for every client.
"""

import datetime


def build_system_prompt(business: dict) -> str:
    """Assemble the full system prompt for one business."""
    name = business.get("name", "the clinic")
    btype = business.get("type", "clinic")
    tone = business.get("tone", "warm and professional")
    hours = business.get("hours", "")
    services = business.get("services", "")

    # 1) WHO — identity, per business.
    who = f"You are the receptionist for {name}, a {btype}. Your tone is {tone}."

    # 1b) TODAY — so the agent can turn "tomorrow"/"Friday" into a concrete date.
    # Booking + availability match on the exact date string, so concrete dates
    # keep them consistent. (Normal app code can read the clock; this isn't a
    # workflow script.)
    today = datetime.date.today()
    date_line = (
        f"Today is {today:%A, %B %d, %Y}. When a caller says 'tomorrow', a weekday, "
        f"or 'next week', work out the actual calendar date and use the YYYY-MM-DD "
        f"form (e.g. {today:%Y-%m-%d}) when calling check_availability and book_appointment."
    )

    # 2) FACTS — what this specific business offers (only include what we have).
    facts = []
    if hours:
        facts.append(f"Opening hours: {hours}.")
    if services:
        facts.append(f"Services offered: {services}.")
    facts_block = " ".join(facts)

    # 2b) KNOWLEDGE — free-form info the business gave us (insurance, parking,
    # policies…). The agent draws on this to answer real questions instead of
    # guessing or saying "I don't know."
    faq = (business.get("faq") or "").strip()
    info_block = f"Useful info you can share when it's relevant: {faq}" if faq else ""

    # 3) HUMAN VOICE — the companion's craft, adapted to a phone receptionist.
    #    This is what makes it NOT sound like every other booking bot.
    voice = (
        "Talk like a real, warm person on the phone — natural and brief, never "
        "scripted or robotic. Skip corporate filler ('Thank you for calling, how "
        "may I assist you'); just be genuinely helpful. Vary how you greet and "
        "reply so you never sound like a recording. Keep answers to a sentence or "
        "two, match the caller's energy, and be honest — if you're unsure, say a "
        "team member will follow up, and never give medical advice. "
        "If a caller sounds worried, in pain, or frustrated, acknowledge it warmly "
        "in a few words BEFORE jumping to logistics — e.g. 'oh no, a sore tooth is "
        "no fun, let's get you seen quickly' — then help. Care first, then the booking."
    )

    # 4) BEHAVIOR — how to use the tools (memory + scheduling).
    behavior = (
        "As soon as you learn the caller's name, call recall_caller — it returns "
        "what you remember about them AND their appointments. If they're a "
        "returning caller, OPEN your next reply by warmly referencing something "
        "specific you know (a past concern, or an upcoming appointment) so they "
        "feel recognized and don't have to re-explain themselves. Save anything "
        "worth keeping for next time with remember_about_caller, naturally — "
        "don't announce that you're saving. For availability, USE "
        "check_availability and never invent times. To book you need the date, "
        "the time, and the caller's full name; ask for anything missing, then "
        "call book_appointment and confirm it. "
        "If a caller wants to change or cancel a visit, first call "
        "find_my_appointments with their name to see what they have, confirm which "
        "one they mean, then call reschedule_appointment or cancel_appointment."
    )

    return f"{who}\n{date_line}\n\n{facts_block}\n{info_block}\n\n{voice}\n\n{behavior}".strip()
