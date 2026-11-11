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

---

## Step 5 — Tool calling (`get_order`)

**What:** `src/tools.py` with a `@tool`-decorated `get_order`; the UI binds
tools to the LLM and runs a **manual tool loop**.

**Why tools matter:** LLMs are frozen at training time — they cannot know
ORD-1002's status. Tool calling lets the model *request* real data while
staying the "brain" that plans the conversation.

**The mechanism (visible in `streamlit_app.py`):**
1. `llm.bind_tools(TOOLS)` — attaches JSON schemas (auto-generated from the
   function signature + docstring) to the request.
2. Model replies with either normal content **or** `tool_calls`
   (name + JSON args). It does not execute anything itself.
3. **Our code** runs the real Python function → append a `ToolMessage`.
4. Call the model again with the result → it may call more tools or give
   the final answer. Loop until no `tool_calls`.

**Why the docstring matters:** the model reads it to decide *when* to use
the tool and how to fill arguments. Bad docstring = bad tool selection.

**Why a not-found path?** Tools must return data the LLM can relay —
including "doesn't exist". Never raise into the model loop; return a
structured message (see `get_order` for `ORD-9999`).

**What's clunky on purpose:** the while-loop in the UI is verbose. Step 6
moves it into LangGraph — you'll feel exactly what the framework buys you.

**Try it:**
```bash
GROQ_API_KEY=... .venv/bin/python -c "from src.tools import get_order; print(get_order.invoke({'order_id':'ORD-1001'}))"
# In the UI: "Where is ORD-1002?" → watch the 🔧 tool expander fire.
```

---

## Step 6 — LangGraph workflow (`src/graph.py`)

**What:** explicit `StateGraph` with two nodes (`agent`, `tools`) and a
conditional edge. The UI's manual while-loop is gone — it now calls
`run_agent(history)`.

**Why a graph, not just a loop?**
| Concern | Step 5 (manual loop) | Step 6 (LangGraph) |
|---|---|---|
| Where memory lives | UI's `session_state` + ad-hoc list | Typed `AgentState` with `add_messages` reducer |
| Tool loop | `while` in the UI | Conditional edge: `agent → tools → agent` |
| Observability | one opaque LLM call | each node = a named span (LangSmith, Step 7) |
| Future nodes (RAG, HITL…) | more UI spaghetti | `g.add_node(...)` + one edge |

**The three LangGraph concepts this file teaches:**
1. **State** — `AgentState(TypedDict)` is the data every node reads/writes.
   `Annotated[list, add_messages]` is a *reducer*: nodes append messages
   instead of overwriting (otherwise each hop would erase history).
2. **Nodes** — plain functions `state → partial state update`. `_agent_node`
   calls the LLM; `ToolNode` is prebuilt and executes tool calls by name.
3. **Conditional edges** — `_should_continue` inspects the last message:
   has `tool_calls`? → route to `tools`; else → `END`. This *is* the agent
   loop, declared as data instead of written as control flow.

**System prompt placement:** injected at `invoke()` time, not stored in
state — the UI never displays it, and it can't be accidentally truncated
out of the conversation.

**Visualize the graph yourself:**
```bash
GROQ_API_KEY=dummy .venv/bin/python -c \
  "from src.graph import build_graph; print(build_graph().get_graph().draw_mermaid())"
```

**Try it:** run the UI and ask *"Where is ORD-1002?"* — the spinner covers
the agent→tools→agent hops; answer cites live order data.

---

## Step 7 — LangSmith tracing (`src/tracing.py`)

**What:** `setup_tracing()` (called at UI startup) + demo script
`demos/02_langsmith_trace.py`.

**What problem does observability solve?** When the agent answers wrong,
"the LLM messed up" is not actionable. LangSmith records every hop as a
nested **run** (span):

```
graph.invoke
├─ agent        ← LLM call #1: model chose tool_calls for ORD-1002
├─ tools        ← get_order("ORD-1002") in → status out
└─ agent        ← LLM call #2: final answer built from tool result
```

Click any span to see exact prompts, raw JSON args, latency, tokens.
Debugging becomes *which hop lied*, not *somewhere in the black box*.

**How it attaches (key insight):** you do NOT instrument `graph.py`.
LangChain/LangGraph ship with callbacks that read env vars:
`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`.
Our module only translates `.env` → process env (plus legacy
`LANGCHAIN_*` aliases). Tracing is a **config-layer** concern.

**Fail-open design:** no key → `setup_tracing()` returns False → app runs
identically with zero traces. Same principle as error handling elsewhere:
observability must never take down the product.

**Get your free keys:**
- Groq: https://console.groq.com/keys
- LangSmith: https://smith.langchain.com/settings (Developer plan, 5k traces/mo, no card)

**Try it:**
```bash
python3 demos/02_langsmith_trace.py "Where is ORD-1002?"
# then open the printed smith.langchain.com URL
```

---

## Step 8 — Custom theme + sidebar (`styles/custom.css`)

**What:** full visual identity (dark navy + brand gradient), chat bubbles,
sidebar with order lookup, live workflow explainer, LangSmith link, clear
button.

**Why CSS in a Python project?** Streamlit renders HTML — `st.markdown`
with `unsafe_allow_html=True` injects our stylesheet once at startup. All
branding lives in **one file**; Python never mixes with presentation.

**Three-layer CSS structure (a pattern worth stealing):**
1. **Design tokens** (`:root` vars) — colors, radii in one block; rebrand
   by editing 10 lines, not 200 selectors.
2. **App chrome** — background gradients, sidebar, inputs, buttons.
3. **Chat bubbles** — `:has([data-testid="stChatMessageAvatarUser"])`
   targets Streamlit's internal test IDs to style user vs assistant sides.

**Sidebar pieces and why each exists:**
- **Quick order lookup** — deterministic (pure Python, no LLM) so users can
  compare "what the tool sees" vs "what the model says".
- **How a reply is made** — live diagram of the graph nodes; reinforces the
  architecture while using the product.
- **Observability card** — tracing status + deep link; fail-open design
  visible in the UI (off state explains the fix).
- **Clear conversation** — resets `session_state.messages`.

**Try it:** `.venv/bin/streamlit run streamlit_app.py` — sidebar right,
bubbles left, amber expanders appear when tools fire.

---

## Step 9 — Architecture docs (Mermaid)

**What:** [ARCHITECTURE.md](ARCHITECTURE.md) with 6 diagrams + README rewrite.

**Why diagrams as code (Mermaid)?** They live in the repo, diff with code,
and render on GitHub/VS Code — architecture that can't rot silently into a
stale PNG. Each diagram maps to real files; read them side by side.

**The six diagrams and what each teaches:**
1. **Module map** — dependency direction: UI → graph → llm/tools → data;
   who is allowed to import whom.
2. **Sequence flow** — one turn end-to-end; shows the UI only participates
   at the start/end (why the graph is reusable for APIs/bots later).
3. **State graph** — nodes, conditional edge, `add_messages` reducer.
4. **Tool contract** — the exact JSON that crosses the wire; the model
   requests, Python executes.
5. **Trace anatomy** — one turn = one trace with nested spans; debug by
   finding the first wrong span.
6. **Future plug-in points** — where RAG/Redis/HITL/multi-agent attach
   with `add_node` instead of rewrites.

**How to read this project now:**
```
LEARNING.md (why each step exists)
  → ARCHITECTURE.md (how the pieces connect)
    → src/graph.py (the heart — everything else serves it)
```

**Full verification checklist:**
```bash
# structure & imports
python3 -c "from src.graph import build_graph; print(build_graph().get_graph().draw_mermaid())"
# tool behavior
python3 -c "from src.tools import get_order; print(get_order.invoke({'order_id':'ORD-1001'}))"
# UI boots
streamlit run streamlit_app.py
# live LLM + tool + trace (needs keys in .env)
python3 demos/02_langsmith_trace.py "Where is ORD-1002?"
```
