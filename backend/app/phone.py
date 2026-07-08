"""Phone-number helpers, shared across channels (reminders, portal lead-intake).

WhatsApp identifies a person by their number in E.164 digits (e.g. 971501234567),
and that same string is our conversation_id for a WhatsApp thread — so a portal
lead's '+971 50 123 4567' and the wa-<sender> Meta later reports MUST normalize
to the same value, or an outreach and its reply land in two different threads.
"""


def to_wa_number(phone: str) -> str:
    """UAE mobile → WhatsApp E.164 digits: '0501234567' / '+971 50 123 4567' /
    '00971501234567' all become '971501234567'. Non-UAE inputs pass through as
    their bare digits."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = "971" + digits[1:]
    return digits
