"""NovaMart support chat — UI entry point (Step 8: themed UI + sidebar).

Run with:
    .venv/bin/streamlit run streamlit_app.py

Responsibility boundary: this file ONLY renders UI and stores chat history.
All workflow logic (tool loop, state, routing) lives in src/graph.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import ConfigError, get_settings
from src.data.orders import get_order, ORDERS
from src.graph import run_agent
from src.tracing import setup_tracing, trace_url

st.set_page_config(
    page_title="NovaMart Support",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

THEME_PATH = Path(__file__).parent / "styles" / "custom.css"
st.markdown(f"<style>{THEME_PATH.read_text()}</style>", unsafe_allow_html=True)

tracing_on = setup_tracing()  # before any LLM call — no-op without key

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎧 NovaMart")
    st.caption("Customer support assistant")

    # --- Order lookup card (deterministic, no LLM) ---
    st.markdown('<div class="nm-card"><h4>📦 Quick order lookup</h4>', unsafe_allow_html=True)
    lookup_id = st.text_input("Order ID", value="ORD-1002", label_visibility="collapsed",
                              placeholder="ORD-####")
    if lookup_id:
        order = get_order(lookup_id)
        if order:
            status = order["status"].replace(" ", "_")
            st.markdown(
                f'<div class="nm-row"><span>Product</span><strong>{order["product"]}</strong></div>'
                f'<div class="nm-row"><span>Placed</span><strong>{order["placed_on"]}</strong></div>'
                f'<div class="nm-row"><span>Status</span>'
                f'<strong><span class="nm-status-pill nm-status-{status}">{order["status"]}</span></strong></div>'
                + (
                    f'<div class="nm-row"><span>Tracking</span><strong>{order["tracking"]}</strong></div>'
                    if order["tracking"]
                    else ""
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="nm-row"><span style="color:#ff8b8b">No order with that ID</span></div>',
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # --- How it works card (live workflow explainer) ---
    st.markdown(
        '<div class="nm-card"><h4>🧠 How a reply is made</h4>'
        '<div class="nm-flow">'
        "1. <b>agent</b> — LLM reads your msg + history<br>"
        "2. needs order data? → <b>tools</b> runs get_order<br>"
        "3. back to <b>agent</b> — builds final answer<br>"
        "4. each hop traced in LangSmith"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # --- Observability card ---
    if tracing_on:
        st.markdown(
            f'<div class="nm-card"><h4>🔬 Observability</h4>'
            f'<div class="nm-row"><span>LangSmith</span>'
            f'<strong style="color:#35d0ba">tracing on</strong></div>'
            f'<a href="{trace_url()}" target="_blank" '
            f'style="color:#6c8cff;font-size:0.85rem">Open traces ↗</a></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="nm-card"><h4>🔬 Observability</h4>'
            '<div class="nm-row"><span>LangSmith</span>'
            '<strong style="color:#93a0c2">off</strong></div>'
            '<span style="color:#93a0c2;font-size:0.8rem">Add LANGSMITH_API_KEY to .env</span></div>',
            unsafe_allow_html=True,
        )

    # --- Controls ---
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption(f"{len(ORDERS)} mock orders · multi-turn memory on")

# ── Main chat ──────────────────────────────────────────────────────────────
st.title("🎧 NovaMart Support")
st.caption('Ask about orders, delivery, refunds or warranty — try *"Where is ORD-1002?"*')

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, ToolMessage):
        continue  # raw tool payloads stay out of the visible chat
    else:
        role = "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

user_input = st.chat_input("How can we help?")

if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                updated = run_agent(st.session_state.messages)
                st.session_state.messages = updated
                answer = next(
                    (
                        m.content
                        for m in reversed(updated)
                        if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None)
                    ),
                    "(no response)",
                )
            except ConfigError as exc:
                answer = f"⚠️ Configuration problem:\n\n{exc}"
                st.session_state.messages.append(AIMessage(content=answer))
            except Exception as exc:
                answer = f"⚠️ Sorry, the workflow failed: `{exc}`"
                st.session_state.messages.append(AIMessage(content=answer))
        st.markdown(answer)

    if not any(
        isinstance(m, AIMessage) and m.content == answer
        for m in st.session_state.messages
    ):
        st.session_state.messages.append(AIMessage(content=answer))
