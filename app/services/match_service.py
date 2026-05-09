import json
import logging
from typing import Any

import numpy as np

from app.database.models.select_embedding import select_embedding

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.42


class NoCandidatesError(Exception):
    """A empresa não tem colaboradores com embedding cadastrado."""


class DatabaseError(Exception):
    """Falha ao consultar os embeddings no banco."""


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosseno entre dois vetores. Robusto a entradas não normalizadas."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _extract_embedding_array(values: Any) -> list | None:
    """Aceita formato novo (lista plana de floats) E formato antigo
    (lista de dicts com chave 'embedding'). Retorna a lista plana ou None."""
    if not isinstance(values, list) or not values:
        return None

    if isinstance(values[0], dict):
        first = values[0]
        inner = first.get("embedding")
        if not isinstance(inner, list) or not inner:
            return None
        return inner

    if all(isinstance(v, (int, float)) for v in values):
        return values

    return None


def _parse_db_row(row: dict) -> tuple[int, np.ndarray] | None:
    """Converte uma linha do banco em (id_colaborador, embedding_array).

    Tolera registros sem embedding ('{}', '[]', NULL) e formato legado
    (lista de dicts contendo o vetor em `embedding`).
    """
    raw = row.get("embedding")
    if not raw:
        return None

    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        logger.warning(
            "Embedding com JSON inválido para colaborador id=%s.", row.get("id")
        )
        return None

    flat = _extract_embedding_array(values)
    if flat is None:
        return None

    try:
        emb = np.asarray(flat, dtype=np.float32)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Embedding inválido para colaborador id=%s: %s", row.get("id"), exc
        )
        return None

    if emb.size == 0:
        return None
    return int(row["id"]), emb


def find_best_match(
    candidate_embedding: list[float] | np.ndarray,
    id_empresa: int,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """Compara o candidato com todos os colaboradores da empresa.

    Retorna o colaborador com maior similaridade. `match` é True se
    a similaridade ultrapassa o threshold.
    """
    rows = select_embedding(id_empresa)
    if rows is False:
        raise DatabaseError("Falha ao consultar colaboradores no banco.")
    parsed = [p for p in (_parse_db_row(r) for r in rows) if p is not None]
    if not parsed:
        raise NoCandidatesError(
            f"Nenhum colaborador da empresa {id_empresa} tem embedding cadastrado."
        )

    candidate = np.asarray(candidate_embedding, dtype=np.float32)

    best_id = -1
    best_sim = -1.0
    for col_id, emb in parsed:
        if emb.shape != candidate.shape:
            logger.warning(
                "Dimensão divergente para colaborador id=%s: %s vs %s",
                col_id, emb.shape, candidate.shape,
            )
            continue
        sim = cosine_similarity(candidate, emb)
        if sim > best_sim:
            best_sim = sim
            best_id = col_id

    return {
        "match": best_sim >= threshold,
        "similarity": best_sim,
        "threshold": threshold,
        "id_colaborador": best_id if best_sim >= threshold else None,
        "best_id_colaborador": best_id,
        "candidates_count": len(parsed),
    }
