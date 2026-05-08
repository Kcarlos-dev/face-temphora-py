from fastapi import APIRouter, Depends

from app.controllers.controller_embedding import ControllerEmbedding

router = APIRouter(prefix="/embedding", tags=["embedding"])


def get_controller() -> ControllerEmbedding:
    return ControllerEmbedding()


@router.get("")
def get_embedding(controller: ControllerEmbedding = Depends(get_controller)):
    return controller.get_embedding()


@router.post("")
def post_embedding(controller: ControllerEmbedding = Depends(get_controller)):
    return controller.post_embedding()
