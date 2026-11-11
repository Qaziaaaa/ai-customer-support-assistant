"""Central configuration — loads secrets from `.env` once, validates them.

Why this file exists:
- Keeps every other module free of `os.environ` lookups.
- Fails fast with a *human* error message (which key is missing, where to
  get it) instead of a cryptic API 401 deep inside a library.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root regardless of where the process started.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    langsmith_api_key: str | None
    langsmith_tracing: bool
    langsmith_project: str


def _require(name: str, hint: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("your_"):
        raise ConfigError(
            f"Missing or placeholder value for {name}.\n"
            f"  → {hint}\n"
            f"  → Then put it in {PROJECT_ROOT / '.env'} "
            f"(copy .env.example if you have not yet)."
        )
    return value


def get_settings() -> Settings:
    """Return validated settings, raising ConfigError with fix instructions."""
    groq_key = _require(
        "GROQ_API_KEY",
        "Get a free key at https://console.groq.com/keys (no credit card).",
    )
    langsmith_key = os.environ.get("LANGSMITH_API_KEY", "").strip() or None
    if langsmith_key and langsmith_key.startswith("your_"):
        langsmith_key = None
    tracing = os.environ.get("LANGSMITH_TRACING", "false").lower() == "true"
    if tracing and langsmith_key is None:
        tracing = False  # cannot trace without a key — degrade silently
    project = os.environ.get("LANGSMITH_PROJECT", "novamart-support").strip()
    return Settings(
        groq_api_key=groq_key,
        langsmith_api_key=langsmith_key,
        langsmith_tracing=tracing,
        langsmith_project=project,
    )
