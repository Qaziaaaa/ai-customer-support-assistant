# Architecture — AI Customer Support Assistant

Three simple diagrams. No function-level detail — just the flow.

---

## 1. The big picture

```mermaid
flowchart LR
    U[👤 You] -->|question| UI[Streamlit chat]
    UI --> A[🤖 Agent]
    A -->|needs facts| T[📦 Order tool]
    T -->|order data| A
    A -->|writes answer| UI
    UI -->|answer| U
    A -.observed by.-> LS[🔬 LangSmith]
```

**In words:** you type → chat app sends to agent → agent either knows the
answer (policies in its prompt) or fetches order data first → final answer
comes back to the chat. LangSmith watches everything.

---

## 2. Agent loop — how one reply is made

```mermaid
flowchart TB
    Q[Your question] --> AG[Agent asks the LLM]
    AG --> D{Needs order data?}

    D -->|No — policy question| ANS[✅ Writes the answer]
    D -->|Yes — asks about an order| TOOL[📦 get_order runs]
    TOOL --> AG2[Agent asks the LLM again<br/>now with the order data]
    AG2 --> ANS

    ANS --> OUT[Answer shown in chat]
```

That's the whole agent: **ask → fetch if needed → ask again → answer.**

---

## 3. Where each answer comes from

```mermaid
flowchart LR
    subgraph you["In your code (static)"]
        P["policies.py<br/>'30 days', '1-year warranty'"]
        O["orders.py<br/>'NV1002US', 'In transit'"]
    end

    subgraph brain["Live LLM (Groq)"]
        W["Wording & tone<br/>sentence structure<br/>follow-up context"]
    end

    P -->|fed via prompt| LLM[LLM]
    O -->|fed via tool| LLM
    LLM --> R["Your answer<br/>facts = yours<br/>words = LLM's"]
```

- **Ask a policy question** → answer built from `policies.py`, phrased by the LLM
- **Ask about an order** → tool pulls from `orders.py`, LLM phrases it
- **Ask something off-script** → LLM either grounds in policies or
  escalates to a human agent (per instructions) — it never invents facts

---

## Where future features plug in

```mermaid
flowchart LR
    A[Agent] --> T[Order tool]
    T --> A

    A -.-> RAG["RAG / documents"]
    A -.-> MEM["Memory"]
    A -.-> MULTI["Multi-agent"]
    T -.-> HITL["Human approval"]
```

Each future feature is **one new box + one line** — the loop above never
gets rewritten. That's why the workflow lives in `src/graph.py` instead of
inside the UI.
