"""NovaMart support chat — UI entry point (Step 5: tool calling).

Run with:
    .venv/bin/streamlit run streamlit_app.py

Responsibility boundary: this file ONLY renders UI and stores chat history.
The manual tool loop below is what LangGraph will own in Step 6 — keep an
eye on it, because that entire block moves into src/graph.py next step.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import ConfigError
from src.data.policies import SYSTEM_PROMPT
from src.llm import get_llm
from src.tools import TOOLS

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
                # Bind tools: sends the JSON schemas along with the prompt.
                llm = get_llm().bind_tools(TOOLS)
                history = [SystemMessage(content=SYSTEM_PROMPT)] + st.session_state.messages

                # --- MANUAL TOOL LOOP (LangGraph replaces this in Step 6) ---
                # One model call; if it requests a tool we run it and call
                # the model AGAIN with the result. Repeat until it answers.
                ai_message = llm.invoke(history)
                tool_calls = getattr(ai_message, "tool_calls", None) or []

                while tool_calls:
                    st.session_state.messages.append(ai_message)
                    for tc in tool_calls:
                        # Execute the real Python function by name.
                        tool_fn = next(t for t in TOOLS if t.name == tc["name"])
                        result = tool_fn.invoke(tc["args"])
                        st.session_state.messages.append(
                            ToolMessage(content=str(result), tool_call_id=tc["id"])
                        )
                        with st.expander(f"🔧 tool: {tc['name']}({tc['args']})"):
                            st.code(str(result))
                    # Feed results back — model may call more tools or answer.
                    ai_message = llm.invoke(
                        [SystemMessage(content=SYSTEM_PROMPT)] + st.session_state.messages
                    )
                    tool_calls = getattr(ai_message, "tool_calls", None) or []
                # --- END MANUAL TOOL LOOP -----------------------------------

                answer = ai_message.content or "(no response)"
            except ConfigError as exc:
                answer = f"⚠️ Configuration problem:\n\n{exc}"
            except Exception as exc:
                answer = f"⚠️ Sorry, the model call failed: `{exc}`"
        st.markdown(answer)

    st.session_state.messages.append(AIMessage(content=answer))
