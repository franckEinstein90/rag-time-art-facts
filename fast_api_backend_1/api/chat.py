from fastapi import APIRouter

chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


@chat_router.get("/")
async def chat_index() -> dict[str, str]:
    return {
        "resource": "chat",
        "status": "ready",
    }