"""
Rag Time Art Facts — standalone Streamlit UI.

Talks to fast_api_backend_1 via HTTP. Run with:
    streamlit run streamlit_standalone_1/app.py
"""

from __future__ import annotations

import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = st.sidebar.text_input(
    "Backend URL",
    value="http://127.0.0.1:8000",
    help="Base URL of the fast_api_backend_1 server.",
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Rag Time Art Facts",
    page_icon="🎨",
    layout="centered",
)

st.title("🎨 Rag Time Art Facts")
st.caption("A simple chat interface backed by fast_api_backend_1.")

# ---------------------------------------------------------------------------
# Sidebar — server health
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Server status")
    if st.button("Check health"):
        try:
            response = httpx.get(f"{API_BASE}/health", timeout=5)
            response.raise_for_status()
            st.success(f"Online — {response.json()}")
        except Exception as exc:
            st.error(f"Unreachable: {exc}")

# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages: list[dict[str, str]] = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask something about art…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                response = httpx.post(
                    f"{API_BASE}/api/chat/",
                    json={"message": prompt},
                    timeout=30,
                )
                response.raise_for_status()
                reply = response.json().get("reply", response.text)
            except httpx.HTTPStatusError as exc:
                reply = f"Server error {exc.response.status_code}: {exc.response.text}"
            except Exception as exc:
                reply = f"Could not reach the backend: {exc}"

        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

if st.session_state.messages and st.sidebar.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()
