import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.python.LLM.types import SimpleChat, SimpleStreamingChat, Stream

import cohere

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
from pydantic import SecretStr


_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x1b\x07]*(?:\x07|\x1b\\))")


def _sanitize_terminal_text(text: str) -> str:
    # Prevent model output from injecting terminal control sequences.
    return _ANSI_ESCAPE_RE.sub("", text).replace("\r", "")


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


api_key = _read_env_key("COHERE_API_KEY")
if not api_key:
    raise EnvironmentError("COHERE_API_KEY is not set. Add it to your .env file.")

# Reset terminal style in case a previous run left colors in a bad state.
print("\x1b[0m", end="")

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
    connection=ConnectionConfig(api_key=SecretStr(api_key)),
)


def _make_chat(key: str) -> SimpleChat:
    try:
        _client = cohere.ClientV2(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise Cohere client: {exc}") from exc

    def chat(prompt: str) -> str:
        response = _client.chat(
            model=command_a.model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.message.content[0].text

    return chat

def _make_streaming_chat(key: str) -> SimpleStreamingChat:
    try:
        _client = cohere.ClientV2(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise Cohere client: {exc}") from exc

    def streaming_chat(prompt: str) -> Stream:
        yield "[requesting stream...] "
        try:
            stream = _client.chat_stream(
                model=command_a.model_id,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
        except Exception as exc:
            yield f"[error: {exc}]"
            yield "[END]"
            return

        full_text = ""
        for event in stream:
            if event.type == "content-delta":
                delta = event.delta.message.content.text
                full_text += delta
                yield delta
            elif event.type == "message-end":
                break

        if not full_text:
            yield "[error: empty streamed content]"
        yield "[END]"

    return streaming_chat

#Testing simple chat
test_cohere_chat = _make_chat(api_key)
command_a.register_chat(test_cohere_chat)
answer = command_a.chat("which cohere model is the fastest? ")
print("Cohere response:", _sanitize_terminal_text(answer))


#Testing streaming chat
command_a.register_streaming_chat(_make_streaming_chat(api_key))
answer = command_a.stream_chat("What are the main differences between Cohere's Command A and OpenAI's GPT-4o?")
print("Streaming response:", end=" ", flush=True)
for chunk in answer:
    if chunk == "[END]":
        break
    print(_sanitize_terminal_text(chunk), end="", flush=True)
print()


