"""
Rag Time Art Facts — standalone Streamlit UI.

Talks directly to Cohere or OpenAI (no backend API required). Run with:
    streamlit run streamlit_standalone_one/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import cohere
import streamlit as st
from openai import OpenAI
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
from src.python.LLM.LLM_Manager import LLMManager  # noqa: E402
from src.python.LLM.types import SimpleChat, SimpleStreamingChat  # noqa: E402


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


# ---------------------------------------------------------------------------
# Cohere builders
# ---------------------------------------------------------------------------

def _make_cohere_chat(model: LLMModel, key: str) -> SimpleChat:
    client = cohere.ClientV2(api_key=key)

    def chat(prompt: str) -> str:
        response = client.chat(
            model=model.model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.message.content[0].text

    return chat


def _extract_cohere_delta(event: Any) -> str:
    try:
        return event.delta.message.content.text
    except Exception:
        return ""


def _make_cohere_streaming_chat(model: LLMModel, key: str) -> SimpleStreamingChat:
    client = cohere.ClientV2(api_key=key)

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
                delta = _extract_cohere_delta(event)
                if delta:
                    yield delta
            elif event.type == "message-end":
                break

    return streaming_chat


# ---------------------------------------------------------------------------
# OpenAI builders
# ---------------------------------------------------------------------------

def _make_openai_chat(model: LLMModel, key: str) -> SimpleChat:
    client = OpenAI(api_key=key)

    def chat(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model.model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    return chat


def _make_openai_streaming_chat(model: LLMModel, key: str) -> SimpleStreamingChat:
    client = OpenAI(api_key=key)

    def streaming_chat(prompt: str):
        stream = client.chat.completions.create(
            model=model.model_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    return streaming_chat


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

@st.cache_resource
def _build_model_manager() -> LLMManager:
    manager = LLMManager()

    cohere_key = _read_env_key("COHERE_API_KEY")
    if cohere_key:
        command_a = LLMModel(
            model_id="command-a-03-2025",
            display_name="Cohere Command A (Mar 2025)",
            provider=ServiceProvider.COHERE,
            execution_backend=ExecutionBackend.API,
            capabilities={
                ModelCapability.CHAT,
                ModelCapability.CHAT_STREAMING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.CODE,
            },
            token_limits=TokenLimits(context_window=256_000, max_output_tokens=8_000),
            pricing=Pricing(input_cost=2.50, output_cost=10.00, unit=PricingUnit.PER_1M_TOKENS),
            connection=ConnectionConfig(api_key=SecretStr(cohere_key)),
        )
        command_a.register_chat(_make_cohere_chat(command_a, cohere_key))
        command_a.register_streaming_chat(_make_cohere_streaming_chat(command_a, cohere_key))
        manager.add(command_a)

    openai_key = _read_env_key("OPENAI_API_KEY")
    if openai_key:
        gpt_4_1_mini = LLMModel(
            model_id="gpt-4.1-mini",
            display_name="OpenAI GPT-4.1 Mini",
            provider=ServiceProvider.OPENAI,
            execution_backend=ExecutionBackend.API,
            capabilities={
                ModelCapability.CHAT,
                ModelCapability.CHAT_STREAMING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.CODE,
            },
            token_limits=TokenLimits(context_window=1_047_576, max_output_tokens=32_768),
            pricing=Pricing(input_cost=0.40, output_cost=1.60, unit=PricingUnit.PER_1M_TOKENS),
            connection=ConnectionConfig(api_key=SecretStr(openai_key)),
        )
        gpt_4_1_mini.register_chat(_make_openai_chat(gpt_4_1_mini, openai_key))
        gpt_4_1_mini.register_streaming_chat(_make_openai_streaming_chat(gpt_4_1_mini, openai_key))
        manager.add(gpt_4_1_mini)

    if len(manager) == 0:
        raise RuntimeError("No API keys found. Set COHERE_API_KEY or OPENAI_API_KEY in your .env file.")

    return manager


def _model_label(model: LLMModel) -> str:
    name = model.display_name or model.model_id
    return f"{name} [{model.model_id}]"


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

def _render_chat_history(messages: list[dict[str, str]]) -> None:
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def _render_simple_chat_page(model: LLMModel) -> None:
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
                    reply = model.chat(prompt)
                except Exception as exc:
                    reply = f"Request failed: {exc}"
            st.markdown(reply)
            st.session_state[key].append({"role": "assistant", "content": reply})


def _render_streaming_chat_page(model: LLMModel) -> None:
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
                streamed_text = st.write_stream(model.stream_chat(prompt))
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
    model_manager = _build_model_manager()
except Exception as exc:
    st.error(f"Configuration error: {exc}")
    st.stop()

available_models = model_manager.active
if not available_models:
    st.error("No active models are available.")
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
    models_by_id = {model.model_id: model for model in available_models}
    selected_model_id = st.selectbox(
        "Choose a model",
        options=list(models_by_id.keys()),
        format_func=lambda model_id: _model_label(models_by_id[model_id]),
        label_visibility="collapsed",
    )
    active_model = model_manager.find_one(selected_model_id)
    if active_model is None:
        st.error(f"Selected model is not registered: {selected_model_id}")
        st.stop()
    st.caption(f"Provider: {active_model.provider}")
    st.caption(f"Context: {active_model.token_limits.context_window:,} tokens")

    st.divider()

    if nav == "simple chat":
        session_key = f"messages_simple_{active_model.model_id}"
        if st.button("Clear conversation"):
            st.session_state[session_key] = []
            st.rerun()
    else:
        session_key = f"messages_stream_{active_model.model_id}"
        if st.button("Clear conversation"):
            st.session_state[session_key] = []
            st.rerun()

if nav == "simple chat":
    _render_simple_chat_page(active_model)
else:
    _render_streaming_chat_page(active_model)


