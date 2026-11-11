# LEARNING.md — step-by-step notes

Each project step adds a section here: **what** changed, **why** it exists,
and **where** to look in the code.

---

## Step 1 — Project skeleton

**What:** git repo, folder structure, `.env.example`, NovaMart mock data.

**Why this layout:**
- `src/data/` holds *facts* (orders, policies) separate from *logic* — later
  you can swap the dict for a real database without touching the agent code.
- `streamlit_app.py` will be UI-only; `src/graph.py` will be workflow-only.
  Separating layers now is what makes future RAG / multi-agent additions
  drop-in instead of rewrites.
- `.env` is gitignored so keys never enter history; `.env.example` documents
  exactly which variables the app expects.

**Why mock data as a dict?** Tool calling needs something deterministic to
retrieve. A dict keeps the first lesson about tools focused on the *mechanism*
(JSON schema → LLM emits call → function runs → result returns), not on SQL.

**Try it:**
```bash
python3 -c "from src.data.orders import get_order; print(get_order('ord-1001'))"
```

---

## Step 2 — Config + raw LLM call (no frameworks)

**What:** `src/config.py` (validated env loading) + `demos/01_raw_llm.py`.

**Why raw first?** LangChain wraps an HTTP call. The demo shows the actual
contract: *messages in → assistant message out*. Everything later is a
convenience layer over this.

**Key ideas in `demos/01_raw_llm.py`:**
- **Roles**: `system` = instructions/persona, `user` = the question,
  `assistant` = model replies. Multi-turn = append the whole history each call.
- **Base URL swap**: Groq is OpenAI-compatible, so the same `openai` SDK
  works — only `base_url` + key change. This is why `llm.py` (Step 4) can
  swap providers cheaply.
- **Grounding**: the system prompt embeds NovaMart policies so answers come
  from *our* text, not the model's imagination.
- **Token usage**: `response.usage` shows what the call cost.

**Why `config.py`?** One place validates keys and raises a *human* error
("get a free key at …") instead of a library 401. Tracing is also wired to
degrade silently when LangSmith keys are absent — observability must never
break the app.

**Try it:**
```bash
cp .env.example .env    # paste your Groq key
.venv/bin/python demos/01_raw_llm.py "What is your refund window?"
```
(Without a key you should see the friendly CONFIG ERROR — that's by design.)
