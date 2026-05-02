"""
Rag Time Art Facts — Streamlit UI backed by fast_api_backend_one.

All LLM logic is delegated to the FastAPI server; this app only does HTTP.
Requires the backend to be running at BACKEND_URL (default http://127.0.0.1:8000).

Run with:
    streamlit run streamlit_frontend_one/app.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Generator

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


# ---------------------------------------------------------------------------
# Lightweight model descriptor (populated from GET /api/model/)
# ---------------------------------------------------------------------------

@dataclass
class ModelInfo:
    model_id: str
    display_name: str
    provider: str
    capabilities: list[str]

    @staticmethod
    def from_dict(data: dict) -> "ModelInfo":
        return ModelInfo(
            model_id=data["model_id"],
            display_name=data["display_name"],
            provider=data["provider"],
            capabilities=data.get("capabilities", []),
        )

    @property
    def supports_streaming(self) -> bool:
        return "chat_streaming" in self.capabilities


# ---------------------------------------------------------------------------
# API client helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def _fetch_models() -> list[ModelInfo]:
    resp = requests.get(f"{_BACKEND_URL}/api/model/", timeout=10)
    resp.raise_for_status()
    return [ModelInfo.from_dict(m) for m in resp.json()]


def _chat(model_id: str, message: str) -> tuple[str, float | None]:
    resp = requests.post(
        f"{_BACKEND_URL}/api/chat/",
        json={"model_id": model_id, "message": message},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["response"], data.get("duration")


def _stream_chat(model_id: str, message: str) -> Generator[str, None, None]:
    with requests.post(
        f"{_BACKEND_URL}/api/chat/stream",
        json={"model_id": model_id, "message": message},
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                yield chunk


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _model_label(model: ModelInfo) -> str:
    return f"{model.display_name} [{model.model_id}]"


def _render_chat_history(messages: list[dict[str, str]]) -> None:
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def _render_simple_chat_page(model: ModelInfo) -> None:
    st.subheader("Simple Chat")
    st.caption(f"Single-response chat using {model.display_name}.")

    key = f"messages_simple_{model.model_id}"
    if key not in st.session_state:
        st.session_state[key] = []

    _render_chat_history(st.session_state[key])

    if prompt := st.chat_input("Ask something...", key="simple_chat_input"):
        st.session_state[key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    reply, duration = _chat(model.model_id, prompt)
                except Exception as exc:
                    reply = f"Request failed: {exc}"
                    duration = None
            st.markdown(reply)
            if duration is not None:
                st.caption(f"⏱ {duration:.2f}s")

        st.session_state[key].append({"role": "assistant", "content": reply})


def _render_streaming_chat_page(model: ModelInfo) -> None:
    st.subheader("Streaming Chat")
    st.caption(f"Token streaming using {model.display_name}.")

    key = f"messages_stream_{model.model_id}"
    if key not in st.session_state:
        st.session_state[key] = []

    _render_chat_history(st.session_state[key])

    if prompt := st.chat_input("Ask something (streaming)...", key="stream_chat_input"):
        st.session_state[key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                streamed_text = st.write_stream(_stream_chat(model.model_id, prompt))
                if not isinstance(streamed_text, str):
                    streamed_text = ""
            except Exception as exc:
                streamed_text = f"Stream failed: {exc}"
                st.markdown(streamed_text)

        st.session_state[key].append({"role": "assistant", "content": streamed_text})


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Rag Time Art Facts",
    page_icon="🎨",
    layout="centered",
)

st.title("🎨 Rag Time Art Facts")

try:
    models = _fetch_models()
except Exception as exc:
    st.error(f"Could not reach the backend at `{_BACKEND_URL}`: {exc}")
    st.info(
        "Make sure **fast_api_backend_one** is running. "
        "Use the *fast_api_backend_one: dev server* launch configuration."
    )
    st.stop()

if not models:
    st.error("No models are available from the backend.")
    st.stop()

nav = st.radio(
    "Navigation",
    ["simple chat", "streaming chat"],
    horizontal=True,
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Model")
    models_by_id = {m.model_id: m for m in models}
    selected_model_id = st.selectbox(
        "Choose a model",
        options=list(models_by_id.keys()),
        format_func=lambda mid: _model_label(models_by_id[mid]),
        label_visibility="collapsed",
    )
    active_model = models_by_id[selected_model_id]
    st.caption(f"Provider: {active_model.provider}")
    st.caption(f"Capabilities: {', '.join(active_model.capabilities)}")

    st.divider()

    session_key = (
        f"messages_simple_{active_model.model_id}"
        if nav == "simple chat"
        else f"messages_stream_{active_model.model_id}"
    )
    if st.button("Clear history", use_container_width=True):
        st.session_state[session_key] = []
        st.rerun()

    st.divider()
    st.caption(f"Backend: `{_BACKEND_URL}`")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if nav == "simple chat":
    _render_simple_chat_page(active_model)
else:
    if not active_model.supports_streaming:
        st.warning(f"{active_model.display_name} does not support streaming. Switch to Simple Chat.")
    else:
        _render_streaming_chat_page(active_model)
