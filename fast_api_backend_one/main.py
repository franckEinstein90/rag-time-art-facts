from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from fast_api_backend_one.api.routes import router
from fast_api_backend_one.llm_manager import build_llm_manager


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.llm_manager = build_llm_manager()
    yield
    # nothing to tear down for HTTP-based clients


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rag Time Art Facts API",
        version="0.1.0",
        description="Backend service for model orchestration, conversations, and embeddings.",
        lifespan=_lifespan,
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fast_api_backend_one.main:app", host="127.0.0.1", port=8000, reload=True)
