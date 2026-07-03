"""Prompt assembly: per-business persona, UAE-time date line, vertical steering."""

import datetime
import zoneinfo

from app.prompt_service import build_system_prompt


def test_prompt_carries_the_business_identity():
    p = build_system_prompt({"name": "Velvet Hair", "type": "salon", "tone": "chic and warm"})
    assert "Velvet Hair" in p
    assert "chic and warm" in p


def test_date_line_uses_uae_time_not_server_utc():
    p = build_system_prompt({"name": "X", "type": "clinic"})
    uae_today = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Dubai")).date()
    assert f"{uae_today:%Y-%m-%d}" in p


def test_real_estate_vertical_steers_to_leads():
    p = build_system_prompt({"name": "Skyline", "type": "real estate agency", "vertical": "real_estate"})
    assert "capture_lead" in p


def test_faq_lands_in_the_prompt():
    p = build_system_prompt({"name": "X", "type": "clinic", "faq": "We accept Daman insurance."})
    assert "Daman" in p
