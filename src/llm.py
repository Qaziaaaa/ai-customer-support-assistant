"""LLM factory — the single place that knows *which* provider we use.

Why a factory function instead of importing ChatGroq everywhere?
- One swap point: later you can add Gemini/OpenAI branches here and no
  other file changes (Open/Closed for the rest of the codebase).
- One place to apply cross-cutting settings (temperature, timeouts,
  LangSmith tagging).

LangChain's role in one sentence: it normalizes dozens of providers behind
one interface — `llm.invoke(messages)` returns an AIMessage regardless of
Groq, OpenAI or Gemini underneath.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

from src.config import get_settings

# Groq free tier. gpt-oss-120b: 3/3 reliable tool-calling in our tests
# (qwen3.8-27b occasionally emitted malformed tool calls; llama-3.3 removed).
DEFAULT_MODEL = "openai/gpt-oss-120b"


@lru_cache(maxsize=1)
def get_llm(model: str = DEFAULT_MODEL) -> BaseChatModel:
    """Return a configured chat model.

    lru_cache: Streamlit reruns the script constantly — building the client
    once per process avoids re-instantiating on every interaction.
    """
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=model,
        temperature=0,  # support answers should be deterministic
        max_tokens=800,  # free tier caps output at 1000 tokens/min — stay under
    )
