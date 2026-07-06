"""
Application configuration.

EVERY setting here is read from an environment variable (or a local `.env`
file) — never hard-coded. Secrets like API keys must not live in the code or
in git. This file is the single place the whole app asks "what are my settings?"

How it works: `Settings` lists the settings we support. `pydantic-settings`
reads each one from the matching environment variable, checks its type, and
uses the default if the variable isn't set.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Read variables from a file named ".env" in the backend folder (if present),
    # in addition to the real environment. `extra="ignore"` means unknown env
    # vars don't crash us.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App basics ---
    # The field name `app_name` maps to the env var APP_NAME (case-insensitive).
    app_name: str = "agent-platform"
    environment: str = "development"  # "development" or "production"

    # --- LLM tuning (env-tunable; no deploy needed to dial the voice) ---
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.7
    # A receptionist answers in a couple of sentences; this cap stops a runaway
    # generation from producing (and billing) an essay.
    gemini_max_output_tokens: int = 1024
    # Hard ceiling on one model call (seconds), including its tool round-trips.
    llm_timeout_seconds: float = 45.0

    # --- Background memory passes (kill switches, no deploy needed) ---
    # Distillation re-reads a finished-ish conversation and files durable caller
    # preferences into memory; consolidation merges a caller's pile of notes into
    # a few crisp ones. Both are best-effort background work — these flags exist
    # so a misbehaving pass can be switched off from the environment instantly.
    distill_enabled: bool = True
    consolidate_enabled: bool = True

    # --- Secrets ---
    gemini_api_key: str = ""
    database_url: str = ""
    # Master key for admin endpoints (listing all businesses, reading any
    # business's bookings). Set ADMIN_API_KEY in the environment. Empty = admin
    # endpoints are locked (secure by default).
    admin_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return ONE shared, cached Settings instance.

    `@lru_cache` makes this run only the first time; every later call returns
    the exact same object. So we read the environment once, not on every request.
    """
    return Settings()
