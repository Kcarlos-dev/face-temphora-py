# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1 — builder: instala dependências em um venv isolado
# ============================================================
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential: compilação de wheels que ainda não têm binários (raro em py3.13)
# pkg-config + libheif-dev: build de pillow-heif a partir do source quando necessário
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libheif-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# venv dedicado pra copiar pro stage final sem trazer pip cache, build deps, etc.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Pré-baixa o modelo do InsightFace (~280MB) durante o build.
# Sem isso a primeira requisição em produção paga 15s+ pra baixar.
RUN python -c "from insightface.app import FaceAnalysis; \
    a = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
    a.prepare(ctx_id=0, det_size=(640, 640))"


# ============================================================
# Stage 2 — runtime: imagem final enxuta
# ============================================================
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    INSIGHTFACE_HOME=/home/appuser/.insightface \
    PORT=8080

# Libs de runtime mínimas:
# - libgomp1 → OpenMP (insightface/numpy)
# - libheif1 → leitura HEIC (Pillow-heif)
# - ca-certificates → SSL/TLS (Cloud SQL, downloads)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libgomp1 \
        libheif1 \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system appuser \
 && useradd --system --gid appuser --create-home --shell /bin/bash appuser

WORKDIR /app

# Venv com dependências já instaladas
COPY --from=builder /opt/venv /opt/venv

# Modelo do InsightFace baixado no builder → /root/.insightface
COPY --from=builder /root/.insightface /home/appuser/.insightface

# Código da aplicação (depois das deps pra aproveitar layer cache)
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser logger_setup.py ./

RUN chown -R appuser:appuser /home/appuser/.insightface

USER appuser

# Cloud Run injeta $PORT (default 8080). Em local, override no docker-compose.
EXPOSE 8080

# `sh -c` pra que $PORT seja expandido em runtime (não em build).
CMD exec uvicorn app.app:app --host 0.0.0.0 --port ${PORT:-8080}
