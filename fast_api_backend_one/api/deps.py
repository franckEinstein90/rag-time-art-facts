"""Shared FastAPI dependency providers."""

from fastapi import Request

from src.python.LLM.LLM_Manager import LLMManager


def get_llm_manager(request: Request) -> LLMManager:
    """Return the app-wide LLMManager from application state."""
    return request.app.state.llm_manager
