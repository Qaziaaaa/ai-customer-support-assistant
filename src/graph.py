"""The agent workflow — LangGraph StateGraph.

This file replaces the manual while-loop from Step 5 with an explicit
graph:

    START ─► agent ─┬─(no tool calls)──────────────► END
                    └─(tool calls)─► tools ─► agent  …

Why a graph instead of a chain/loop in the UI?
- **State is typed and owned** — `AgentState.messages` is the single source
  of truth; nodes only read/write that key (add_messages reducer appends).
- **The UI stops knowing about tools** — it just calls `run_agent(...)`.
- **Every hop is a named node** — which is exactly what LangSmith traces
  (Step 7) and what you'll extend later (RAG node, HITL approval node…).
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.data.policies import SYSTEM_PROMPT
from src.llm import get_llm
from src.tools import TOOLS


class AgentState(TypedDict):
    """Everything the workflow needs to carry between nodes.

    `Annotated[..., add_messages]` = the reducer: when a node returns
    {"messages": [new...]}, LangGraph APPENDS instead of overwriting.
    That's how conversation memory survives multiple node hops.
    """

    messages: Annotated[list, add_messages]


def _agent_node(state: AgentState) -> dict:
    """Call the LLM. If it wants tools, it returns tool_calls; otherwise
    its content is the final answer."""
    llm = get_llm().bind_tools(TOOLS)
    system = SystemMessage(content=SYSTEM_PROMPT)
    # Prepend system prompt each hop without storing it in state forever.
    reply = llm.invoke([system] + state["messages"])
    return {"messages": [reply]}


def _should_continue(state: AgentState) -> str:
    """Conditional edge: keep looping while the last AI message requests
    tools, otherwise finish."""
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "end"


def build_graph():
    """Compile the workflow. Building once per process (cached in UI)."""
    g = StateGraph(AgentState)
    g.add_node("agent", _agent_node)
    g.add_node("tools", ToolNode(TOOLS))  # prebuilt: runs tools by name

    g.add_edge(START, "agent")
    g.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", "end": END},  # map: predicate result → node
    )
    g.add_edge("tools", "agent")  # tool results flow back into the model
    return g.compile()


def run_agent(history: list) -> list:
    """Entry point for the UI: full message history in, updated history out.

    The system prompt is injected at invoke-time (not stored in state) so
    it never bloats the conversation the UI displays.
    """
    graph = build_graph()
    final_state = graph.invoke(
        {"messages": [SystemMessage(content=SYSTEM_PROMPT)] + list(history)}
    )
    return final_state["messages"]
