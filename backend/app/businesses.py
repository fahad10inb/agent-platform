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
        "faq": (
            "We accept most major insurance plans; bring your card and we'll verify on arrival. "
            "Free parking is available behind the building. We welcome children and offer family "
            "appointments. First visits take about 45 minutes. Emergencies: call and we'll fit you in."
        ),
        # Demo key (protects only demo data). Real businesses get a random key
        # generated at onboarding — never a committed constant.
        "api_key": "bizkey_bright_smile_demo",
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
        "faq": (
            "Walk-ins welcome when we have space, but booking is best. Parking is on the street "
            "or the garage next door. Balayage takes 2-3 hours; please arrive with dry, unwashed "
            "hair for color. We sell gift cards. Cancellations within 24 hours may incur a fee."
        ),
        "api_key": "bizkey_velvet_hair_demo",
    },
]
