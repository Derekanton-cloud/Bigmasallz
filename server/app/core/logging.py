"""Centralised logging configuration for the application."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import get_settings


def configure_logging() -> None:
    """Configure root logger with console and rotating file handlers."""
    settings = get_settings()
    log_dir: Path = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"
    log_format = (
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    logging.basicConfig(
        level=settings.log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5),
        ],
    )
