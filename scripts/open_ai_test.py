import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.python.LLM.types import Chat, ChatRequest, ChatResponse, SimpleChat, SimpleStreamingChat, Stream
from src.python.utils.call_timer import timed_chat

from openai import OpenAI

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


api_key = _read_env_key("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("OPENAI_API_KEY is not set. Add it to your .env file.")

# Reset terminal style in case a previous run left colors in a bad state.
print("\x1b[0m", end="")

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
    connection=ConnectionConfig(api_key=SecretStr(api_key)),
)


def _make_simple_chat(key: str) -> SimpleChat:
    try:
        _client = OpenAI(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise OpenAI client: {exc}") from exc

    def chat(prompt: str) -> str:
        response = _client.chat.completions.create(
            model=gpt_4_1_mini.model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    return chat


def _make_streaming_chat(key: str) -> SimpleStreamingChat:
    try:
        _client = OpenAI(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise OpenAI client: {exc}") from exc

    def streaming_chat(prompt: str) -> Stream:
        yield "[requesting stream...] "
        try:
            stream = _client.chat.completions.create(
                model=gpt_4_1_mini.model_id,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                stream=True,
            )
        except Exception as exc:
            yield f"[error: {exc}]"
            yield "[END]"
            return

        full_text = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_text += delta
                yield delta

        if not full_text:
            yield "[error: empty streamed content]"
        yield "[END]"

    return streaming_chat


if __name__ == "__main__":
    # Testing simple chat
    test_openai_chat = _make_simple_chat(api_key)
    gpt_4_1_mini.register_chat(test_openai_chat)
    answer = gpt_4_1_mini.chat("Respond with the exact text 'Test One'")
    print("OpenAI response:", _sanitize_terminal_text(str(answer)))

    # Testing streaming chat
    gpt_4_1_mini.register_streaming_chat(_make_streaming_chat(api_key))
    answer = gpt_4_1_mini.stream_chat("Respond with the exact text 'Test Two'")
    print("Streaming response:", end=" ", flush=True)
    for chunk in answer:
        if chunk == "[END]":
            break
        print(_sanitize_terminal_text(chunk), end="", flush=True)
    print()


gpt_5_4_mini = LLMModel(
    model_id="gpt-5.4-mini",
    display_name="OpenAI GPT-5.4 Mini",
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
    connection=ConnectionConfig(api_key=SecretStr(api_key)),
)


def _make_gpt_5_chat(key: str) -> Chat:
    try:
        _client = OpenAI(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise OpenAI client: {exc}") from exc

    @timed_chat
    def chat(prompt: ChatRequest) -> ChatResponse:
        response = _client.responses.create(
            model=gpt_5_4_mini.model_id,
            input=prompt["message"],
            reasoning={"effort": "low"},
        )
        content = response.output_text or ""
        return {"response": content, "duration": 0.0}

    return chat


if __name__ == "__main__":
    # Testing GPT-5 chat (ChatRequest -> ChatResponse)
    gpt_5_chat = _make_gpt_5_chat(api_key)
    gpt_5_4_mini.register_chat(gpt_5_chat)
    gpt5_answer = gpt_5_4_mini.chat(
        {"message": "Respond with the exact text 'Test Three' and use low reasoning effort."}
    )
    if isinstance(gpt5_answer, dict):
        gpt5_answer = {
            **gpt5_answer,
            "response": _sanitize_terminal_text(str(gpt5_answer.get("response", ""))),
        }
    print("GPT-5 mini response:", gpt5_answer)



 