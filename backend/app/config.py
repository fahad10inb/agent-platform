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

    # --- Secrets (placeholders — not used until later lessons) ---
    # Empty for now. We'll fill these when we add the AI brain and the database.
    gemini_api_key: str = ""
    database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return ONE shared, cached Settings instance.

    `@lru_cache` makes this run only the first time; every later call returns
    the exact same object. So we read the environment once, not on every request.
    """
    return Settings()
