from fastapi import APIRouter

from fast_api_backend_1.api.chat import chat_router
from fast_api_backend_1.api.model import model_router
from fast_api_backend_1.api.vectorize import vectorize_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(vectorize_router)
router.include_router(model_router)


@router.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {
        "service": "rag-time-art-facts",
        "docs": "/docs",
        "health": "/health",
    }
