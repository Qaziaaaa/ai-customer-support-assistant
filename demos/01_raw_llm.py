"""Demo 1 — talk to the LLM with ZERO frameworks.

Run after: pip install openai && putting GROQ_API_KEY in .env

    python3 demos/01_raw_llm.py "What is your refund window?"

Why start here?
LangChain/LangGraph wrap this exact HTTP call. Before using the wrappers,
see what they actually wrap: a list of messages in, text out.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running the demo without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI  # noqa: E402

from src.config import ConfigError, get_settings  # noqa: E402
from src.data.policies import SYSTEM_PROMPT  # noqa: E402

# Groq exposes an OpenAI-compatible endpoint — same SDK, different base_url.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"


def main() -> None:
    question = " ".join(sys.argv[1:]) or "What is your refund window?"

    try:
        settings = get_settings()
    except ConfigError as exc:
        print(f"CONFIG ERROR\n{exc}", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=settings.groq_api_key, base_url=GROQ_BASE_URL)

    # The entire LLM contract: messages in → assistant message out.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
    except Exception as exc:  # network, auth, rate limit…
        print(f"LLM CALL FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    answer = response.choices[0].message.content
    usage = response.usage
    print(f"Q: {question}\n")
    print(f"A: {answer}\n")
    print(f"[tokens — prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}]")


if __name__ == "__main__":
    main()
