from fastapi import APIRouter, File, Query, UploadFile

from app.routes._upload_pipeline import upload_to_faces
from app.services.match_service import DEFAULT_THRESHOLD, compare_to_reference

router = APIRouter(prefix="/match", tags=["match"])


@router.post("")
async def post_match(
    file: UploadFile = File(..., description="Imagem (jpg, png, webp, heic, heif)"),
    threshold: float = Query(
        DEFAULT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Limiar de similaridade de cossenos para considerar 'match'.",
    ),
):
    """Compara as faces detectadas com a referência. Retorna a melhor similaridade."""
    faces = await upload_to_faces(file)

    best_similarity = max(
        compare_to_reference(f["embedding"], threshold=threshold)["similarity"]
        for f in faces
    )

    return {
        "match": best_similarity >= threshold,
        "similarity": best_similarity,
        "threshold": threshold,
    }
