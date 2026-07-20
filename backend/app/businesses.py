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
        "vertical": "clinic",
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
        "vertical": "salon",
    },
    {
        "id": "skyline-realty",
        "name": "Skyline Realty",
        "type": "real estate agency",
        "hours": "Daily, 9am to 8pm",
        "services": "apartments and villas for sale and rent across Dubai",
        "tone": "polished and proactive",
        "open_hour": 9,
        "close_hour": 20,
        "slot_minutes": 30,
        "faq": (
            "We cover Dubai Marina, Downtown, JVC, Business Bay and more, for both sale and rent. "
            "Viewings are arranged with an agent; bring Emirates ID for paperwork. We can advise on "
            "mortgages and rental contracts (Ejari). Tell us your budget and area and we'll shortlist."
        ),
        "api_key": "bizkey_skyline_realty_demo",
        "vertical": "real_estate",
        # Real-estate agency profile — what the AI knows about the agency.
        "areas_covered": "Dubai Marina, JVC, Downtown Dubai, Business Bay, Dubai Hills, Arabian Ranches",
        "deal_focus": "Secondary sales and rentals, plus select off-plan",
        "languages": "English, Arabic, Hindi, Russian",
        "orn": "28154",
        "staff": (
            "Omar Haddad — Marina & JBR (English/Arabic) · "
            "Jessica Tan — Dubai Hills & Ranches (English) · "
            "Ravi Menon — JVC & Business Bay (English/Hindi)"
        ),
    },
    {
        "id": "handy-home",
        "name": "Handy Home Services",
        "type": "home maintenance company",
        "hours": "Sunday to Friday, 8am to 6pm",
        "services": "AC servicing, plumbing, electrical, handyman, and deep cleaning",
        "tone": "friendly and dependable",
        "open_hour": 8,
        "close_hour": 18,
        "slot_minutes": 60,
        "faq": (
            "We serve all of Dubai. Same-day visits when slots allow. We give a free quote before any "
            "work. Payment by card or cash on completion. For emergencies, tell us and we'll prioritise."
        ),
        "api_key": "bizkey_handy_home_demo",
        "vertical": "general",
    },
]
