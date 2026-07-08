"""Property listings: endpoint auth + validation, replace semantics, and the
prompt block that lets the agent shortlist REAL properties — and only those."""

from app import db
from app.prompt_service import build_system_prompt

ADMIN = {"X-API-Key": "admin_test_key"}
BRIGHT = {"X-API-Key": "bizkey_bright_smile_demo"}

SHEET = {
    "listings": [
        {"title": "2BR apartment, Bloom Towers", "area": "JVC", "bedrooms": "2",
         "price": "1.2M", "purpose": "sale", "notes": "ready, near park"},
        {"title": "1BR apartment, Marina Gate", "area": "Dubai Marina", "bedrooms": "1",
         "price": "95k/yr", "purpose": "rent"},
    ]
}


def test_listings_endpoint_auth_matrix(client):
    """Deny by default, deny cross-tenant, allow own key and admin."""
    assert client.post("/manage/skyline-realty/listings", json=SHEET).status_code == 401
    assert client.post("/manage/skyline-realty/listings", json=SHEET, headers=BRIGHT).status_code == 403
    assert client.post("/manage/skyline-realty/listings", json=SHEET, headers=ADMIN).status_code == 200


def test_listings_validation(client):
    for bad in (
        {"listings": [{"title": ""}]},
        {"listings": [{"title": "x" * 121}]},
        {"listings": [{"title": f"unit {i}"} for i in range(101)]},
    ):
        assert client.post("/manage/skyline-realty/listings", json=bad, headers=ADMIN).status_code == 422


def test_replace_semantics_and_manage_prefill(client):
    client.post("/manage/skyline-realty/listings", json=SHEET, headers=ADMIN)
    smaller = {"listings": [{"title": "Studio, Business Bay", "price": "650k", "purpose": "sale"}]}
    client.post("/manage/skyline-realty/listings", json=smaller, headers=ADMIN)
    rows = client.get("/manage/skyline-realty", headers=ADMIN).json()["listings_rows"]
    assert [r["title"] for r in rows] == ["Studio, Business Bay"]  # replaced, not appended


def test_prompt_carries_the_sheet_and_the_only_these_rule(client):
    db.replace_listings("skyline-realty", [dict(r) for r in SHEET["listings"]])
    p = build_system_prompt(db.get_business("skyline-realty"))
    assert "CURRENT LISTINGS" in p
    # These seed rows carry NO permit, so the hard gate withholds their price,
    # purpose AND notes (a description can hide a price) — only title/area/beds
    # + the withheld marker show.
    assert "2BR apartment, Bloom Towers — JVC — 2 BR [NO PERMIT — price withheld]" in p
    assert "1.2M" not in p and "near park" not in p  # price and description gone
    assert "the ONLY properties that exist" in p
    # And a business with no sheet gets no block (nothing changes for salons).
    assert "CURRENT LISTINGS" not in build_system_prompt(db.get_business("bright-smile"))
