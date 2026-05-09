import logging
import threading
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

MODEL_NAME = "buffalo_l"
DET_SIZE = (640, 640)
PROVIDERS = ["CPUExecutionProvider"]


class NoFaceDetectedError(Exception):
    """Nenhuma face foi detectada na imagem."""


class InvalidImageError(Exception):
    """Bytes recebidos não puderam ser decodificados como imagem."""


_face_app: FaceAnalysis | None = None
_face_app_lock = threading.Lock()


def get_face_analyser() -> FaceAnalysis:
    """Carrega o FaceAnalysis uma única vez (singleton thread-safe)."""
    global _face_app
    if _face_app is not None:
        return _face_app

    with _face_app_lock:
        if _face_app is None:
            logger.info("Carregando modelo InsightFace %r...", MODEL_NAME)
            analyser = FaceAnalysis(name=MODEL_NAME, providers=PROVIDERS)
            analyser.prepare(ctx_id=0, det_size=DET_SIZE)
            _face_app = analyser
            logger.info("Modelo InsightFace pronto.")
    return _face_app


def _decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise InvalidImageError("Não foi possível decodificar os bytes como imagem.")
    return img


def _gender_label(gender: int | None) -> str | None:
    if gender is None:
        return None
    return {0: "F", 1: "M"}.get(int(gender))


def _face_to_dict(face: Any) -> dict[str, Any]:
    bbox = face.bbox.astype(int).tolist()
    embedding = face.normed_embedding.astype(np.float32)
    return {
        "bbox": bbox,
        "det_score": float(face.det_score),
        "embedding": embedding.tolist(),
        "embedding_dim": int(embedding.shape[0]),
        "age": int(face.age) if getattr(face, "age", None) is not None else None,
        "gender": _gender_label(getattr(face, "gender", None)),
    }


def extract_embeddings(image_bytes: bytes) -> list[dict[str, Any]]:
    """Roda detecção + reconhecimento e devolve uma lista de faces.

    Cada face contém bbox, score, embedding L2-normalizado (512-d) e atributos.
    Faces são ordenadas pela maior área (face mais "principal" primeiro).
    """
    img = _decode_image(image_bytes)
    analyser = get_face_analyser()
    faces = analyser.get(img)

    if not faces:
        raise NoFaceDetectedError("Nenhuma face detectada na imagem.")

    results = [_face_to_dict(f) for f in faces]
    results.sort(
        key=lambda f: (f["bbox"][2] - f["bbox"][0]) * (f["bbox"][3] - f["bbox"][1]),
        reverse=True,
    )
    return results
