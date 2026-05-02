# This script tests the use of system prompts (called "instructions" in the OpenAI API) to steer the behavior of a model. It defines two chats using the same underlying model but different instructions: one where the model is prompted to answer as a cook, and another where it is prompted to answer as a chemist. We then test both chats with the same question about salt to see how the responses differ based on the instructions.   

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

# Clear the terminal to make it easier to read the test output.
os.system("cls" if os.name == "nt" else "clear")

gpt_5_4_mini_chemist = LLMModel(
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

gpt_5_4_mini_cook = LLMModel(
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

def _make_gpt_5_cook_chat(key: str) -> Chat:
    try:
        _client = OpenAI(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise OpenAI client: {exc}") from exc

    @timed_chat
    def chat(prompt: ChatRequest) -> ChatResponse:
        response = _client.responses.create(
            model=gpt_5_4_mini_cook.model_id,
            instructions="You are a cook and you answer questions about food and cooking. If asked about an ingredient, you provide information about its flavor profile and how it can be used in cooking, for example as a spice, vegetable, protein, etc. You might also discuss how to prepare it and what dishes it pairs well with.",
            input=prompt["message"]
        )
        content = response.output_text or ""
        return {"response": content, "duration": 0.0}

    return chat

def _make_gpt_5_chemist_chat(key: str) -> Chat:
    try:
        _client = OpenAI(api_key=key)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialise OpenAI client: {exc}") from exc

    @timed_chat
    def chat(prompt: ChatRequest) -> ChatResponse:
        response = _client.responses.create(
            model=gpt_5_4_mini_chemist.model_id,
            instructions="You are a chemist and you answer questions about chemistry. If asked about a molecule or substance, you provide information about its chemical properties and structure and how it can be used in chemical reactions, for example as a catalyst, solvent, reagent, etc. You might also discuss its acidity/basicity, polarity, toxicity, and safety precautions.",
            input=prompt["message"]
        )
        content = response.output_text or ""
        return {"response": content, "duration": 0.0}

    return chat

# Testing GPT-5 chat (ChatRequest -> ChatResponse)
gpt_5_cook_chat = _make_gpt_5_cook_chat(api_key)
gpt_5_4_mini_chemist_chat = _make_gpt_5_chemist_chat(api_key)

gpt_5_4_mini_chemist.register_chat(gpt_5_4_mini_chemist_chat)
gpt_5_4_mini_cook.register_chat(gpt_5_cook_chat)

message = "Tell me about vinegar"
gpt5_answer = gpt_5_4_mini_cook.chat(
    {"message": message}
)
if isinstance(gpt5_answer, dict):
    gpt5_answer = {
        **gpt5_answer,
        "response": _sanitize_terminal_text(str(gpt5_answer.get("response", ""))),
    }
print("GPT-5 mini response:", gpt5_answer)

print ("\n" + "="*80 + "\n")

gpt5_answer = gpt_5_4_mini_chemist.chat(
    {"message": message}
)
if isinstance(gpt5_answer, dict):
    gpt5_answer = {
        **gpt5_answer,
        "response": _sanitize_terminal_text(str(gpt5_answer.get("response", ""))),
    }
print("GPT-5 mini response:", gpt5_answer)
 