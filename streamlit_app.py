"""NovaMart support chat — UI entry point (Step 4: LangChain chat).

Run with:
    .venv/bin/streamlit run streamlit_app.py

Responsibility boundary: this file ONLY renders UI and stores chat history.
LLM details live in src/llm.py — when we swap to LangGraph in Step 6, this
file barely changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import ConfigError, get_settings  # noqa: F401  (settings validated inside get_llm)
from src.data.policies import SYSTEM_PROMPT
from src.llm import get_llm

st.set_page_config(page_title="NovaMart Support", page_icon="🎧", layout="centered")

# --- session state: chat history lives here between reruns -----------------
# Streamlit reruns the whole script on every interaction; session_state is
# the only thing that persists. We store LangChain message objects so the
# graph (Step 6) can consume them directly.
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🎧 NovaMart Support")
st.caption("Ask about orders, delivery, refunds or warranty.")

# Replay history as chat bubbles.
for msg in st.session_state.messages:
    with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
        st.markdown(msg.content)

# --- user input -------------------------------------------------------------
user_input = st.chat_input("How can we help?")

if user_input:
    # 1. Show + persist the user's message immediately (optimistic render).
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Call the LLM with full history (system prompt + everything said).
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                llm = get_llm()
                response = llm.invoke(
                    [SystemMessage(content=SYSTEM_PROMPT)] + st.session_state.messages
                )
                answer = response.content or "(no response)"
            except ConfigError as exc:
                answer = f"⚠️ Configuration problem:\n\n{exc}"
            except Exception as exc:  # rate limit, network, auth…
                answer = f"⚠️ Sorry, the model call failed: `{exc}`"
        st.markdown(answer)

    # 3. Persist the assistant reply so the next turn includes it.
    st.session_state.messages.append(AIMessage(content=answer))
