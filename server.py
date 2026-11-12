"""Landing-page server: static clone + live agent API.

Run:
    .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000

Serves the mirrored site from landing/ and exposes POST /api/chat which
is wired to the same LangGraph workflow the Streamlit UI uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402

from src.config import ConfigError  # noqa: E402
from src.graph import run_agent  # noqa: E402
from src.tracing import setup_tracing  # noqa: E402

LANDING = Path(__file__).resolve().parent / "landing"

app = FastAPI(title="NovaMart Landing + Chat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local demo only
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_tracing()  # before any LLM call — no-op without key


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _to_lc(messages: list[ChatMessage]) -> list:
    """OpenAI-style dict messages → LangChain message objects."""
    out = []
    for m in messages:
        if m.role == "user":
            out.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            out.append(AIMessage(content=m.content))
        # system/other roles ignored — prompt lives in src/data/policies.py
    return out


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    history = _to_lc(req.messages)
    try:
        updated = run_agent(history)
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # surface workflow failures to the UI
        raise HTTPException(status_code=500, detail=f"workflow failed: {exc}") from exc

    answer = next(
        (
            m.content
            for m in reversed(updated)
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None)
        ),
        "(no response)",
    )
    return {"reply": answer}


# ── Static site ─────────────────────────────────────────────────────────────
# html=True → directory requests serve index.html; 404s fall through carefully.
app.mount("/assets", StaticFiles(directory=LANDING / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str) -> FileResponse:
    """Serve mirrored pages; clean URLs (/about) map to /about.html."""
    if not full_path:
        return FileResponse(LANDING / "index.html")
    candidate = LANDING / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    if not Path(full_path).suffix and (LANDING / f"{full_path}.html").is_file():
        return FileResponse(LANDING / f"{full_path}.html")
    raise HTTPException(status_code=404, detail="Not found")
