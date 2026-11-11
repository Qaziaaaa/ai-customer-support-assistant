"""NovaMart support chat — UI entry point (Step 3: basic chat, raw LLM).

Run with:
    .venv/bin/streamlit run streamlit_app.py

Responsibility boundary: this file ONLY renders UI and stores chat history.
LLM details live in src/ — when we swap to LangGraph in Step 6, this file
barely changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import ConfigError, get_settings
from src.data.policies import SYSTEM_PROMPT

st.set_page_config(page_title="NovaMart Support", page_icon="🎧", layout="centered")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"

# --- session state: chat history lives here between reruns -----------------
# Streamlit reruns the whole script on every interaction; session_state is
# the only thing that persists. History = list of {role, content} dicts —
# the exact message format the LLM API expects.
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🎧 NovaMart Support")
st.caption("Ask about orders, delivery, refunds or warranty.")

# Replay history as chat bubbles.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- user input -------------------------------------------------------------
user_input = st.chat_input("How can we help?")

if user_input:
    # 1. Show + persist the user's message immediately (optimistic render).
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Call the LLM with full history (system prompt + everything said).
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                settings = get_settings()
                client = OpenAI(api_key=settings.groq_api_key, base_url=GROQ_BASE_URL)
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}]
                    + st.session_state.messages,
                )
                answer = response.choices[0].message.content or "(no response)"
            except ConfigError as exc:
                answer = f"⚠️ Configuration problem:\n\n{exc}"
            except Exception as exc:  # rate limit, network, auth…
                answer = f"⚠️ Sorry, the model call failed: `{exc}`"
        st.markdown(answer)

    # 3. Persist the assistant reply so the next turn includes it.
    st.session_state.messages.append({"role": "assistant", "content": answer})
