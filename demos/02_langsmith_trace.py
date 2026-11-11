"""Demo 2 — watch one agent turn show up in LangSmith.

Prereqs:
  1. GROQ_API_KEY + LANGSMITH_API_KEY in .env (both free, no card)
  2. pip install -r requirements.txt

Run:
  python3 demos/02_langsmith_trace.py "Where is ORD-1002?"

Then open https://smith.langchain.com → project `novamart-support`
→ click the newest run. You should see nested spans:
  graph.invoke
    ├─ agent        (LLM call #1 — decides to use get_order)
    ├─ tools        (get_order execution)
    └─ agent        (LLM call #2 — final answer)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage

from src.config import ConfigError
from src.graph import run_agent
from src.tracing import setup_tracing, trace_url


def main() -> None:
    question = " ".join(sys.argv[1:]) or "Where is ORD-1002?"

    try:
        settings_ok = setup_tracing()
    except ConfigError as exc:
        print(f"CONFIG ERROR\n{exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Tracing: {'ON → ' + trace_url() if settings_ok else 'OFF (no LangSmith key)'}")

    messages = run_agent([HumanMessage(content=question)])
    answer = next(
        (m.content for m in reversed(messages) if m.content and not getattr(m, "tool_calls", None)),
        "(no answer)",
    )
    print(f"Q: {question}\nA: {answer}")

    # Surface tool hops so learners see the loop even without LangSmith.
    for m in messages:
        if m.type == "tool":
            print(f"  [tool result] {str(m.content)[:100]}")

    if settings_ok:
        print(f"\nInspect the full trace: {trace_url()}")


if __name__ == "__main__":
    main()
