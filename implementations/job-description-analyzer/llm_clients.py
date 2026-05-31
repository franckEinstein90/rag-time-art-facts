from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import cohere
from openai import OpenAI

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.python.LLM.models import LLMModel  # noqa: E402

_SYSTEM_PROMPT = "You are an expert career coach and technical recruiter."


def _make_cohere_streaming_chat(model: LLMModel, key: str):
    client = cohere.ClientV2(api_key=key)

    def _extract_delta(event: Any) -> str:
        try:
            return event.delta.message.content.text
        except Exception:
            return ""

    def streaming_chat(prompt: str):
        stream = client.chat_stream(
            model=model.model_id,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        for event in stream:
            if event.type == "content-delta":
                delta = _extract_delta(event)
                if delta:
                    yield delta
            elif event.type == "message-end":
                break

    return streaming_chat


def _make_openai_streaming_chat(model: LLMModel, key: str):
    client = OpenAI(api_key=key)

    def streaming_chat(prompt: str):
        stream = client.chat.completions.create(
            model=model.model_id,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
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
