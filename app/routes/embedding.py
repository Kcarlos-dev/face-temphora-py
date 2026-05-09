from fastapi import APIRouter, File, UploadFile

from app.routes._upload_pipeline import upload_to_faces

router = APIRouter(prefix="/embedding", tags=["embedding"])


@router.get("")
def get_embedding():
    return {"message": "Hello, World!"}


@router.post("")
async def post_embedding(
    file: UploadFile = File(..., description="Imagem (jpg, png, webp, heic, heif)"),
):
    faces = await upload_to_faces(file)
    return {
        "faces": [
            {"embedding": f["embedding"], "det_score": f["det_score"]}
            for f in faces
        ],
    }
