from fastapi import APIRouter

vectorize_router = APIRouter(prefix="/api/vectorize", tags=["vectorize"])


@vectorize_router.get("/")
async def vectorize_index() -> dict[str, str]:
    return {
        "resource": "vectorize",
        "status": "ready",
    }