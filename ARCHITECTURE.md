# Architecture — AI Customer Support Assistant

Visual guide to how a request moves through the system. Each diagram maps
1:1 to files in this repo — open them side by side while reading.

---

## 1. Module map — who owns what

```mermaid
flowchart TB
    subgraph UI["Presentation — streamlit_app.py + styles/custom.css"]
        CHAT["chat loop<br/>(render → invoke → persist)"]
        SIDE["sidebar: order lookup · workflow explainer · tracing link"]
        CSS["custom.css — brand theme"]
    end

    subgraph CORE["Agent core — src/"]
        GRAPH["graph.py<br/>StateGraph: agent ⇄ tools"]
        LLM["llm.py<br/>get_llm() factory"]
        TOOLS["tools.py<br/>@tool get_order"]
        TRACE["tracing.py<br/>LangSmith env setup"]
        CFG["config.py<br/>.env validation"]
    end

    subgraph DATA["Facts — src/data/"]
        ORD["orders.py<br/>mock order dict"]
        POL["policies.py<br/>NovaMart system prompt"]
    end

    subgraph EXT["External services"]
        GROQ["Groq API<br/>(free LLM)"]
        LS["LangSmith<br/>(traces)"]
    end

    CHAT --> GRAPH
    SIDE --> ORD
    GRAPH --> LLM
    GRAPH --> TOOLS
    TOOLS --> ORD
    LLM --> GROQ
    LLM --> POL
    GRAPH --> POL
    TRACE --> LS
    CFG --> LLM
    UI -. applies .-> CSS
```

**Rule of thumb:** `streamlit_app.py` never imports `ChatGroq` or knows tool
names; `graph.py` never renders anything. Swap UI or provider without
touching the other side.

---

## 2. Request flow — one user turn end-to-end

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant G as LangGraph
    participant A as agent node
    participant L as Groq LLM
    participant T as tools node
    participant D as orders.py
    participant S as LangSmith

    U->>UI: "Where is ORD-1002?"
    UI->>UI: append HumanMessage to session_state
    UI->>G: run_agent(history)
    G->>S: trace: graph.invoke
    G->>A: hop 1
    A->>L: system prompt + history (tool schemas attached)
    L-->>A: tool_calls: get_order(order_id="ORD-1002")
    A-->>G: AIMessage with tool_calls
    G->>T: conditional edge → tools
    T->>D: get_order("ORD-1002")
    D-->>T: order dict
    T-->>G: ToolMessage(order details)
    G->>A: hop 2 (tool results now in state)
    A->>L: system prompt + history + ToolMessage
    L-->>A: final text answer
    A-->>G: AIMessage (no tool_calls)
    G-->>UI: state.messages (full transcript)
    UI->>UI: render assistant bubble, persist
    UI-->>U: "Your keyboard is in transit…"
```

Notice: **the UI participates only at the start and end.** Everything
between is the graph — that's why the same graph can later serve an API,
Slack bot or CLI without rewriting agent logic.

---

## 3. LangGraph state graph

```mermaid
flowchart LR
    START([START]) --> agent

    agent{"agent node<br/>llm.bind_tools()<br/>invoke(state.messages)"}

    agent -->|"no tool_calls"| END([END])
    agent -->|"tool_calls"| tools["tools node<br/>ToolNode(get_order)"]
    tools --> agent

    style agent fill:#1a2444,stroke:#6c8cff,color:#e8ecf8
    style tools fill:#1a2444,stroke:#ffb454,color:#e8ecf8
```

**State schema** (`src/graph.py`):

```mermaid
flowchart TB
    subgraph state["AgentState"]
        msgs["messages: Annotated[list, add_messages]"]
    end
    subgraph reducers["add_messages reducer"]
        r1["node returns {messages: [X]}"] -->|"append, not replace"| msgs
    end
    subgraph nodes["Nodes"]
        n1["agent"] -->|"writes AIMessage / tool_calls"| state
        n2["tools"] -->|"writes ToolMessage"| state
    end
```

- **agent** — calls LLM; output is either final text or `tool_calls`.
- **tools** — prebuilt `ToolNode`; executes each requested tool by name.
- **conditional edge** — `_should_continue` inspects the last message:
  has `tool_calls`? → `tools`, else → `END`.
- **reducer** — `add_messages` appends; without it each hop would wipe history.

---

## 4. Tool-calling contract (what actually crosses the wire)

```mermaid
flowchart TB
    subgraph request["Request to Groq"]
        SYS["system: NovaMart policies"]
        HIST["history: human/AI/tool messages"]
        SCHEMA["tools: JSON schema of get_order<br/>{order_id: string, description: …}"]
    end
    request --> LLM

    LLM --> decision{"needs data?"}
    decision -->|"yes"| TC["tool_calls: [{name, args, id}]<br/>(model never executes it)"]
    decision -->|"no"| ANSWER["content: final answer"]
    TC --> RUN["our code runs get_order(args)"]
    RUN --> TM["ToolMessage(content=result,<br/>tool_call_id=id)"]
    TM --> LLM
    ANSWER --> UI
```

Key insight: the model only **requests** execution with JSON arguments;
Python runs the function and feeds the result back. Hallucination risk
drops because live data enters the conversation as a first-class message.

---

## 5. LangSmith trace anatomy

One user turn → one trace, nested runs:

```mermaid
flowchart TB
    subgraph trace["Trace: graph.invoke (project novamart-support)"]
        direction TB
        h1["run: agent<br/>latency · tokens · raw prompt"]
        h2["run: tools · get_order<br/>args={'order_id':'ORD-1002'} · result"]
        h3["run: agent<br/>final completion"]
        h1 --> h2 --> h3
    end
    trace -. exported via .-> ENV["LANGSMITH_TRACING=true<br/>LANGSMITH_API_KEY<br/>LANGSMITH_PROJECT"]
```

- Span open/close comes from LangChain callbacks — **no tracing code in
  `graph.py`**; `tracing.py` only sets env vars at startup.
- Fail-open: missing key → spans simply never export; app behavior identical.
- Debug workflow: wrong answer → open trace → find first span whose
  input/output looks wrong (bad prompt? bad tool args? bad tool result?).

---

## 6. Where future features plug in

```mermaid
flowchart LR
    subgraph now["MVP (built)"]
        A[agent] --> T[tools: get_order]
        T --> A
    end
    subgraph later["Later — no rewrite needed"]
        RAG["RAG node<br/>(embeddings + vector store)"]
        CACHE["Redis state cache<br/>behind add_messages"]
        MEM["long-term memory node<br/>before agent"]
        HITL["approval node<br/>on sensitive tools"]
        MULTI["multi-agent router<br/>replaces single agent"]
    end
    A -. insert .-> RAG
    A -. replace .-> MULTI
    T -. guard .-> HITL
    state -. swap .-> CACHE
```

Each addition is `g.add_node(...)` + an edge — the reason Step 6 insisted
on an explicit graph instead of a loop in the UI.
