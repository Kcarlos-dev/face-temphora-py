from fastapi import FastAPI

from app.routes.index import index_router

# uvicorn app.app:app --host 0.0.0.0 --port 5011


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(index_router)
    return app


app = create_app()
