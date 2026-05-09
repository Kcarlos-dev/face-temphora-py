"""Helpers HTTP compartilhados pelas rotas que recebem upload de imagem."""

import asyncio
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.services.embedding_service import (
    InvalidImageError,
    NoFaceDetectedError,
    extract_embeddings,
)
from app.services.image_service import (
    ImageDecodeError,
    is_accepted_image,
    normalize_image_bytes,
)


async def upload_to_faces(file: UploadFile) -> list[dict[str, Any]]:
    """Valida → lê → normaliza HEIC → extrai embeddings.

    Levanta `HTTPException` com o status apropriado em caso de erro.
    Retorna a lista de faces (já ordenada por área decrescente).
    """
    if not is_accepted_image(file.content_type, file.filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Tipo de arquivo inválido: {file.content_type!r} "
                f"(arquivo {file.filename!r}). Envie uma imagem."
            ),
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem vazio.",
        )

    try:
        image_bytes, _converted = normalize_image_bytes(
            image_bytes, file.content_type, file.filename
        )
    except ImageDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível decodificar a imagem HEIC/HEIF: {exc}",
        )

    try:
        return await asyncio.to_thread(extract_embeddings, image_bytes)
    except InvalidImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except NoFaceDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
