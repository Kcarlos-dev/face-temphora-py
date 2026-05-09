import io
import os

import pillow_heif
from PIL import Image, UnidentifiedImageError

pillow_heif.register_heif_opener()


ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
    }
)
HEIF_TYPES: frozenset[str] = frozenset({"image/heic", "image/heif"})
HEIF_EXTENSIONS: frozenset[str] = frozenset({".heic", ".heif"})


class ImageDecodeError(Exception):
    """Levantada quando os bytes recebidos não puderam ser decodificados."""


def _ext(filename: str | None) -> str:
    if not filename:
        return ""
    return os.path.splitext(filename)[1].lower()


def is_heif(content_type: str | None, filename: str | None) -> bool:
    if content_type and content_type.lower() in HEIF_TYPES:
        return True
    return _ext(filename) in HEIF_EXTENSIONS


def is_accepted_image(content_type: str | None, filename: str | None) -> bool:
    ct = (content_type or "").lower()
    if ct in ALLOWED_IMAGE_TYPES:
        return True
    if ct.startswith("image/"):
        return True
    return is_heif(content_type, filename)


def heif_to_jpeg_bytes(image_bytes: bytes, quality: int = 95) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageDecodeError(str(exc)) from exc

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def normalize_image_bytes(
    image_bytes: bytes,
    content_type: str | None,
    filename: str | None,
) -> tuple[bytes, bool]:
    """Converte HEIC/HEIF para JPEG; demais formatos passam intactos.

    Retorna (bytes_finais, foi_convertido).
    """
    if is_heif(content_type, filename):
        return heif_to_jpeg_bytes(image_bytes), True
    return image_bytes, False
