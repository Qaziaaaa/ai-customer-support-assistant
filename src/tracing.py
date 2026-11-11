"""LangSmith tracing — observability for the agent.

What LangSmith does: every LLM call, tool execution and graph node becomes
a nested "run" (span) you can inspect at https://smith.langchain.com.
When something answers wrong, the trace shows *which hop* misbehaved:
bad prompt? wrong tool args? tool returned garbage?

How it attaches (the important part): LangChain/LangGraph read these env
vars automatically —
    LANGSMITH_TRACING=true     → turn tracing on
    LANGSMITH_API_KEY=...      → authenticate
    LANGSMITH_PROJECT=...      → group runs in a project
No code changes inside graph.py/llm.py are needed; instrumentation is
baked into the libraries. This module just makes the env explicit (and
covers the legacy LANGCHAIN_* aliases some tools still expect).

Tracing is OPTIONAL by design: if the key is missing, the app runs
identically with zero traces. Observability must never break the product.
"""

from __future__ import annotations

import os

from src.config import get_settings


def setup_tracing() -> bool:
    """Configure LangSmith env vars from .env. Returns True if active.

    Call once at startup (UI entry / demo scripts) BEFORE any LLM calls.
    """
    try:
        settings = get_settings()
    except Exception:
        return False  # no config → no tracing, no crash

    if not (settings.langsmith_tracing and settings.langsmith_api_key):
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    # Legacy aliases — some LangChain versions still read these.
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    return True


def trace_url(project: str | None = None) -> str:
    """Deep link to the project's trace list (shown in the UI sidebar)."""
    from src.config import get_settings

    proj = project or get_settings().langsmith_project
    return f"https://smith.langchain.com/projects/{proj}"
