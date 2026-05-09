import json
import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

REFERENCE_PATH = Path(__file__).resolve().parent.parent / "data" / "reference_face.json"

DEFAULT_THRESHOLD = 0.42

_reference_cache: dict[str, Any] | None = None
_reference_lock = threading.Lock()


class ReferenceNotLoadedError(Exception):
    """A referência não pôde ser carregada (arquivo ausente ou inválido)."""


def _load_reference() -> dict[str, Any]:
    if not REFERENCE_PATH.exists():
        raise ReferenceNotLoadedError(
            f"Arquivo de referência não encontrado: {REFERENCE_PATH}"
        )

    with REFERENCE_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    embedding = np.asarray(data.get("embedding", []), dtype=np.float32)
    if embedding.size == 0:
        raise ReferenceNotLoadedError("Referência sem campo 'embedding'.")

    norm = float(np.linalg.norm(embedding))
    if norm == 0.0:
        raise ReferenceNotLoadedError("Embedding de referência tem norma zero.")
    if abs(norm - 1.0) > 1e-3:
        logger.warning(
            "Referência não estava L2-normalizada (||v||=%.4f); normalizando.", norm
        )
        embedding = embedding / norm

    return {
        "name": data.get("name", "referencia"),
        "filename": data.get("filename"),
        "model": data.get("model"),
        "embedding": embedding,
        "embedding_dim": int(embedding.shape[0]),
    }


def get_reference() -> dict[str, Any]:
    """Carrega e cacheia a referência (singleton thread-safe)."""
    global _reference_cache
    if _reference_cache is not None:
        return _reference_cache
    with _reference_lock:
        if _reference_cache is None:
            _reference_cache = _load_reference()
    return _reference_cache


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosseno entre dois vetores. Robusto a entradas não normalizadas."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def compare_to_reference(
    candidate_embedding: list[float] | np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    ref = get_reference()
    candidate = np.asarray(candidate_embedding, dtype=np.float32)

    if candidate.shape != ref["embedding"].shape:
        raise ValueError(
            f"Dimensão do embedding candidato ({candidate.shape}) "
            f"difere da referência ({ref['embedding'].shape})."
        )

    similarity = cosine_similarity(candidate, ref["embedding"])
    return {
        "match": similarity >= threshold,
        "similarity": similarity,
        "threshold": threshold,
        "reference_name": ref["name"],
    }
