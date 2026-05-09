import json
import logging
from fastapi import APIRouter, File, Form, UploadFile
from app.routes._upload_pipeline import upload_to_faces
from app.database.models.update_embedding import update_embedding
router = APIRouter(prefix="/embedding", tags=["embedding"])



@router.post("")
async def post_embedding(
    file: UploadFile = File(..., description="Imagem (jpg, png, webp, heic, heif)"),
    id_colaborador: int = Form(..., description="ID do colaborador dono da face"),
):
    faces = await upload_to_faces(file)
    id_colaborador = id_colaborador
    embedding = {      
        "faces": [
            {"embedding": f["embedding"], "det_score": f["det_score"]}
            for f in faces
        ],
    }
    embedding = embedding["faces"]  

    is_success = update_embedding(embedding, id_colaborador)
    return {
        "is_success": is_success,
    }
