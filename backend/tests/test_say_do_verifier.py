"""The general say-do verifier: does the reply CLAIM an action the tools didn't
actually perform? Pure reconciliation — this is the always-on reliability signal
that generalizes the lead-capture net to every action (booking, reschedule,
handoff, ...). It must fire on a real gap and stay silent when the tool backed
the claim (a noisy verifier is worse than a quiet one)."""

from app import say_do_verifier


def _act(*names):
    return [{"name": n, "args": {}, "result": None} for n in names]


def test_claim_without_the_tool_is_a_gap():
    gaps = say_do_verifier.detect("You're all booked for Tuesday at 3pm!", activity=[])
    assert len(gaps) == 1
    assert gaps[0]["action"] == "appointment booked"
    assert "book_appointment" in gaps[0]["expected_tool"]


def test_claim_backed_by_the_tool_is_not_a_gap():
    gaps = say_do_verifier.detect(
        "You're all booked for Tuesday at 3pm!", _act("book_appointment")
    )
    assert gaps == []


def test_lead_claim_backed_by_qualify_counts_as_backed():
    # The lead claim is satisfied by EITHER lead tool — qualify_lead here.
    gaps = say_do_verifier.detect(
        "Noted your details — an agent will call you shortly.", _act("qualify_lead")
    )
    assert gaps == []


def test_lead_claim_with_no_lead_tool_is_a_gap():
    gaps = say_do_verifier.detect(
        "Got your details, someone will reach out today.", _act("check_availability")
    )
    assert [g["action"] for g in gaps] == ["lead / follow-up"]


def test_handoff_claim_without_request_human_is_a_gap():
    gaps = say_do_verifier.detect(
        "Sure — connecting you to a human agent now.", activity=[]
    )
    assert [g["action"] for g in gaps] == ["human handoff"]


def test_plain_informational_reply_never_flags():
    # No claim of an action → no gap, no matter what ran (or didn't).
    assert say_do_verifier.detect("We're open 9 to 6, Sunday to Thursday.", []) == []
    assert say_do_verifier.detect("Our address is 12 Marina Walk.", None) == []


def test_multiple_independent_gaps_in_one_reply():
    reply = "You're booked for Tuesday, and I'm connecting you to an agent."
    gaps = say_do_verifier.detect(reply, activity=[])
    actions = {g["action"] for g in gaps}
    assert actions == {"appointment booked", "human handoff"}


def test_malformed_activity_entries_are_tolerated():
    # Real transcripts can carry odd shapes; detect must never raise.
    assert say_do_verifier.detect("You're booked!", [None, {}, {"name": None}])
