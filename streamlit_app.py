"""NovaMart support chat — UI entry point (Step 6: LangGraph).

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

from src.config import ConfigError
from src.graph import run_agent

st.set_page_config(page_title="NovaMart Support", page_icon="🎧", layout="centered")

# --- session state: chat history lives here between reruns -----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🎧 NovaMart Support")
st.caption("Ask about orders, delivery, refunds or warranty.")

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, ToolMessage):
        continue  # raw tool payloads stay out of the visible chat
    else:
        role = "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

# --- user input -------------------------------------------------------------
user_input = st.chat_input("How can we help?")

if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                # The whole agent workflow in one call:
                # agent ⇄ tools loop runs inside the graph, not here.
                updated = run_agent(st.session_state.messages)
                # Replace history with the graph's output (it includes our
                # new user msg + any tool messages + final AI answer).
                st.session_state.messages = updated
                answer = next(
                    (m.content for m in reversed(updated)
                     if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None)),
                    "(no response)",
                )
            except ConfigError as exc:
                answer = f"⚠️ Configuration problem:\n\n{exc}"
                st.session_state.messages.append(AIMessage(content=answer))
            except Exception as exc:
                answer = f"⚠️ Sorry, the workflow failed: `{exc}`"
                st.session_state.messages.append(AIMessage(content=answer))
        st.markdown(answer)

    # ToolMessage entries from the graph are already in `updated`;
    # ensure the final answer is present even if finders failed.
    if not any(
        isinstance(m, AIMessage) and m.content == answer
        for m in st.session_state.messages
    ):
        st.session_state.messages.append(AIMessage(content=answer))
