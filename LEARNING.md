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

---

## Step 3 — Streamlit chat UI (multi-turn, raw LLM)

**What:** `streamlit_app.py` — chat bubbles, input box, history in
`st.session_state`.

**Why Streamlit?** Python-only, so the learning focus stays on the AI stack.
It is a *server-side reactive* framework: the whole script re-runs on every
interaction (keystroke → widget change → submit). That mental model drives
everything about how state works.

**The three-part chat loop** (same pattern you'll see in every chat app):
1. **Render history** — replay `st.session_state.messages` as bubbles.
2. **On new input** — optimistically render the user bubble, call the LLM
   with `system + full history`, render the reply.
3. **Persist reply** — append the assistant message so the *next* rerun
   includes it.

**Why history in `session_state`?** The LLM API is *stateless* — it forgets
everything between calls. Multi-turn works only because we resend the entire
conversation each time. (LangGraph in Step 6 moves this state into the graph;
the UI keeps owning display only.)

**What's still raw:** the file talks to the `openai` SDK directly. Step 4
replaces that one call with LangChain — watch how little else changes.

**Try it:**
```bash
.venv/bin/streamlit run streamlit_app.py
```
Ask "what's your refund policy?" then a follow-up like "and if it's damaged?" —
the second answer only works because history is resent.

---

## Step 4 — LangChain layer (ChatGroq factory)

**What:** `src/llm.py` (`get_llm()`), UI now calls `llm.invoke(...)` with
LangChain message objects instead of the raw `openai` SDK.

**Why LangChain at all?** It answers three recurring pain points:
1. **Provider abstraction** — `ChatGroq`, `ChatOpenAI`, `ChatGoogleGenerativeAI`
   all expose `.invoke(messages)`. Swapping providers = edit one factory.
2. **Message types** — `SystemMessage` / `HumanMessage` / `AIMessage` are
   classes, not dicts; fewer typos, tool-calling fields come for free later.
3. **Integration surface** — tools (Step 5), LangGraph (Step 6) and LangSmith
   (Step 7) all speak "LangChain objects". Skipping this layer means
   re-implementing all three yourself.

**What did NOT change?** The UI flow (render → call → persist) and
`config.py`. That's the point of the factory: `streamlit_app.py` imports
`get_llm`, never `ChatGroq` directly.

**Design details worth noting:**
- `temperature=0` — support answers should be reproducible, not creative.
- `@lru_cache` on the factory — Streamlit re-runs the script constantly;
  cache the client for the process lifetime.
- `demos/01_raw_llm.py` stays untouched as a permanent baseline: when
  something breaks in the framework stack, the raw demo tells you whether
  the API itself is fine.

**Try it:**
```bash
.venv/bin/python -c "from src.llm import get_llm; print(get_llm())"
# (needs GROQ_API_KEY in .env)
```
