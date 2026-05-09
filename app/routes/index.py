from fastapi import APIRouter

from app.routes.embedding import router as embedding_router
from app.routes.match import router as match_router

index_router = APIRouter()

index_router.include_router(embedding_router)
index_router.include_router(match_router)
