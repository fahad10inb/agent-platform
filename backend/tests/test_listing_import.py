"""Listings import: field normalization across sources, CSV/XML/Reelly parsing,
the import endpoint, and the permit-gated prompt rendering."""

from app import db, listing_import
from app.prompt_service import build_system_prompt

ADMIN = {"X-API-Key": "admin_test_key"}


# ── normalization (aliases across CRMs/portals) ──────────────────────────────
def test_normalize_maps_varied_field_names():
    raw = {"Property Title": "2BR Marina", "Community": "Dubai Marina", "Beds": "2",
           "Asking Price": "1.8M", "Offering Type": "sale", "Trakheesi": "7129XYZ",
           "Ref No": "SR-11", "Description": "high floor"}
    n = listing_import.normalize_listing(raw)
    assert n["title"] == "2BR Marina" and n["area"] == "Dubai Marina" and n["bedrooms"] == "2"
    assert n["price"] == "1.8M" and n["purpose"] == "sale"
    assert n["permit_number"] == "7129XYZ" and n["reference"] == "SR-11" and n["notes"] == "high floor"


def test_normalize_drops_a_titleless_record():
    assert listing_import.normalize_listing({"price": "1M", "area": "JVC"}) is None


# ── CSV / XML parsing ────────────────────────────────────────────────────────
def test_parse_csv():
    csv_text = ("title,area,beds,price,purpose,permit\n"
                "2BR Marina,Dubai Marina,2,1.8M,sale,7129XYZ\n"
                "Studio Bay,Business Bay,studio,650k,sale,\n")
    rows = listing_import.parse_csv(csv_text)
    assert len(rows) == 2
    assert rows[0]["permit_number"] == "7129XYZ" and rows[1]["permit_number"] == ""


def test_parse_xml():
    xml = """<list>
      <property><title>Villa AR</title><community>Arabian Ranches</community>
        <bedrooms>3</bedrooms><price>2.9M</price><permit_number>RERA-55</permit_number></property>
      <property><name>1BR JVC</name><location>JVC</location><beds>1</beds><rent>58k</rent></property>
    </list>"""
    rows = listing_import.parse_xml(xml)
    assert len(rows) == 2
    assert rows[0]["title"] == "Villa AR" and rows[0]["permit_number"] == "RERA-55"
    assert rows[1]["title"] == "1BR JVC" and rows[1]["area"] == "JVC"


def test_reelly_normalizes_fetched_json(monkeypatch):
    monkeypatch.setattr(listing_import, "_fetch_raw_authed",
                        lambda url, key: '{"data":[{"name":"Off-plan Tower","community":"JVC",'
                                         '"bedrooms":"1","price":"900k","permit":"DLD-9"}]}')
    rows = listing_import.fetch_reelly("key123")
    assert rows[0]["title"] == "Off-plan Tower" and rows[0]["permit_number"] == "DLD-9"


# ── the import endpoint ──────────────────────────────────────────────────────
def test_import_endpoint_replaces_the_sheet(client):
    csv_text = "title,area,beds,price,permit\n2BR Marina,Dubai Marina,2,1.8M,7129XYZ\n"
    r = client.post("/manage/skyline-realty/listings/import",
                    json={"format": "csv", "data": csv_text}, headers=ADMIN)
    assert r.status_code == 200
    assert r.json() == {"status": "imported", "count": 1, "with_permit": 1}
    rows = db.list_listings("skyline-realty")
    assert rows[0]["title"] == "2BR Marina" and rows[0]["permit_number"] == "7129XYZ"


def test_import_endpoint_rejects_empty_and_needs_auth(client):
    assert client.post("/manage/skyline-realty/listings/import",
                       json={"format": "csv", "data": "title,area\n"}).status_code == 401
    r = client.post("/manage/skyline-realty/listings/import",
                    json={"format": "csv", "data": "nothing,useful\n"}, headers=ADMIN)
    assert r.status_code == 422  # no listings found


# ── permit-gated prompt ──────────────────────────────────────────────────────
def test_prompt_marks_permitted_and_unpermitted_listings(client):
    db.replace_listings("skyline-realty", [
        {"title": "2BR Marina", "area": "Dubai Marina", "price": "1.8M", "permit_number": "7129XYZ"},
        {"title": "Villa JVC", "area": "JVC", "price": "3M"},  # no permit
    ])
    p = build_system_prompt(db.get_business("skyline-realty"))
    assert "permit 7129XYZ" in p
    assert "[NO PERMIT]" in p
    assert "illegal to advertise a property without a valid advertising permit" in p
