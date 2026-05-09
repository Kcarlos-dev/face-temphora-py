from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.routes._upload_pipeline import upload_to_faces
from app.services.match_service import (
    DEFAULT_THRESHOLD,
    DatabaseError,
    NoCandidatesError,
    find_best_match,
)

router = APIRouter(prefix="/match", tags=["match"])


@router.post("")
async def post_match(
    file: UploadFile = File(..., description="Imagem (jpg, png, webp, heic, heif)"),
    id_empresa: int = Form(..., description="ID da empresa (escopo da busca)"),
    threshold: float = Query(
        DEFAULT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Limiar de similaridade de cossenos.",
    ),
):
    """Identifica o colaborador da empresa cuja face mais se parece com a enviada."""
    faces = await upload_to_faces(file)
    main_face = faces[0]

    try:
        result = find_best_match(
            main_face["embedding"], id_empresa=id_empresa, threshold=threshold
        )
    except NoCandidatesError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return result
