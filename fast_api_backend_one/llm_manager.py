"""
Application-scoped LLM manager.

Call `build_llm_manager()` once at startup (e.g. in the FastAPI lifespan)
and attach the result to `app.state.llm_manager`.  All routers can then
retrieve it via the `get_llm_manager` dependency helper.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import cohere
from openai import OpenAI
from pydantic import SecretStr

from src.python.LLM.LLM_Manager import LLMManager
from src.python.LLM.models import (
    ConnectionConfig,
    ExecutionBackend,
    LLMModel,
    ModelCapability,
    Pricing,
    PricingUnit,
    ServiceProvider,
    TokenLimits,
)
from src.python.LLM.sqlite_db import create_llm_models_sqlite_db
from src.python.LLM.types import Chat, ChatRequest, ChatResponse, SimpleChat, SimpleStreamingChat, Stream
from src.python.utils.call_timer import timed_chat


_ANSI_ESCAPE_RE = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x1b\x07]*(?:\x07|\x1b\\))"
)


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
# Cohere — Command A
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


def _make_cohere_streaming_chat(model: LLMModel, key: str) -> SimpleStreamingChat:
    client = cohere.ClientV2(api_key=key)

    def streaming_chat(prompt: str) -> Stream:
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
                try:
                    delta = event.delta.message.content.text
                except Exception:
                    delta = ""
                if delta:
                    yield _ANSI_ESCAPE_RE.sub("", delta)
            elif event.type == "message-end":
                break

    return streaming_chat


def _register_cohere_command_a(manager: LLMManager, key: str) -> None:
    model = LLMModel(
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
        connection=ConnectionConfig(api_key=SecretStr(key)),
    )
    model.register_chat(_make_cohere_chat(model, key))
    model.register_streaming_chat(_make_cohere_streaming_chat(model, key))
    manager.add(model)


# ---------------------------------------------------------------------------
# OpenAI — GPT-4.1 Mini  (SimpleChat / SimpleStreamingChat)
# ---------------------------------------------------------------------------

def _make_openai_simple_chat(model: LLMModel, key: str) -> SimpleChat:
    client = OpenAI(api_key=key)

    def chat(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model.model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    return chat


def _make_openai_streaming_chat(model: LLMModel, key: str) -> SimpleStreamingChat:
    client = OpenAI(api_key=key)

    def streaming_chat(prompt: str) -> Stream:
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
                yield _ANSI_ESCAPE_RE.sub("", delta)

    return streaming_chat


def _register_openai_gpt_4_1_mini(manager: LLMManager, key: str) -> None:
    model = LLMModel(
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
        connection=ConnectionConfig(api_key=SecretStr(key)),
    )
    model.register_chat(_make_openai_simple_chat(model, key))
    model.register_streaming_chat(_make_openai_streaming_chat(model, key))
    manager.add(model)


# ---------------------------------------------------------------------------
# OpenAI — GPT-5.4 Mini  (Chat / ChatResponse via Responses API)
# ---------------------------------------------------------------------------

def _make_openai_gpt_5_chat(model: LLMModel, key: str) -> Chat:
    client = OpenAI(api_key=key)

    @timed_chat
    def chat(prompt: ChatRequest) -> ChatResponse:
        response = client.responses.create(
            model=model.model_id,
            input=prompt["message"],
            reasoning={"effort": "low"},
        )
        content = response.output_text or ""
        return {"response": _ANSI_ESCAPE_RE.sub("", content), "duration": 0.0}

    return chat


def _register_openai_gpt_5_4_mini(manager: LLMManager, key: str) -> None:
    model = LLMModel(
        model_id="gpt-5.4-mini",
        display_name="OpenAI GPT-5.4 Mini",
        provider=ServiceProvider.OPENAI,
        execution_backend=ExecutionBackend.API,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.CODE,
            ModelCapability.REASONING,
        },
        token_limits=TokenLimits(context_window=1_047_576, max_output_tokens=32_768),
        pricing=Pricing(input_cost=0.40, output_cost=1.60, unit=PricingUnit.PER_1M_TOKENS),
        connection=ConnectionConfig(api_key=SecretStr(key)),
    )
    model.register_chat(_make_openai_gpt_5_chat(model, key))
    manager.add(model)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_llm_manager() -> LLMManager:
    """
    Build and return an LLMManager with all configured models.

    Models are only registered when their API key is present in the
    environment or .env file.  At least one key must be available.
    """
    manager = LLMManager()
    path_of_root = Path(__file__).resolve().parents[1]
    #check if there is a sqlite db in the root of the project, if so load it and add the models to the manager
    sqlite_db_path = path_of_root / "fast_api_backend_one" / "llm_models.db"
    if not sqlite_db_path.exists():
        create_llm_models_sqlite_db(sqlite_db_path)
        print(f"Created new SQLite database for LLM models at: {sqlite_db_path}")

    cohere_key = _read_env_key("COHERE_API_KEY")
    if cohere_key:
        _register_cohere_command_a(manager, cohere_key)

    openai_key = _read_env_key("OPENAI_API_KEY")
    if openai_key:
        _register_openai_gpt_4_1_mini(manager, openai_key)
        _register_openai_gpt_5_4_mini(manager, openai_key)

    if len(manager) == 0:
        raise RuntimeError(
            "No LLM models could be registered. "
            "Set COHERE_API_KEY and/or OPENAI_API_KEY in your environment or .env file."
        )

    return manager
