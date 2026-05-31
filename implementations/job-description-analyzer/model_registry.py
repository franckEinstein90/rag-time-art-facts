from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from pydantic import SecretStr

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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
from src.python.utils import read_env_key  # noqa: E402
from src.python.LLM.LLM_Manager import LLMManager  # noqa: E402
from llm_clients import _make_cohere_streaming_chat, _make_openai_streaming_chat  # noqa: E402


@st.cache_resource
def build_model_manager(allow_empty: bool = False) -> LLMManager:
    manager = LLMManager()

    cohere_key = read_env_key("COHERE_API_KEY")
    if cohere_key:
        command_a = LLMModel(
            model_id="command-a-03-2025",
            display_name="Cohere Command A",
            provider=ServiceProvider.COHERE,
            execution_backend=ExecutionBackend.API,
            capabilities={ModelCapability.CHAT, ModelCapability.CHAT_STREAMING},
            token_limits=TokenLimits(context_window=256_000, max_output_tokens=8_000),
            pricing=Pricing(input_cost=2.50, output_cost=10.00, unit=PricingUnit.PER_1M_TOKENS),
            connection=ConnectionConfig(api_key=SecretStr(cohere_key)),
        )
        command_a.register_streaming_chat(_make_cohere_streaming_chat(command_a, cohere_key))
        manager.add(command_a)

    openai_key = read_env_key("OPENAI_API_KEY")
    if openai_key:
        gpt_4_1_mini = LLMModel(
            model_id="gpt-4.1-mini",
            display_name="GPT-4.1 Mini",
            provider=ServiceProvider.OPENAI,
            execution_backend=ExecutionBackend.API,
            capabilities={ModelCapability.CHAT, ModelCapability.CHAT_STREAMING},
            token_limits=TokenLimits(context_window=1_047_576, max_output_tokens=32_768),
            pricing=Pricing(input_cost=0.40, output_cost=1.60, unit=PricingUnit.PER_1M_TOKENS),
            connection=ConnectionConfig(api_key=SecretStr(openai_key)),
        )
        gpt_4_1_mini.register_streaming_chat(_make_openai_streaming_chat(gpt_4_1_mini, openai_key))
        manager.add(gpt_4_1_mini)

    if len(manager) == 0 and not allow_empty:
        raise RuntimeError(
            "No API keys found. Set COHERE_API_KEY or OPENAI_API_KEY in your .env file."
        )

    return manager
