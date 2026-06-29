"""
Seed businesses — demo clients we load into the DB at startup so there's data
to test with. In production these come from real onboarding (one row per client,
inserted via db.upsert_business). Each needs a unique `id` that requests carry.
"""

SEED_BUSINESSES = [
    {
        "id": "bright-smile",
        "name": "Bright Smile Dental",
        "type": "dental clinic",
        "hours": "Monday to Friday, 9am to 5pm",
        "services": "checkups, cleanings, fillings, crowns, and whitening",
        "tone": "warm and reassuring",
        "open_hour": 9,  # 9am
        "close_hour": 17,  # 5pm (last slot starts before this)
        "slot_minutes": 30,
    },
    {
        "id": "velvet-hair",
        "name": "Velvet Hair Studio",
        "type": "hair salon",
        "hours": "Tuesday to Saturday, 10am to 7pm",
        "services": "cuts, color, balayage, and blowouts",
        "tone": "chic and friendly",
        "open_hour": 10,  # 10am
        "close_hour": 19,  # 7pm
        "slot_minutes": 30,
    },
]
