"""Every page must be reachable AND must lead somewhere.

A prospect walking a demo should never hit a dead end. This locks the site's link
graph: each page serves, each internal link resolves, and no page traps the
visitor with no way out. (All three of these regressed at once: /demo had no way
home and no owner's view, /dashboard trapped you after sign-in, and /privacy was
orphaned — nothing linked to it.)"""

import re

PAGES = [
    "/",
    "/watch",
    "/demo?business_id=skyline-realty",
    "/widget?business_id=skyline-realty",
    "/dashboard",
    "/privacy",
]


def _links(html: str) -> set[str]:
    """Internal hrefs on a page (absolute paths only; anchors handled separately)."""
    return {h for h in re.findall(r'href="(/[^"]*)"', html)}


def test_every_page_serves(client):
    for path in PAGES:
        assert client.get(path).status_code == 200, path


def test_no_page_is_a_dead_end(client):
    """Every page offers at least one way out."""
    for path in PAGES:
        html = client.get(path).text
        assert _links(html), f"{path} has no internal links — it's a dead end"


def test_every_internal_link_resolves(client):
    """No broken link anywhere on the site."""
    for path in PAGES:
        for link in _links(client.get(path).text):
            assert client.get(link).status_code == 200, f"{path} -> {link} is broken"


def test_the_demo_completes_the_pitch(client):
    """The demo must go home AND hand off to the owner's dashboard — the last
    beat of the pitch is 'the lead you just watched it capture is waiting here'."""
    html = client.get("/demo?business_id=skyline-realty").text
    links = _links(html)
    assert "/" in links, "the demo can't get back to the site"
    assert "/dashboard" in links, "the demo doesn't hand off to the owner's view"


def test_the_landing_page_reaches_the_operator_demo_and_the_privacy_policy(client):
    """A broker asking 'show me' or 'where's your privacy policy?' must not be
    met with nothing."""
    links = _links(client.get("/").text)
    assert any(link.startswith("/demo?") for link in links), "no route to the live demo"
    assert "/privacy" in links, "the privacy policy is orphaned"


def test_landing_anchors_point_at_real_sections(client):
    html = client.get("/").text
    for anchor in set(re.findall(r'href="#([a-zA-Z0-9_-]+)"', html)):
        assert f'id="{anchor}"' in html, f'#{anchor} has no matching section'
