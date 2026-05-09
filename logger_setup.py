"""Configuração centralizada de logging.

Comportamento:
- SEMPRE loga em stdout/stderr (padrão pra containers/Cloud Run, que
  capturam stdout direto pro Cloud Logging).
- Opcionalmente também loga em arquivo se a env `LOG_FILE` estiver setada
  e o caminho for writable.

Ajuste o nível com a env `LOG_LEVEL` (default: INFO).
"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE")  # ex.: /tmp/system.log

_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

if LOG_FILE:
    try:
        handlers.append(
            TimedRotatingFileHandler(
                LOG_FILE, when="D", interval=3, backupCount=10, encoding="utf-8"
            )
        )
    except (PermissionError, FileNotFoundError, OSError) as exc:
        # Não derruba a app: só avisa em stderr e segue sem arquivo.
        sys.stderr.write(
            f"[logger_setup] Não foi possível abrir LOG_FILE={LOG_FILE!r}: {exc}\n"
        )

logging.basicConfig(level=LOG_LEVEL, handlers=handlers, format=_FORMAT, force=True)
