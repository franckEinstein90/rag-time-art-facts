from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .Connection_Config_Model import ConnectionConfig
from .Enum_Types import ConnectionStatus, ExecutionBackend, ModelCapability, PricingUnit, ServiceProvider
from .Pricing_Model import Pricing
from .Rate_Limits_Model import RateLimits
from .Token_Limit_Model import TokenLimits
from .Tokenizer_Config_Model import TokenizerConfig
from .Usage_Stats_Model import UsageStats
from ..types import Chat, ChatRequest, ChatResponse, SimpleChat, SimpleStreamingChat, Stream


class LLMModel(BaseModel):
    """
    A fully-described large language model instance.

    Covers identity, capabilities, token limits, pricing, connection,
    tokenization, usage tracking, and lifecycle metadata.
    """

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True, arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4, description="Stable internal identifier.")
    model_id: str = Field(..., description="Provider model name, e.g. 'gpt-4o', 'claude-sonnet-4-6'.")
    display_name: str | None = Field(None, description="Human-friendly label.")
    version: str | None = Field(None, description="Model version or snapshot date, e.g. '2025-05-01'.")
    provider: ServiceProvider = ServiceProvider.CUSTOM
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    capabilities: set[ModelCapability] = Field(default_factory=set)

    token_limits: TokenLimits

    pricing: Pricing | None = None

    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    execution_backend: ExecutionBackend = ExecutionBackend.API

    tokenizer: TokenizerConfig | None = None

    usage: UsageStats = Field(default_factory=UsageStats)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deprecated_at: datetime | None = None
    expires_at: datetime | None = Field(
        None, description="When this model version will be retired by the provider."
    )
    is_active: bool = True

    metadata: dict[str, Any] = Field(default_factory=dict)

    # Runtime-provided handlers for capability-specific actions.
    capability_functions: dict[ModelCapability, Callable[..., Any]] = Field(
        default_factory=dict,
        exclude=True,
        repr=False,
    )
    streaming_chat_function: SimpleStreamingChat | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    @field_validator("capabilities", mode="before")
    @classmethod
    def coerce_capabilities(cls, v: Any) -> set[ModelCapability]:
        if isinstance(v, (list, tuple)):
            return set(v)
        return v

    @field_validator("capability_functions", mode="before")
    @classmethod
    def coerce_capability_functions(
        cls,
        v: dict[ModelCapability | str, Callable[..., Any]] | None,
    ) -> dict[ModelCapability, Callable[..., Any]]:
        if v is None:
            return {}
        return {ModelCapability(capability): func for capability, func in v.items()}

    @model_validator(mode="after")
    def validate_capability_function_support(self) -> "LLMModel":
        unsupported = [capability for capability in self.capability_functions if not self.supports(capability)]
        if unsupported:
            unsupported_caps = ", ".join(
                ModelCapability(capability).value for capability in unsupported
            )
            raise ValueError(
                "capability_functions can only be registered for supported capabilities. "
                f"Unsupported: {unsupported_caps}."
            )
        return self

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_deprecated(self) -> bool:
        if self.deprecated_at is None:
            return False
        return datetime.now(timezone.utc) >= self.deprecated_at

    @property
    def days_until_expiry(self) -> int | None:
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    def supports(self, capability: ModelCapability) -> bool:
        return ModelCapability(capability) in {ModelCapability(c) for c in self.capabilities}

    def register_capability_function(
        self,
        capability: ModelCapability,
        func: Callable[..., Any],
        *,
        allow_unsupported: bool = False,
    ) -> None:
        capability = ModelCapability(capability)
        if not callable(func):
            raise TypeError("func must be callable.")
        if not allow_unsupported and not self.supports(capability):
            raise ValueError(
                f"Cannot register function for unsupported capability: {capability.value}."
            )
        self.capability_functions[capability] = func
        self.touch()

    def has_capability_function(self, capability: ModelCapability) -> bool:
        capability = ModelCapability(capability)
        return capability in self.capability_functions

    def remove_capability_function(self, capability: ModelCapability) -> None:
        capability = ModelCapability(capability)
        self.capability_functions.pop(capability, None)
        self.touch()

    def register_chat(self, func: SimpleChat | Chat, *, allow_unsupported: bool = False) -> None:
        def _chat_adapter(payload: str | ChatRequest) -> str | ChatResponse:
            if isinstance(payload, str):
                try:
                    result = func(payload)  # type: ignore[arg-type]
                except (TypeError, KeyError, AttributeError):
                    request: ChatRequest = {"message": payload}
                    result = func(request)  # type: ignore[arg-type]

                if isinstance(result, str):
                    return result
                if isinstance(result, dict):
                    response = result.get("response")
                    if isinstance(response, str):
                        return response
                raise TypeError(
                    "Registered chat function must return a string for string input, or a ChatResponse with a string 'response' field."
                )

            if not isinstance(payload.get("message"), str):
                raise TypeError("ChatRequest must contain a string 'message' field.")

            try:
                result = func(payload["message"])  # type: ignore[arg-type]
            except (TypeError, KeyError, AttributeError):
                result = func(payload)  # type: ignore[arg-type]

            if isinstance(result, dict):
                response = result.get("response")
                duration = result.get("duration")
                if isinstance(response, str) and isinstance(duration, (int, float)):
                    return {"response": response, "duration": float(duration)}
            if isinstance(result, str):
                return {"response": result, "duration": 0.0}
            raise TypeError(
                "Registered chat function must return ChatResponse for ChatRequest input, or a string that can be adapted to ChatResponse."
            )

        self.register_capability_function(
            ModelCapability.CHAT,
            _chat_adapter,
            allow_unsupported=allow_unsupported,
        )

    def register_streaming_chat(
        self,
        func: SimpleStreamingChat,
        *,
        allow_unsupported: bool = False,
    ) -> None:
        if not callable(func):
            raise TypeError("func must be callable.")
        if not allow_unsupported and not self.supports(ModelCapability.CHAT_STREAMING):
            raise ValueError(
                f"Cannot register function for unsupported capability: {ModelCapability.CHAT_STREAMING.value}."
            )
        self.streaming_chat_function = func
        self.touch()

    def execute_capability(self, capability: ModelCapability, *args: Any, **kwargs: Any) -> Any:
        capability = ModelCapability(capability)
        if not self.supports(capability):
            raise ValueError(f"Model does not support capability: {capability.value}.")
        func = self.capability_functions.get(capability)
        if func is None:
            raise NotImplementedError(
                f"No function registered for capability: {capability.value}."
            )
        return func(*args, **kwargs)

    def chat(self, prompt: str | ChatRequest) -> str | ChatResponse:
        started_at = perf_counter()
        result = self.execute_capability(ModelCapability.CHAT, prompt)
        elapsed = perf_counter() - started_at

        if isinstance(prompt, str):
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                response = result.get("response")
                if isinstance(response, str):
                    return response
            raise TypeError("Registered chat function must return a string for string input.")

        if not isinstance(prompt.get("message"), str):
            raise TypeError("ChatRequest must contain a string 'message' field.")
        if isinstance(result, dict):
            response = result.get("response")
            if isinstance(response, str):
                return {"response": response, "duration": elapsed}
        if isinstance(result, str):
            return {"response": result, "duration": elapsed}
        raise TypeError(
            "Registered chat function must return ChatResponse for ChatRequest input."
        )

    def stream_chat(self, prompt: str) -> Stream:
        if not self.supports(ModelCapability.CHAT_STREAMING):
            raise ValueError(
                f"Model does not support capability: {ModelCapability.CHAT_STREAMING.value}."
            )
        if self.streaming_chat_function is None:
            raise NotImplementedError("No streaming chat function registered.")
        return self.streaming_chat_function(prompt)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        self.is_active = True
        self.touch()

    def record_request(self, **kwargs: Any) -> None:
        self.usage.record_request(**kwargs)
        self.touch()

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> float | None:
        if self.pricing is None:
            return None
        divisor = {
            PricingUnit.PER_1K_TOKENS: 1_000,
            PricingUnit.PER_1M_TOKENS: 1_000_000,
            PricingUnit.PER_REQUEST: None,
            PricingUnit.PER_SECOND: None,
        }[PricingUnit(self.pricing.unit)]

        if divisor is None:
            return None

        return (input_tokens * self.pricing.input_cost + output_tokens * self.pricing.output_cost) / divisor
