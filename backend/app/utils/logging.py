"""Structured logging configuration."""

import logging
import sys

from app.core.config import settings


def setup_logging():
    """Configure application logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
