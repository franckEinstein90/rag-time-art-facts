from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .deps import get_llm_manager
from src.python.LLM.LLM_Manager import LLMManager

model_router = APIRouter(prefix="/api/model", tags=["model"])

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]


class ModelInfo(BaseModel):
    model_id: str
    display_name: str
    provider: str
    capabilities: list[str]


def _string_value(value: object) -> str:
    return str(getattr(value, "value", value))


@model_router.get("/", response_model=list[ModelInfo])
async def list_models(manager: LLMManagerDep) -> list[ModelInfo]:
    return [
        ModelInfo(
            model_id=m.model_id,
            display_name=m.display_name,
            provider=_string_value(m.provider),
            capabilities=[_string_value(c) for c in m.capabilities],
        )
        for m in manager.active
    ]