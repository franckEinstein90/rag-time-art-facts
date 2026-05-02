from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .deps import get_llm_manager
from src.python.LLM.LLM_Manager import LLMManager
from src.python.LLM.models import ModelCapability
from src.python.LLM.types import ChatRequest

chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]


class ChatPayload(BaseModel):
    model_id: str
    message: str


class ChatResult(BaseModel):
    model_id: str
    response: str
    duration: float | None = None


@chat_router.get("/")
async def chat_index() -> dict[str, str]:
    return {"resource": "chat", "status": "ready"}


@chat_router.post("/", response_model=ChatResult)
async def chat(payload: ChatPayload, manager: LLMManagerDep) -> ChatResult:
    model = manager.find_one(payload.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{payload.model_id}' not found.")

    request: ChatRequest = {"message": payload.message}
    raw = model.chat(request)

    if isinstance(raw, dict):
        return ChatResult(
            model_id=payload.model_id,
            response=raw["response"],
            duration=raw.get("duration"),
        )
    return ChatResult(model_id=payload.model_id, response=str(raw))


@chat_router.post("/stream")
async def chat_stream(payload: ChatPayload, manager: LLMManagerDep) -> StreamingResponse:
    model = manager.find_one(payload.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{payload.model_id}' not found.")
    if not model.supports(ModelCapability.CHAT_STREAMING):
        raise HTTPException(
            status_code=422,
            detail=f"Model '{payload.model_id}' does not support streaming.",
        )

    def token_generator():
        for chunk in model.stream_chat(payload.message):
            yield chunk

    return StreamingResponse(token_generator(), media_type="text/plain")