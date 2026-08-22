"""Configuração central de logging do pipeline: console + arquivo rotativo."""

import logging
from logging.handlers import RotatingFileHandler

from clima_pipeline.config import LOG_FILE, LOG_LEVEL

_CONFIGURADO = False


def setup_logging(level: str | None = None) -> None:
    """Configura o logger raiz uma única vez (chamadas repetidas são no-op)."""
    global _CONFIGURADO
    if _CONFIGURADO:
        return

    nivel = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formato)

    arquivo_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    arquivo_handler.setFormatter(formato)

    logging.basicConfig(level=nivel, handlers=[console_handler, arquivo_handler])
    _CONFIGURADO = True
