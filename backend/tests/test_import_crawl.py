"""The import crawler's link selection: same-site matching that survives www.
mismatches, scoring that prefers hub pages over leaf articles, and top-N
picking instead of first-N."""

from app.import_service import _pick_links, _same_site, _score_link


def test_same_site_ignores_www_prefix():
    assert _same_site("https://fadelab.ae", "https://www.fadelab.ae/services")
    assert _same_site("https://www.fadelab.ae", "https://fadelab.ae/prices")
    assert not _same_site("https://fadelab.ae", "https://instagram.com/fadelab")


def test_pick_links_takes_the_best_not_the_first():
    """A clinic with 40 treatment articles: /our-services and /prices must win
    even when leaf articles appear first in the document."""
    hrefs = (
        [f"/{x}-treatment-dubai/" for x in ("gum", "root-canal", "tmj", "bioclear")]
        + ["/our-services/", "/prices/", "/contact/", "/blog/some-post/"]
    )
    picked = _pick_links("https://clinic.ae", hrefs)
    assert "https://clinic.ae/our-services/" in picked[:2]
    assert "https://clinic.ae/prices/" in picked[:2]


def test_pick_links_survives_www_mismatch_and_junk():
    hrefs = ["https://www.clinic.ae/services", "mailto:hi@clinic.ae", "tel:+97150",
             "#top", "javascript:void(0)", "https://facebook.com/clinic/book"]
    assert _pick_links("https://clinic.ae", hrefs) == ["https://www.clinic.ae/services"]


def test_pick_links_dedupes_paths_and_skips_homepage():
    hrefs = ["/services", "/services/", "https://clinic.ae/services", "/"]
    assert len(_pick_links("https://clinic.ae", hrefs)) == 1


def test_score_prefers_hub_pages():
    assert _score_link("/our-services/") > _score_link("/gum-treatment-recovery/tips/deep")
    assert _score_link("/random-blog-post/") == 0
