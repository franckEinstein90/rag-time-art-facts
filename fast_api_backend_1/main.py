from fastapi import FastAPI

from fast_api_backend_1.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rag Time Art Facts API",
        version="0.1.0",
        description="Backend service for model orchestration, conversations, and embeddings.",
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fast_api_backend_1.main:app", host="127.0.0.1", port=8000, reload=True)
