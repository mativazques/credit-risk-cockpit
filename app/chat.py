"""Copilot chat panel (C3.4).

Renders a chat over the governed copilot. The heavy lifting (function-calling, hardening)
lives behind the FastAPI /ask endpoint; this panel only sends questions through the thin
HTTP client and shows the answer plus which governed tools were called (the "show your
work" that keeps the agent honest). Configure the API location with COPILOT_API_URL
(defaults to the local `make api` server).
"""
from __future__ import annotations

import os

import streamlit as st

from copilot.client import CopilotError, ask

API_URL = os.environ.get("COPILOT_API_URL", "http://localhost:8000")

_EXAMPLES = [
    "What was the lifetime default rate for the 2016Q1 cohort?",
    "Compare the default rate of 2015Q1 vs 2016Q1.",
    "Which metrics can I ask about?",
]


def _tool_trace(tool_calls: list[dict]) -> str:
    names = ", ".join(f"`{c['name']}`" for c in tool_calls)
    return f"Called governed tools: {names}" if names else "Answered without a tool call."


def render() -> None:
    st.caption(
        "Ask a natural-language question about the book's credit risk. The copilot may "
        "only call the governed metrics — same definitions as the charts, never free SQL. "
        f"Needs the copilot API running (`make api`) at `{API_URL}`."
    )
    st.caption("Try: " + " · ".join(f"*{e}*" for e in _EXAMPLES))

    if "chat" not in st.session_state:
        st.session_state.chat = []

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("trace"):
                st.caption(msg["trace"])

    question = st.chat_input("Ask about default rates, cohorts, vintages…")
    if not question:
        return

    st.session_state.chat.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Querying the governed metrics…"):
            try:
                result = ask(question, base_url=API_URL)
            except CopilotError:
                answer = (
                    "The copilot service isn't reachable. Start it with `make api` and "
                    "make sure `GEMINI_API_KEY` is set."
                )
                st.error(answer)
                st.session_state.chat.append({"role": "assistant", "content": answer})
                return
        trace = _tool_trace(result.get("tool_calls", []))
        st.markdown(result["answer"])
        st.caption(trace)
        st.session_state.chat.append(
            {"role": "assistant", "content": result["answer"], "trace": trace}
        )
