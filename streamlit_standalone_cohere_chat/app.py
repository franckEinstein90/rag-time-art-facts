"""
Rag Time Art Facts — standalone Streamlit UI.

Talks directly to Cohere (no backend API required). Run with:
    streamlit run streamlit_standalone_1/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import cohere
import streamlit as st
from pydantic import SecretStr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.python.LLM.models import (  # noqa: E402
    ConnectionConfig,
    ExecutionBackend,
    LLMModel,
    ModelCapability,
    Pricing,
    PricingUnit,
    ServiceProvider,
    TokenLimits,
)
from src.python.LLM.types import SimpleChat, StreamingChat  # noqa: E402


def _read_env_key(key: str) -> str | None:
    value = os.getenv(key)
    if value:
        return value

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, raw_val = line.split("=", 1)
        if name.strip() != key:
            continue
        parsed = raw_val.strip().strip('"').strip("'")
        if parsed:
            os.environ[key] = parsed
            return parsed
    return None


def _make_chat(model: LLMModel, key: str) -> SimpleChat:
    try:
        client = cohere.ClientV2(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise Cohere client: {exc}") from exc

    def chat(prompt: str) -> str:
        response = client.chat(
            model=model.model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.message.content[0].text

    return chat


def _extract_delta_text(event: Any) -> str:
    try:
        return event.delta.message.content.text
    except Exception:
        return ""


def _make_streaming_chat(model: LLMModel, key: str) -> StreamingChat:
    try:
        client = cohere.ClientV2(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise Cohere client: {exc}") from exc

    def streaming_chat(prompt: str):
        stream = client.chat_stream(
            model=model.model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        for event in stream:
            if event.type == "content-delta":
                delta = _extract_delta_text(event)
                if delta:
                    yield delta
            elif event.type == "message-end":
                break

    return streaming_chat


@st.cache_resource
def _build_model() -> LLMModel:
    api_key = _read_env_key("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY is not set in environment or .env file.")

    command_a = LLMModel(
        model_id="command-a-03-2025",
        display_name="Cohere Command A (Mar 2025)",
        provider=ServiceProvider.COHERE,
        execution_backend=ExecutionBackend.API,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.CODE,
        },
        token_limits=TokenLimits(context_window=256_000, max_output_tokens=8_000),
        pricing=Pricing(input_cost=2.50, output_cost=10.00, unit=PricingUnit.PER_1M_TOKENS),
        connection=ConnectionConfig(api_key=SecretStr(api_key)),
    )
    command_a.register_chat(_make_chat(command_a, api_key))
    command_a.register_streaming_chat(_make_streaming_chat(command_a, api_key))
    return command_a


def _render_chat_history(messages: list[dict[str, str]]) -> None:
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def _render_simple_chat_page(command_a: LLMModel) -> None:
    st.subheader("Simple Cohere Chat")
    st.caption("Single-response chat using command_a.chat(...).")

    if "messages_simple" not in st.session_state:
        st.session_state.messages_simple = []

    _render_chat_history(st.session_state.messages_simple)

    if prompt := st.chat_input("Ask something about art...", key="simple_chat_input"):
        st.session_state.messages_simple.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    reply = command_a.chat(prompt)
                except Exception as exc:
                    reply = f"Cohere request failed: {exc}"

            st.markdown(reply)
            st.session_state.messages_simple.append({"role": "assistant", "content": reply})


def _render_streaming_chat_page(command_a: LLMModel) -> None:
    st.subheader("Streaming Cohere Chat")
    st.caption("Token streaming using command_a.stream_chat(...) backed by co.chat_stream(...).")

    if "messages_stream" not in st.session_state:
        st.session_state.messages_stream = []

    _render_chat_history(st.session_state.messages_stream)

    if prompt := st.chat_input("Ask something about art (streaming)...", key="stream_chat_input"):
        st.session_state.messages_stream.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                streamed_text = st.write_stream(command_a.stream_chat(prompt))
                if not isinstance(streamed_text, str):
                    streamed_text = ""
            except Exception as exc:
                streamed_text = f"Cohere stream failed: {exc}"
                st.markdown(streamed_text)

        st.session_state.messages_stream.append({"role": "assistant", "content": streamed_text})

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Rag Time Art Facts",
    page_icon="🎨",
    layout="centered",
)

st.title("🎨 Rag Time Art Facts")
st.caption("Cohere chat playground with simple and streaming modes.")

nav = st.radio(
    "Navigation",
    ["simple cohere chat", "streaming cohere chat"],
    horizontal=True,
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Model")
    st.write("Cohere Command A (Mar 2025)")
    st.write("No backend API call is used in this app.")
    if nav == "simple cohere chat" and st.button("Clear simple conversation"):
        st.session_state.messages_simple = []
        st.rerun()
    if nav == "streaming cohere chat" and st.button("Clear streaming conversation"):
        st.session_state.messages_stream = []
        st.rerun()

try:
    command_a = _build_model()
except Exception as exc:
    st.error(f"Configuration error: {exc}")
    st.stop()

if nav == "simple cohere chat":
    _render_simple_chat_page(command_a)
else:
    _render_streaming_chat_page(command_a)
