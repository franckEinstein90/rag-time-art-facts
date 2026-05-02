from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import SecretStr

from src.python.LLM.LLM_Manager import LLMManager
from src.python.LLM.models import (
    ConnectionConfig,
    ExecutionBackend,
    LLMModel,
    ModelCapability,
    Pricing,
    PricingUnit,
    RateLimits,
    ServiceProvider,
    TokenLimits,
    TokenizerConfig,
)


def build_gpt4o() -> LLMModel:
    return LLMModel(
        model_id="gpt-4o",
        display_name="GPT-4o",
        provider=ServiceProvider.OPENAI,
        description="OpenAI's flagship multimodal model.",
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.IMAGE_INPUT,
            ModelCapability.CODE,
        },
        token_limits=TokenLimits(context_window=128_000, max_output_tokens=4_096),
        pricing=Pricing(input_cost=2.50, output_cost=10.00, unit=PricingUnit.PER_1M_TOKENS),
        connection=ConnectionConfig(
            api_key=SecretStr("sk-..."),
            timeout_seconds=60,
        ),
        rate_limits=RateLimits(requests_per_minute=500, tokens_per_minute=200_000),
        tokenizer=TokenizerConfig(
            tokenizer_name="cl100k_base",
            tokenizer_library="tiktoken",
            vocab_size=100_277,
        ),
        expires_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )


def build_claude() -> LLMModel:
    return LLMModel(
        model_id="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6",
        provider=ServiceProvider.ANTHROPIC,
        capabilities={
            ModelCapability.CHAT,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.IMAGE_INPUT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
        },
        token_limits=TokenLimits(context_window=200_000, max_output_tokens=8_192),
        pricing=Pricing(input_cost=3.00, output_cost=15.00, unit=PricingUnit.PER_1M_TOKENS),
        connection=ConnectionConfig(api_key=SecretStr("sk-ant-...")),
        tokenizer=TokenizerConfig(tokenizer_name="claude-tokenizer", vocab_size=100_000),
    )


def build_embed() -> LLMModel:
    return LLMModel(
        model_id="text-embedding-3-large",
        display_name="OpenAI Embedding v3 Large",
        provider=ServiceProvider.OPENAI,
        capabilities={ModelCapability.EMBEDDING},
        token_limits=TokenLimits(context_window=8_191, embedding_dimensions=3_072),
        pricing=Pricing(input_cost=0.13, output_cost=0.0, unit=PricingUnit.PER_1M_TOKENS),
        connection=ConnectionConfig(api_key=SecretStr("sk-...")),
        tokenizer=TokenizerConfig(tokenizer_name="cl100k_base", tokenizer_library="tiktoken"),
    )


@pytest.fixture
def manager_with_three_models() -> tuple[LLMManager, LLMModel, LLMModel, LLMModel]:
    gpt4o = build_gpt4o()
    claude = build_claude()
    embed = build_embed()
    manager = LLMManager()
    manager.add(gpt4o).add(claude).add(embed)
    return manager, gpt4o, claude, embed


def test_registers_models(manager_with_three_models: tuple[LLMManager, LLMModel, LLMModel, LLMModel]) -> None:
    manager, _, _, _ = manager_with_three_models
    assert len(manager) == 3
    assert len(manager.active) == 3


def test_records_usage_and_estimates_cost(
    manager_with_three_models: tuple[LLMManager, LLMModel, LLMModel, LLMModel],
) -> None:
    _, gpt4o, _, _ = manager_with_three_models

    gpt4o.record_request(success=True, input_tokens=512, output_tokens=128, latency_seconds=1.42)
    cost = gpt4o.estimate_cost(512, 128)

    assert cost is not None
    assert round(cost, 6) == 0.00256
    assert gpt4o.usage.success_rate == 1.0


def test_filters_models_with_function_calling(
    manager_with_three_models: tuple[LLMManager, LLMModel, LLMModel, LLMModel],
) -> None:
    manager, _, _, _ = manager_with_three_models
    fc_models = manager.with_capability(ModelCapability.FUNCTION_CALLING)
    assert sorted([m.display_name for m in fc_models]) == ["Claude Sonnet 4.6", "GPT-4o"]


def test_filters_models_by_provider(
    manager_with_three_models: tuple[LLMManager, LLMModel, LLMModel, LLMModel],
) -> None:
    manager, _, _, _ = manager_with_three_models
    openai_models = manager.by_provider(ServiceProvider.OPENAI)
    assert sorted([m.display_name for m in openai_models]) == ["GPT-4o", "OpenAI Embedding v3 Large"]


def test_remove_model(manager_with_three_models: tuple[LLMManager, LLMModel, LLMModel, LLMModel]) -> None:
    manager, _, _, embed = manager_with_three_models
    manager.remove(embed.id)
    assert len(manager) == 2


def test_duplicate_add_requires_overwrite() -> None:
    manager = LLMManager()
    model = build_gpt4o()
    manager.add(model)

    with pytest.raises(ValueError):
        manager.add(model)


def test_update_requires_existing_model() -> None:
    manager = LLMManager()
    with pytest.raises(KeyError):
        manager.update(build_gpt4o())


def test_find_one_returns_none_for_missing() -> None:
    manager = LLMManager()
    assert manager.find_one("missing-model") is None


def test_token_limit_validation_rejects_invalid_output_window() -> None:
    with pytest.raises(ValueError):
        TokenLimits(context_window=10, max_output_tokens=20)


def test_deactivate_expired() -> None:
    manager = LLMManager()
    expired = LLMModel(
        model_id="expired-model",
        display_name="Expired",
        provider=ServiceProvider.CUSTOM,
        token_limits=TokenLimits(context_window=1000, max_output_tokens=100),
        expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    manager.add(expired)

    affected = manager.deactivate_expired()

    assert len(affected) == 1
    assert affected[0].id == expired.id
    assert expired.is_active is False


def test_execute_registered_capability_function() -> None:
    model = build_gpt4o()

    def chat_handler(prompt: str) -> str:
        return f"echo:{prompt}"

    model.register_capability_function(ModelCapability.CHAT, chat_handler)

    result = model.execute_capability(ModelCapability.CHAT, "hello")

    assert result == "echo:hello"


def test_register_chat_allows_command_style_invocation() -> None:
    model = build_gpt4o()

    def chat_handler(prompt: str) -> str:
        return f"chat:{prompt}"

    model.register_chat(chat_handler)

    assert model.chat("hello") == "chat:hello"


def test_chat_requires_string_return_value() -> None:
    model = build_gpt4o()

    model.register_chat(lambda _: 123)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        model.chat("hello")


def test_register_streaming_chat_allows_stream_invocation() -> None:
    model = build_gpt4o()

    def stream_handler(prompt: str):
        yield "chunk:"
        yield prompt

    model.register_streaming_chat(stream_handler)

    assert list(model.stream_chat("hello")) == ["chunk:", "hello"]


def test_stream_chat_requires_registered_function() -> None:
    model = build_gpt4o()

    with pytest.raises(NotImplementedError):
        list(model.stream_chat("hello"))


def test_register_capability_function_rejects_unsupported_capability() -> None:
    model = build_embed()

    with pytest.raises(ValueError):
        model.register_capability_function(ModelCapability.CHAT, lambda _: "nope")


def test_execute_capability_requires_registered_function() -> None:
    model = build_gpt4o()

    with pytest.raises(NotImplementedError):
        model.execute_capability(ModelCapability.CHAT, "hello")


def test_constructor_rejects_unsupported_capability_functions() -> None:
    with pytest.raises(ValueError):
        LLMModel(
            model_id="bad-capability-func",
            provider=ServiceProvider.CUSTOM,
            token_limits=TokenLimits(context_window=1000, max_output_tokens=100),
            capabilities={ModelCapability.EMBEDDING},
            capability_functions={ModelCapability.CHAT: lambda *_: None},
        )


def test_execution_backend_defaults_to_api() -> None:
    model = build_gpt4o()
    assert model.execution_backend == ExecutionBackend.API


def test_execution_backend_can_be_set_to_cpu_or_gpu() -> None:
    cpu_model = LLMModel(
        model_id="local-cpu-model",
        provider=ServiceProvider.OLLAMA,
        token_limits=TokenLimits(context_window=4096),
        execution_backend=ExecutionBackend.CPU,
    )
    gpu_model = LLMModel(
        model_id="local-gpu-model",
        provider=ServiceProvider.OLLAMA,
        token_limits=TokenLimits(context_window=4096),
        execution_backend=ExecutionBackend.GPU,
    )
    assert cpu_model.execution_backend == ExecutionBackend.CPU
    assert gpu_model.execution_backend == ExecutionBackend.GPU
