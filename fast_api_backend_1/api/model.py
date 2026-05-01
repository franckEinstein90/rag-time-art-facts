from fastapi import APIRouter

model_router = APIRouter(prefix="/api/model", tags=["model"])


@model_router.get("/")
async def model_index() -> dict[str, str]:
    return {
        "resource": "model",
        "status": "ready",
    }